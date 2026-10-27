from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pathlib import Path

from ..database import get_db
from ..models import Voice
from ..providers.factory import get_tts_provider
from ..services.audio_service import AudioService
from ..config import settings

router = APIRouter(prefix="/api/voices", tags=["Voices"])

def seed_default_voices(db: Session):
    """Seed the database with licensed Indian voices if empty."""
    count = db.query(Voice).count()
    if count == 0:
        mock_provider = get_tts_provider("mock")
        voices_data = mock_provider.get_supported_voices()
        for v in voices_data:
            voice = Voice(
                id=v["id"],
                display_name=v["display_name"],
                provider="mock",
                provider_voice_id=v["id"],
                gender=v["gender"],
                age_style=v.get("age_style", "young adult"),
                tone=v.get("tone", "conversational"),
                language=v.get("language", "Hindi / Hinglish"),
                accent=v.get("accent", "Standard"),
                description=v.get("description", ""),
                sample_text=v.get("sample_text", "नमस्ते, मैं आवाज़ एआई की आवाज़ हूँ।"),
                sample_url=f"/api/voices/{v['id']}/sample",
                license_type=v["license_type"],
                consent_proof_url=v["consent_proof_url"],
                is_published=True,
                avatar_color=v.get("avatar_color", "from-blue-600 to-indigo-800")
            )
            db.add(voice)
        db.commit()

@router.get("")
def list_voices(
    gender: Optional[str] = Query(None, description="male or female"),
    language: Optional[str] = Query(None, description="Hindi or Hinglish"),
    tone: Optional[str] = Query(None, description="calm, energetic, news, storytelling, etc."),
    search: Optional[str] = Query(None, description="Search query by name or description"),
    db: Session = Depends(get_db)
):
    seed_default_voices(db)
    query = db.query(Voice).filter(Voice.is_published == True)

    if gender and gender.lower() != "all":
        query = query.filter(Voice.gender == gender.lower())

    if language and language.lower() != "all":
        # Matches if voice language contains query
        query = query.filter(Voice.language.ilike(f"%{language}%"))

    if tone and tone.lower() != "all":
        query = query.filter(Voice.tone.ilike(f"%{tone}%"))

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            (Voice.display_name.ilike(search_fmt)) |
            (Voice.description.ilike(search_fmt)) |
            (Voice.id.ilike(search_fmt))
        )

    voices = query.all()
    return [v.to_dict() for v in voices]

@router.get("/{voice_id}")
def get_voice(voice_id: str, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id.lower()).first()
    if not voice:
        raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found")
    return voice.to_dict()

@router.get("/{voice_id}/sample")
async def get_voice_sample(voice_id: str, db: Session = Depends(get_db)):
    voice = db.query(Voice).filter(Voice.id == voice_id.lower()).first()
    if not voice:
        seed_default_voices(db)
        voice = db.query(Voice).filter(Voice.id == voice_id.lower()).first()
        if not voice:
            raise HTTPException(status_code=404, detail=f"Voice '{voice_id}' not found")

    sample_filename = f"sample_{voice.id}.wav"
    sample_path = settings.SAMPLE_DIR / sample_filename

    if not sample_path.exists() or sample_path.stat().st_size == 0:
        filename, _, _, _ = await AudioService.generate_speech(
            text=voice.sample_text,
            voice_id=voice.id,
            speed=1.0,
            pitch=1.0,
            stability=0.5,
            audio_format="wav",
            provider_name=voice.provider
        )
        src_path = settings.AUDIO_DIR / filename
        sample_path.write_bytes(src_path.read_bytes())

    return FileResponse(
        path=str(sample_path),
        media_type="audio/wav",
        headers={"Content-Disposition": f'inline; filename="{sample_filename}"'}
    )
