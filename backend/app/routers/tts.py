from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Optional
from pathlib import Path
import os

from ..database import get_db
from ..models import Voice, AudioGeneration
from ..services.audio_service import AudioService
from ..config import settings

router = APIRouter(prefix="/api", tags=["TTS"])

class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=settings.MAX_CHAR_LIMIT, description="Text to synthesize in Hindi or Hinglish")
    voice_id: str = Field("neeraj", description="Voice ID from voice library")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speech rate (0.5 to 2.0)")
    pitch: float = Field(1.0, ge=0.5, le=1.5, description="Speech pitch (0.5 to 1.5)")
    stability: float = Field(0.5, ge=0.0, le=1.0, description="Voice stability/clarity")
    format: str = Field("wav", pattern="^(wav|mp3)$", description="Audio format")
    provider: Optional[str] = Field(None, description="Optional provider override")

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

@router.post("/tts", response_model=TTSResponse)
async def generate_tts(req: TTSRequest, db: Session = Depends(get_db)):
    # Validate voice exists
    voice = db.query(Voice).filter(Voice.id == req.voice_id.lower()).first()
    if not voice:
        # Check if voices need to be seeded
        from .voices import seed_default_voices
        seed_default_voices(db)
        voice = db.query(Voice).filter(Voice.id == req.voice_id.lower()).first()
        if not voice:
            raise HTTPException(status_code=404, detail=f"Voice '{req.voice_id}' not found.")

    provider_to_use = req.provider or voice.provider or settings.DEFAULT_PROVIDER

    filename, file_url, duration, was_cached = await AudioService.generate_speech(
        text=req.text,
        voice_id=voice.id,
        speed=req.speed,
        pitch=req.pitch,
        stability=req.stability,
        audio_format=req.format,
        provider_name=provider_to_use
    )

    download_url = f"/api/audio/{filename}?download=true"

    return TTSResponse(
        id=filename.split(".")[0],
        filename=filename,
        audio_url=file_url,
        download_url=download_url,
        duration_seconds=duration,
        cached=was_cached,
        ai_label="AI-Generated Voice (AwaazAI)",
        voice=voice.to_dict(),
        speed=req.speed,
        pitch=req.pitch,
        stability=req.stability,
        format=req.format
    )

@router.get("/audio/{filename}")
async def get_audio_file(filename: str, download: bool = Query(False)):
    file_path = settings.AUDIO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    ext = file_path.suffix.lower().replace(".", "")
    media_type = f"audio/{ext}" if ext in ["wav", "mp3", "mpeg"] else "application/octet-stream"
    
    headers = {
        "Accept-Ranges": "bytes",
        "X-AI-Generated-Voice": "AwaazAI-Verified",
    }
    if download:
        headers["Content-Disposition"] = f'attachment; filename="awaazai_{filename}"'
    else:
        headers["Content-Disposition"] = f'inline; filename="{filename}"'

    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers=headers
    )
