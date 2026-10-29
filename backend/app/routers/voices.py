import re
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from pathlib import Path
import os

from ..database import get_db
from ..models import Voice
from ..providers.factory import get_tts_provider
from ..providers.fish_audio_provider import FISH_FEATURED_VOICES
from ..services.audio_service import AudioService
from ..config import settings

router = APIRouter(prefix="/api/voices", tags=["Voices"])

VOICE_ID_REGEX = re.compile(r"^[a-z0-9_-]{1,50}$")

CURATED_PREMIUM_VOICES = [
    {
        "id": "sarvam_shubh",
        "display_name": "Shubh (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "shubh",
        "gender": "male",
        "age_style": "middle aged",
        "tone": "news",
        "language": "Hindi / Hinglish",
        "accent": "Standard Hindi",
        "description": "Authoritative and articulate male voice ideal for news, business, and formal narrations.",
        "sample_text": "नमस्ते, यह सर्वम एआई का शुभ वॉइस मॉडल है।",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-shubh",
        "tier": "premium",
        "avatar_color": "from-amber-500 to-orange-600"
    },
    {
        "id": "sarvam_aditya",
        "display_name": "Aditya (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "aditya",
        "gender": "male",
        "age_style": "young adult",
        "tone": "storytelling",
        "language": "Hindi / Hinglish",
        "accent": "Delhi Urban",
        "description": "Deep and resonant male voice perfect for audiobooks and dramatic scripts.",
        "sample_text": "नमस्ते, मैं आदित्य हूँ। कहानियों और संवादों के लिए उत्कृष्ट।",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-aditya",
        "tier": "premium",
        "avatar_color": "from-blue-600 to-indigo-800"
    },
    {
        "id": "sarvam_rahul",
        "display_name": "Rahul (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "rahul",
        "gender": "male",
        "age_style": "young adult",
        "tone": "conversational",
        "language": "Hindi / Hinglish",
        "accent": "Urban Hinglish",
        "description": "Energetic, modern, and casual tone suitable for YouTube videos and podcasts.",
        "sample_text": "नमस्ते दोस्तों, राहुल की आवाज़ में आपका स्वागत है।",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-rahul",
        "tier": "premium",
        "avatar_color": "from-purple-600 to-pink-600"
    },
    {
        "id": "sarvam_ashutosh",
        "display_name": "Ashutosh (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "ashutosh",
        "gender": "male",
        "age_style": "middle aged",
        "tone": "documentary",
        "language": "Hindi / Hinglish",
        "accent": "Standard Hindi",
        "description": "Calm, deep, and trustworthy voice designed for informative and historical scripts.",
        "sample_text": "नमस्कार, आशुतोष की वाणी में ज्ञान और गंभीरता का संगम है।",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-ashutosh",
        "tier": "premium",
        "avatar_color": "from-emerald-600 to-teal-800"
    },
    {
        "id": "sarvam_rohan",
        "display_name": "Rohan (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "rohan",
        "gender": "male",
        "age_style": "young adult",
        "tone": "conversational",
        "language": "Hindi / Hinglish",
        "accent": "North Indian",
        "description": "Friendly and relatable male tone suitable for peer dialogue and customer support.",
        "sample_text": "अरे भाई! रोहन यहाँ है, बताओ आज क्या नया बनाना है?",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-rohan",
        "tier": "premium",
        "avatar_color": "from-cyan-600 to-blue-700"
    },
    {
        "id": "sarvam_priya",
        "display_name": "Priya (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "priya",
        "gender": "female",
        "age_style": "young adult",
        "tone": "conversational",
        "language": "Hindi / Hinglish",
        "accent": "Delhi Urban",
        "description": "Crystal-clear, warm female voice ideal for conversations and advertisements.",
        "sample_text": "नमस्ते! मैं प्रिया हूँ, आपकी पसंदीदा आवाज़।",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-priya",
        "tier": "premium",
        "avatar_color": "from-rose-500 to-pink-700"
    },
    {
        "id": "sarvam_ritu",
        "display_name": "Ritu (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "ritu",
        "gender": "female",
        "age_style": "middle aged",
        "tone": "storytelling",
        "language": "Hindi / Hinglish",
        "accent": "Standard Hindi",
        "description": "Expressive and melodic female voice, perfect for emotional narrations.",
        "sample_text": "नमस्ते, ऋतु की आवाज़ में भावना और मिठास है।",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-ritu",
        "tier": "premium",
        "avatar_color": "from-violet-600 to-purple-800"
    },
    {
        "id": "sarvam_neha",
        "display_name": "Neha (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "neha",
        "gender": "female",
        "age_style": "young adult",
        "tone": "energetic",
        "language": "Hindi / Hinglish",
        "accent": "Urban Hinglish",
        "description": "Upbeat, youthful female voice ideal for social media and marketing.",
        "sample_text": "हाय एवरीवन! नेहा यहाँ है, चलिए कुछ नया और क्रिएटिव करते हैं!",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-neha",
        "tier": "premium",
        "avatar_color": "from-fuchsia-500 to-rose-600"
    },
    {
        "id": "sarvam_kavya",
        "display_name": "Kavya (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "kavya",
        "gender": "female",
        "age_style": "young adult",
        "tone": "calm",
        "language": "Hindi / Hinglish",
        "accent": "Standard Hindi",
        "description": "Soft, calm, and soothing female voice suited for meditation and mindfulness.",
        "sample_text": "नमस्ते, काव्या के साथ शांति और विश्राम का अनुभव करें।",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-kavya",
        "tier": "premium",
        "avatar_color": "from-teal-500 to-emerald-700"
    },
    {
        "id": "sarvam_shreya",
        "display_name": "Shreya (Premium)",
        "provider": "sarvam",
        "provider_voice_id": "shreya",
        "gender": "female",
        "age_style": "young adult",
        "tone": "news",
        "language": "Hindi / Hinglish",
        "accent": "Standard Hindi",
        "description": "Sharp, articulate, and poised voice for broadcast journalism and podcasts.",
        "sample_text": "नमस्कार, श्रेया के साथ आज के मुख्य समाचार और विश्लेषण।",
        "license_type": "Commercial - AwaazAI Premium",
        "consent_proof_url": "https://awaazai.com/legal/consent/sarvam-shreya",
        "tier": "premium",
        "avatar_color": "from-amber-600 to-yellow-600"
    }
]

PREMIUM_VOICE_IDS = {v["id"] for v in CURATED_PREMIUM_VOICES}
PREMIUM_SPEAKER_NAMES = {v["provider_voice_id"] for v in CURATED_PREMIUM_VOICES}

def seed_default_voices(db: Session):
    """Seed the database with free and exactly 10 premium Indian voices."""
    # 1. Seed Free Voices if missing
    existing_ids = {r[0] for r in db.query(Voice.id).all()}
    
    mock_provider = get_tts_provider("mock")
    voices_data = mock_provider.get_supported_voices()
    for v in voices_data:
        if v["id"] not in existing_ids:
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
                avatar_color=v.get("avatar_color", "from-blue-600 to-indigo-800"),
                tier="free",
                is_active=True
            )
            db.add(voice)
            existing_ids.add(v["id"])

    # 2. Seed Exactly 10 Premium Voices
    for pv in CURATED_PREMIUM_VOICES:
        if pv["id"] not in existing_ids:
            voice = Voice(
                id=pv["id"],
                display_name=pv["display_name"],
                provider=pv["provider"],
                provider_voice_id=pv["provider_voice_id"],
                gender=pv["gender"],
                age_style=pv["age_style"],
                tone=pv["tone"],
                language=pv["language"],
                accent=pv["accent"],
                description=pv["description"],
                sample_text=pv["sample_text"],
                sample_url=f"/api/voices/{pv['id']}/sample",
                license_type=pv["license_type"],
                consent_proof_url=pv["consent_proof_url"],
                is_published=True,
                avatar_color=pv["avatar_color"],
                tier="premium",
                is_active=True
            )
            db.add(voice)
            existing_ids.add(pv["id"])

    # 3. Seed Fish Audio Featured Voices
    for fv in FISH_FEATURED_VOICES:
        if fv["id"] not in existing_ids:
            voice = Voice(
                id=fv["id"],
                display_name=fv["display_name"],
                provider="fish",
                provider_voice_id=fv["reference_id"],
                gender=fv["gender"],
                age_style=fv["age_style"],
                tone=fv["tone"],
                language=fv["language"],
                accent=fv["accent"],
                description=fv["description"],
                sample_text=fv["sample_text"],
                sample_url=f"/api/voices/{fv['id']}/sample",
                license_type=fv["license_type"],
                consent_proof_url=fv["consent_proof_url"],
                is_published=True,
                avatar_color=fv["avatar_color"],
                tier="featured",
                is_active=True
            )
            db.add(voice)
            existing_ids.add(fv["id"])
        else:
            # Sync updated sample_text and descriptions if already seeded
            v_obj = db.query(Voice).filter(Voice.id == fv["id"]).first()
            if v_obj:
                v_obj.sample_text = fv["sample_text"]
                v_obj.description = fv["description"]
                v_obj.tone = fv["tone"]
                v_obj.accent = fv["accent"]
    
    db.commit()

@router.get("")
def list_voices(
    gender: Optional[str] = Query(None, description="male or female"),
    language: Optional[str] = Query(None, description="Hindi or Hinglish"),
    tone: Optional[str] = Query(None, description="calm, energetic, news, storytelling, etc."),
    tier: Optional[str] = Query(None, description="free or premium"),
    search: Optional[str] = Query(None, description="Search query by name or description"),
    db: Session = Depends(get_db)
):
    seed_default_voices(db)
    query = db.query(Voice).filter(Voice.is_published == True, Voice.is_active == True)

    if tier and isinstance(tier, str) and tier.lower() != "all":
        query = query.filter(Voice.tier == tier.lower())

    if gender and isinstance(gender, str) and gender.lower() != "all":
        query = query.filter(Voice.gender == gender.lower())

    if language and isinstance(language, str) and language.lower() != "all":
        # Matches if voice language contains query
        query = query.filter(Voice.language.ilike(f"%{language}%"))

    if tone and isinstance(tone, str) and tone.lower() != "all":
        query = query.filter(Voice.tone.ilike(f"%{tone}%"))

    if search and isinstance(search, str):
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
    clean_id = voice_id.lower().strip()
    if not VOICE_ID_REGEX.match(clean_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid voice ID format.")

    voice = db.query(Voice).filter(Voice.id == clean_id).first()
    if not voice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Voice '{voice_id}' not found.")
    return voice.to_dict()

@router.get("/{voice_id}/sample")
async def get_voice_sample(voice_id: str, db: Session = Depends(get_db)):
    clean_id = voice_id.lower().strip()
    if not VOICE_ID_REGEX.match(clean_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid voice ID format.")

    voice = db.query(Voice).filter(Voice.id == clean_id).first()
    if not voice:
        seed_default_voices(db)
        voice = db.query(Voice).filter(Voice.id == clean_id).first()
        if not voice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Voice '{voice_id}' not found.")

    sample_filename = f"sample_{voice.id}.wav"
    base_dir = settings.SAMPLE_DIR.resolve()
    sample_path = (base_dir / sample_filename).resolve()

    if not sample_path.is_relative_to(base_dir):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

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
        headers={
            "Content-Disposition": f'inline; filename="{sample_filename}"',
            "Cache-Control": "public, max-age=86400",
            "X-Content-Type-Options": "nosniff"
        }
    )
