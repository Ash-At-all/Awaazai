import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..config import settings
from ..services.auth_service import (
    normalize_email,
    is_disposable_domain,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    generate_verification_token,
    _hasher,
)
from ..services.quota_service import QuotaService

router = APIRouter(prefix="/api/auth", tags=["Authentication & Trial"])

# In-memory IP signup tracking to mitigate automated trial abuse
_ip_signup_history = {}

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

class VerifyEmailRequest(BaseModel):
    token: str = Field(..., min_length=10)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)

def get_optional_user(
    request: Request,
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Extracts user from httpOnly cookie or Authorization Bearer header.
    Returns None if unauthenticated without raising an exception.
    """
    token = request.cookies.get("awaazai_session")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

    if not token:
        return None

    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        return None

    return db.query(User).filter(User.id == payload["sub"]).first()

def get_current_user(
    user: Optional[User] = Depends(get_optional_user)
) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required."
        )
    return user

def require_admin(
    user: User = Depends(get_current_user)
) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required."
        )
    return user

@router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(req: SignupRequest, request: Request, db: Session = Depends(get_db)):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "127.0.0.1").split(",")[0].strip()

    # Per-IP Signup Rate Limit (max 5 accounts per 10 minutes)
    now = datetime.now(timezone.utc).timestamp()
    if client_ip in _ip_signup_history:
        _ip_signup_history[client_ip] = [t for t in _ip_signup_history[client_ip] if t > now - 600]
        if len(_ip_signup_history[client_ip]) >= 5:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many signups from this network. Please try again later."
            )
    else:
        _ip_signup_history[client_ip] = []

    # 1. Reject disposable/temporary emails
    if is_disposable_domain(req.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Temporary or disposable email domains are not permitted for free trials."
        )

    # 2. Normalize email (Gmail dots & plus-aliases) to enforce one trial per person
    norm_email = normalize_email(req.email)

    # 3. Check for existing account
    existing = db.query(User).filter(
        (User.email == req.email.lower()) | (User.normalized_email == norm_email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # 4. Hash password with Argon2id
    pwd_hash = hash_password(req.password)
    v_token, v_expiry = generate_verification_token()

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    user = User(
        id=user_id,
        email=req.email.lower(),
        normalized_email=norm_email,
        hashed_password=pwd_hash,
        role="user",
        is_verified=False,
        verification_token=v_token,
        verification_token_expires_at=v_expiry,
        trial_started_at=None,
        trial_ends_at=None,
    )
    db.add(user)
    db.commit()

    _ip_signup_history[client_ip].append(now)

    return {
        "message": "Account created. Please verify your email to activate your 30-day premium trial.",
        "user_id": user_id,
        "email": user.email,
        "verification_token": v_token  # Provided for immediate verification in test/dev
    }

@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.verification_token == req.token).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token."
        )

    now = datetime.utcnow()
    if user.verification_token_expires_at and now > user.verification_token_expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one."
        )

    # Activate 30-day trial in UTC strictly on verification
    user.is_verified = True
    user.verification_token = None
    user.verification_token_expires_at = None
    user.trial_started_at = datetime.utcnow()
    user.trial_ends_at = user.trial_started_at + timedelta(days=settings.TRIAL_DAYS)
    db.commit()

    # Issue JWT session cookie
    token = create_access_token(user.id, user.email, user.role)
    response.set_cookie(
        key="awaazai_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    quota = QuotaService.get_user_quota_summary(db, user)
    return {
        "message": f"Email verified! Your {settings.TRIAL_DAYS}-day premium trial is now active.",
        "user": user.to_dict(),
        "quota": quota,
        "token": token
    }

@router.post("/login")
def login(req: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.lower()).first()

    now = datetime.utcnow()
    if user and user.locked_until and now < user.locked_until:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to multiple failed login attempts. Please try again later."
        )

    # Timing-safe comparison to prevent username enumeration
    if not user:
        # Perform dummy verify to simulate constant-time work
        _hasher.verify("$argon2id$v=19$m=65536,t=2,p=1$c29tZXNhbHQ$7sK7Gz10qf0sZt3gG9u2Ew", "dummy")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    if not verify_password(user.hashed_password, req.password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = now + timedelta(minutes=15)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password."
        )

    # Successful login: reset failed counter
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()

    token = create_access_token(user.id, user.email, user.role)
    response.set_cookie(
        key="awaazai_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=not settings.DEBUG,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )

    quota = QuotaService.get_user_quota_summary(db, user)
    return {
        "message": "Login successful.",
        "user": user.to_dict(),
        "quota": quota,
        "token": token
    }

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("awaazai_session")
    return {"message": "Successfully logged out."}

@router.get("/me")
def get_me(user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    if not user:
        return {
            "authenticated": False,
            "user": None,
            "quota": {
                "is_trial_active": False,
                "days_left": 0,
                "premium_daily_chars_left": 0,
                "premium_total_chars_left": 0,
                "free_daily_chars_left": settings.FREE_FALLBACK_DAILY_CHARS,
                "current_engine": "free",
                "ineligibility_reason": "unauthenticated"
            }
        }

    quota = QuotaService.get_user_quota_summary(db, user)
    return {
        "authenticated": True,
        "user": user.to_dict(),
        "quota": quota
    }
