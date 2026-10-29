import re
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
import os

from ..database import get_db
from ..models import Voice, AudioGeneration, User
from ..services.audio_service import AudioService
from ..services.quota_service import QuotaService
from ..routers.auth import get_optional_user
from ..routers.voices import PREMIUM_VOICE_IDS, PREMIUM_SPEAKER_NAMES
from ..config import settings

router = APIRouter(prefix="/api", tags=["TTS"])

# Safe alphanumeric + hyphen/underscore filename matcher
SAFE_FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+\.(wav|mp3)$")

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=settings.MAX_CHAR_LIMIT, description="Text to synthesize in Hindi or Hinglish")
    voice_id: str = Field("neeraj", max_length=50, description="Voice ID from voice library")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech rate (0.5 to 2.0)")
    pitch: float = Field(1.0, ge=0.5, le=1.5, description="Speech pitch (0.5 to 1.5)")
    stability: float = Field(0.5, ge=0.0, le=1.0, description="Voice stability/clarity")
    format: str = Field("wav", pattern="^(wav|mp3)$", description="Audio format")
    provider: Optional[str] = Field(None, max_length=50, description="Optional provider override")

    @field_validator("voice_id")
    @classmethod
    def sanitize_voice_id(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[a-z0-9_-]+$", clean):
            raise ValueError("Voice ID must contain only alphanumeric characters, underscores, or hyphens.")
        return clean

class TTSResponse(BaseModel):
    id: str
    filename: str
    audio_url: str
    download_url: str
    duration_seconds: float
    cached: bool
    ai_label: str
    voice: dict
    speed: float
    pitch: float
    stability: float
    format: str
    engine_used: str = "free"  # "premium" or "free"
    fallback_reason: Optional[str] = None  # None, "trial_expired", "daily_limit", "total_limit", "provider_error", etc.

@router.post("/tts", response_model=TTSResponse)
async def generate_tts(
    req: TTSRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    clean_voice_id = req.voice_id.lower()

    # Reject non-allowlisted premium voice IDs upfront
    if (clean_voice_id.startswith("sarvam_") or req.provider == "sarvam") and (
        clean_voice_id not in PREMIUM_VOICE_IDS and clean_voice_id not in PREMIUM_SPEAKER_NAMES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Voice '{clean_voice_id}' is not in the curated premium voice allowlist."
        )

    # 1. Validate voice exists in DB
    voice = db.query(Voice).filter(Voice.id == clean_voice_id).first()
    if not voice:
        from .voices import seed_default_voices
        seed_default_voices(db)
        voice = db.query(Voice).filter(Voice.id == clean_voice_id).first()
        if not voice:
            raise HTTPException(status_code=404, detail=f"Voice '{req.voice_id}' not found.")

    is_premium_requested = (voice.tier == "premium" or req.provider == "sarvam" or clean_voice_id.startswith("sarvam_"))
    is_fish_requested = (voice.provider == "fish" or req.provider == "fish" or clean_voice_id.startswith("fish_"))

    # Server-side allowlist enforcement: Reject any non-allowlisted premium voice
    if is_premium_requested and clean_voice_id not in PREMIUM_VOICE_IDS and clean_voice_id not in PREMIUM_SPEAKER_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Voice '{clean_voice_id}' is not in the curated premium voice allowlist."
        )

    requested_chars = len(req.text.strip())
    engine_to_use = "free"
    fallback_reason = None
    target_provider = "mock"
    target_voice_id = voice.id

    if is_fish_requested:
        target_provider = "fish"
        target_voice_id = voice.id
        engine_to_use = "fish_s2.1"
    elif is_premium_requested:
        is_eligible, ineligibility_reason = QuotaService.check_premium_eligibility(db, user, requested_chars)
        if is_eligible:
            engine_to_use = "premium"
            target_provider = "sarvam"
            target_voice_id = voice.id
        else:
            engine_to_use = "free"
            fallback_reason = ineligibility_reason
            target_provider = "mock"
            # Map to matching free fallback voice if available
            target_voice_id = "priya" if voice.gender == "female" else "neeraj"
    else:
        target_provider = req.provider or voice.provider or settings.DEFAULT_PROVIDER
        target_voice_id = voice.id

    # 2. Execute synthesis with automatic fallback
    try:
        filename, file_url, duration, was_cached = await AudioService.generate_speech(
            text=req.text,
            voice_id=target_voice_id,
            speed=req.speed,
            pitch=req.pitch,
            stability=req.stability,
            audio_format=req.format,
            provider_name=target_provider
        )
    except Exception as exc:
        # Graceful fallback: If premium synthesis errors, switch to Edge-TTS without deducting quota
        if engine_to_use == "premium":
            engine_to_use = "free"
            fallback_reason = "provider_error"
            fallback_voice = "priya" if voice.gender == "female" else "neeraj"
            filename, file_url, duration, was_cached = await AudioService.generate_speech(
                text=req.text,
                voice_id=fallback_voice,
                speed=req.speed,
                pitch=req.pitch,
                stability=req.stability,
                audio_format=req.format,
                provider_name="mock"
            )
        else:
            raise exc

    # 3. Quota deduction (only when NOT cached and user is authenticated)
    if not was_cached and user:
        QuotaService.deduct_quota_atomic(
            db=db,
            user_id=user.id,
            engine_used=engine_to_use,
            chars_synthesized=requested_chars
        )

    download_url = f"/api/audio/{filename}?download=true"

    return TTSResponse(
        id=filename.split(".")[0],
        filename=filename,
        audio_url=file_url,
        download_url=download_url,
        duration_seconds=duration,
        cached=was_cached,
        ai_label=f"AI-Generated Voice ({engine_to_use.title()} Tier - AwaazAI)",
        voice=voice.to_dict(),
        speed=req.speed,
        pitch=req.pitch,
        stability=req.stability,
        format=req.format,
        engine_used=engine_to_use,
        fallback_reason=fallback_reason
    )

@router.get("/audio/{filename}")
async def get_audio_file(filename: str, download: bool = Query(False)):
    # 1. Enforce strict filename whitelist regex to prevent traversal sequences
    if not SAFE_FILENAME_REGEX.match(filename):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid audio filename format."
        )

    # 2. Canonical path resolution and boundary verification
    base_dir = settings.AUDIO_DIR.resolve()
    requested_file = (base_dir / filename).resolve()

    try:
        # Guarantee requested path is strictly within the audio directory
        if not requested_file.is_relative_to(base_dir):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied."
            )
    except AttributeError:
        # Fallback for Python versions without is_relative_to
        if os.path.commonpath([str(base_dir), str(requested_file)]) != str(base_dir):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    if not requested_file.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audio file not found.")

    ext = requested_file.suffix.lower().replace(".", "")
    media_type = f"audio/{ext}" if ext in ["wav", "mp3", "mpeg"] else "application/octet-stream"
    
    headers = {
        "Accept-Ranges": "bytes",
        "X-AI-Generated-Voice": "AwaazAI-Verified",
        "Cache-Control": "public, max-age=86400, immutable" if not download else "no-cache",
    }
    safe_download_name = f"awaazai_{filename}"
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{safe_download_name}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'

    return FileResponse(
        path=str(requested_file),
        media_type=media_type,
        headers=headers
    )
