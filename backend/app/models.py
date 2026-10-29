from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, Integer, Text
from .database import Base

class Voice(Base):
    __tablename__ = "voices"

    id = Column(String, primary_key=True, index=True)
    display_name = Column(String, nullable=False)
    provider = Column(String, default="mock", nullable=False)
    provider_voice_id = Column(String, nullable=False)
    gender = Column(String, nullable=False)  # "male", "female"
    age_style = Column(String, default="young adult")  # "young adult", "middle aged", "senior"
    tone = Column(String, default="conversational")  # "calm", "energetic", "news", "storytelling", "conversational"
    language = Column(String, default="Hindi / Hinglish")  # "Hindi", "Hinglish", "Hindi / Hinglish"
    accent = Column(String, default="Delhi Urban")
    description = Column(Text, default="")
    sample_text = Column(Text, default="नमस्ते, मैं आवाज़ एआई की एक आवाज़ हूँ।")
    sample_url = Column(String, default="")
    license_type = Column(String, nullable=False)  # Required
    consent_proof_url = Column(String, nullable=False)  # Required
    is_published = Column(Boolean, default=True)
    avatar_color = Column(String, default="from-amber-500 to-orange-600")
    tier = Column(String, default="free", nullable=False)  # "free" or "premium"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "display_name": self.display_name,
            "provider": self.provider,
            "provider_voice_id": self.provider_voice_id,
            "gender": self.gender,
            "age_style": self.age_style,
            "tone": self.tone,
            "language": self.language,
            "accent": self.accent,
            "description": self.description,
            "sample_text": self.sample_text,
            "sample_url": self.sample_url,
            "license_type": self.license_type,
            "consent_proof_url": self.consent_proof_url,
            "is_published": self.is_published,
            "avatar_color": self.avatar_color,
            "tier": self.tier or "free",
            "is_active": self.is_active if self.is_active is not None else True,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class AudioGeneration(Base):
    __tablename__ = "audio_generations"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, index=True, nullable=True)  # Nullable for anonymous/legacy generations
    voice_id = Column(String, index=True)
    text = Column(Text, nullable=False)
    normalized_text = Column(Text, default="")
    file_path = Column(String, nullable=False)
    file_url = Column(String, nullable=False)
    file_hash = Column(String, index=True)
    format = Column(String, default="wav")
    speed = Column(Float, default=1.0)
    pitch = Column(Float, default=1.0)
    stability = Column(Float, default=0.5)
    duration_seconds = Column(Float, default=0.0)
    is_conversation = Column(Boolean, default=False)
    engine_used = Column(String, default="free")  # "premium" or "free"
    fallback_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    normalized_email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="user", nullable=False)  # "user" or "admin"
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String, nullable=True, index=True)
    verification_token_expires_at = Column(DateTime, nullable=True)
    trial_started_at = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "role": self.role,
            "is_verified": self.is_verified,
            "trial_started_at": self.trial_started_at.isoformat() if self.trial_started_at else None,
            "trial_ends_at": self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class UserQuota(Base):
    __tablename__ = "user_quotas"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, index=True, nullable=False)
    date = Column(String, index=True, nullable=False)  # UTC date "YYYY-MM-DD"
    daily_premium_chars_used = Column(Integer, default=0, nullable=False)
    total_premium_chars_used = Column(Integer, default=0, nullable=False)
    daily_free_chars_used = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class GlobalSpend(Base):
    __tablename__ = "global_spend"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(String, unique=True, index=True, nullable=False)  # UTC date "YYYY-MM-DD"
    total_spend_inr = Column(Float, default=0.0, nullable=False)
    total_chars_synthesized = Column(Integer, default=0, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PronunciationRule(Base):
    __tablename__ = "pronunciation_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, unique=True, index=True, nullable=False)
    spoken_form = Column(String, nullable=False)
    language = Column(String, default="hinglish")
    created_at = Column(DateTime, default=datetime.utcnow)
