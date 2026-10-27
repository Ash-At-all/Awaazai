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
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

class AudioGeneration(Base):
    __tablename__ = "audio_generations"

    id = Column(String, primary_key=True, index=True)
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
    created_at = Column(DateTime, default=datetime.utcnow)

class PronunciationRule(Base):
    __tablename__ = "pronunciation_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, unique=True, index=True, nullable=False)
    spoken_form = Column(String, nullable=False)
    language = Column(String, default="hinglish")
    created_at = Column(DateTime, default=datetime.utcnow)
