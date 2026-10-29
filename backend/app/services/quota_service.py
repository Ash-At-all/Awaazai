"""
Atomic Quota Accounting & Fallback Routing Service for AwaazAI.
Handles trial duration checks, per-user limits, global spend guardrails,
and SQLite transaction serialization to prevent race-condition overspending.
"""
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..config import settings
from ..models import User, UserQuota, GlobalSpend

# Standard rate: ₹0.0015 per synthesized premium character
COST_PER_PREMIUM_CHAR_INR = 0.0015

def get_current_utc_date() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

class QuotaService:
    @staticmethod
    def get_user_quota_summary(db: Session, user: User) -> Dict[str, Any]:
        """
        Calculates remaining trial days, premium quota balances, and current engine status.
        """
        now = datetime.now(timezone.utc)
        today_str = get_current_utc_date()

        # Check verification
        if not user.is_verified:
            return {
                "is_trial_active": False,
                "days_left": 0,
                "trial_ends_at": None,
                "premium_daily_chars_left": 0,
                "premium_total_chars_left": 0,
                "free_daily_chars_left": settings.FREE_FALLBACK_DAILY_CHARS,
                "current_engine": "free",
                "ineligibility_reason": "unverified",
            }

        # Check trial expiry
        trial_ends_at = user.trial_ends_at
        if trial_ends_at and trial_ends_at.tzinfo is None:
            trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)

        if not trial_ends_at or now > trial_ends_at:
            return {
                "is_trial_active": False,
                "days_left": 0,
                "trial_ends_at": trial_ends_at.isoformat() if trial_ends_at else None,
                "premium_daily_chars_left": 0,
                "premium_total_chars_left": 0,
                "free_daily_chars_left": settings.FREE_FALLBACK_DAILY_CHARS,
                "current_engine": "free",
                "ineligibility_reason": "trial_expired",
            }

        days_left = max(0, (trial_ends_at - now).days + 1)

        # Retrieve today's quota record
        today_record = (
            db.query(UserQuota)
            .filter(UserQuota.user_id == user.id, UserQuota.date == today_str)
            .first()
        )
        daily_premium_used = today_record.daily_premium_chars_used if today_record else 0
        daily_free_used = today_record.daily_free_chars_used if today_record else 0

        # Calculate overall total premium chars used across all days
        latest_total_record = (
            db.query(UserQuota)
            .filter(UserQuota.user_id == user.id)
            .order_by(UserQuota.updated_at.desc())
            .first()
        )
        total_premium_used = latest_total_record.total_premium_chars_used if latest_total_record else 0

        premium_daily_left = max(0, settings.TRIAL_DAILY_PREMIUM_CHARS - daily_premium_used)
        premium_total_left = max(0, settings.TRIAL_TOTAL_PREMIUM_CHARS - total_premium_used)
        free_daily_left = max(0, settings.FREE_FALLBACK_DAILY_CHARS - daily_free_used)

        is_eligible = (
            premium_daily_left > 0
            and premium_total_left > 0
            and not settings.PREMIUM_KILL_SWITCH
        )

        ineligibility_reason = None
        if settings.PREMIUM_KILL_SWITCH:
            ineligibility_reason = "kill_switch"
        elif premium_total_left <= 0:
            ineligibility_reason = "total_limit"
        elif premium_daily_left <= 0:
            ineligibility_reason = "daily_limit"

        return {
            "is_trial_active": True,
            "days_left": days_left,
            "trial_ends_at": trial_ends_at.isoformat(),
            "premium_daily_chars_left": premium_daily_left,
            "premium_total_chars_left": premium_total_left,
            "free_daily_chars_left": free_daily_left,
            "current_engine": "premium" if is_eligible else "free",
            "ineligibility_reason": ineligibility_reason,
        }

    @staticmethod
    def check_premium_eligibility(
        db: Session,
        user: Optional[User],
        requested_chars: int,
    ) -> Tuple[bool, Optional[str]]:
        """
        Determines whether a synthesis request is allowed to use the premium provider.
        Returns: (is_eligible: bool, fallback_reason: Optional[str])
        """
        if settings.PREMIUM_KILL_SWITCH:
            return False, "kill_switch"

        if not user:
            return False, "unauthenticated"

        if not user.is_verified:
            return False, "unverified"

        # Check single-request character limit for premium tier
        if requested_chars > settings.MAX_CHARS_PER_REQUEST_PREMIUM:
            return False, "max_chars_exceeded"

        now = datetime.now(timezone.utc)
        trial_ends_at = user.trial_ends_at
        if trial_ends_at and trial_ends_at.tzinfo is None:
            trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)

        if not trial_ends_at or now > trial_ends_at:
            return False, "trial_expired"

        today_str = get_current_utc_date()

        # Check Global Spend Cap
        global_rec = db.query(GlobalSpend).filter(GlobalSpend.date == today_str).first()
        current_daily_spend = global_rec.total_spend_inr if global_rec else 0.0
        if current_daily_spend >= settings.GLOBAL_DAILY_PREMIUM_SPEND_CAP_INR:
            return False, "global_budget"

        # Check User Daily Quota
        today_record = (
            db.query(UserQuota)
            .filter(UserQuota.user_id == user.id, UserQuota.date == today_str)
            .first()
        )
        daily_used = today_record.daily_premium_chars_used if today_record else 0
        if daily_used + requested_chars > settings.TRIAL_DAILY_PREMIUM_CHARS:
            return False, "daily_limit"

        # Check User Lifetime Quota
        latest_record = (
            db.query(UserQuota)
            .filter(UserQuota.user_id == user.id)
            .order_by(UserQuota.updated_at.desc())
            .first()
        )
        total_used = latest_record.total_premium_chars_used if latest_record else 0
        if total_used + requested_chars > settings.TRIAL_TOTAL_PREMIUM_CHARS:
            return False, "total_limit"

        return True, None

    @staticmethod
    def deduct_quota_atomic(
        db: Session,
        user_id: Optional[str],
        engine_used: str,
        chars_synthesized: int,
    ) -> None:
        """
        Atomically records synthesized character consumption.
        Cached segments (chars_synthesized = 0) do not consume quota.
        """
        if chars_synthesized <= 0 or not user_id:
            return

        today_str = get_current_utc_date()

        # Atomic transaction execution with SQLite locking
        try:
            # Acquire exclusive write lock to prevent race conditions
            db.execute(text("BEGIN IMMEDIATE"))
        except Exception:
            # If already inside transaction, continue
            pass

        try:
            today_record = (
                db.query(UserQuota)
                .filter(UserQuota.user_id == user_id, UserQuota.date == today_str)
                .with_for_update() if "sqlite" not in settings.DATABASE_URL
                else db.query(UserQuota)
                .filter(UserQuota.user_id == user_id, UserQuota.date == today_str)
            ).first()

            # Find previous total
            prev_record = (
                db.query(UserQuota)
                .filter(UserQuota.user_id == user_id)
                .order_by(UserQuota.id.desc())
                .first()
            )
            prev_total = prev_record.total_premium_chars_used if prev_record else 0

            if not today_record:
                today_record = UserQuota(
                    user_id=user_id,
                    date=today_str,
                    daily_premium_chars_used=chars_synthesized if engine_used == "premium" else 0,
                    total_premium_chars_used=prev_total + (chars_synthesized if engine_used == "premium" else 0),
                    daily_free_chars_used=chars_synthesized if engine_used == "free" else 0,
                )
                db.add(today_record)
            else:
                if engine_used == "premium":
                    today_record.daily_premium_chars_used += chars_synthesized
                    today_record.total_premium_chars_used += chars_synthesized
                else:
                    today_record.daily_free_chars_used += chars_synthesized

            # Update Global Spend if premium
            if engine_used == "premium":
                global_rec = db.query(GlobalSpend).filter(GlobalSpend.date == today_str).first()
                spend_incurred = chars_synthesized * COST_PER_PREMIUM_CHAR_INR
                if not global_rec:
                    global_rec = GlobalSpend(
                        date=today_str,
                        total_spend_inr=spend_incurred,
                        total_chars_synthesized=chars_synthesized,
                    )
                    db.add(global_rec)
                else:
                    global_rec.total_spend_inr += spend_incurred
                    global_rec.total_chars_synthesized += chars_synthesized

            db.commit()
        except Exception as e:
            db.rollback()
            raise e
