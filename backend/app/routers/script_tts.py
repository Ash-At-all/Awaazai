"""
script_tts.py
─────────────
POST /api/tts/script — multi-voice script synthesis.
GET /api/tts/script/{id}/export — timeline-accurate SRT & JSON exports.
GET /api/tts/script/{id}/stem/{artist_id} — isolated speaker stem generation.

Reuses existing AudioService and AudioStitcher.
Implements typed segments, pauses, source offsets, cost reporting, and stem exports.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Voice, User
from ..services.audio_service import AudioService
from ..services.exporter import ExporterService
from ..services.quota_service import QuotaService
from ..routers.auth import get_optional_user
from ..routers.voices import PREMIUM_VOICE_IDS, PREMIUM_SPEAKER_NAMES
from ..services.script_parser import (
    DialogueSegment,
    PauseSegment,
    count_spoken_characters,
    parse_script,
    validate_artist_name,
)
from ..services.stitcher import AudioStitcher

router = APIRouter(prefix="/api/tts", tags=["Script TTS"])

# Safe script ID regex
SCRIPT_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")

# ── Speed mapping ──────────────────────────────────────────────────
SPEED_MAP = {
    -2: 0.50,
    -1: 0.75,
     0: 1.00,
     1: 1.25,
     2: 1.50,
     3: 2.00,
}


def map_speed(slider_value: int) -> float:
    """Convert UI slider integer to provider speed float."""
    clamped = max(-2, min(3, slider_value))
    return SPEED_MAP.get(clamped, 1.0)


# ── Request / Response models ──────────────────────────────────────
class ArtistIn(BaseModel):
    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=20)
    voice_id: str = Field(..., min_length=1, max_length=50)
    speed: int = Field(0, ge=-2, le=3)
    stability: float = Field(0.5, ge=0.0, le=1.0)

    @field_validator("name")
    @classmethod
    def check_name(cls, v: str) -> str:
        err = validate_artist_name(v)
        if err:
            raise ValueError(err)
        return v

    @field_validator("voice_id")
    @classmethod
    def sanitize_voice_id(cls, v: str) -> str:
        clean = v.strip().lower()
        if not re.match(r"^[a-z0-9_-]+$", clean):
            raise ValueError(
                "voice_id must contain only alphanumeric characters, "
                "underscores, or hyphens."
            )
        return clean


class ScriptTTSRequest(BaseModel):
    artists: List[ArtistIn] = Field(..., min_length=1, max_length=6)
    script: str = Field(..., min_length=1)
    audio_format: str = Field("wav", pattern="^(wav|mp3)$")


class SegmentOut(BaseModel):
    type: str = "dialogue"  # "dialogue" or "pause"
    artist: Optional[str] = None
    artist_id: Optional[str] = None
    text: Optional[str] = None
    start_ms: int
    end_ms: int
    duration_ms: int
    source_start: Optional[int] = None
    source_end: Optional[int] = None


class StemOut(BaseModel):
    artist_id: str
    artist_name: str
    stem_url: str


class ScriptTTSResponse(BaseModel):
    id: str
    audio_url: str
    download_url: str
    srt_url: str
    transcript_url: str
    duration_seconds: float
    segments: List[SegmentOut]
    cached: bool
    ai_label: str
    format: str
    spoken_char_count: int
    characters_submitted: int
    characters_cached: int
    characters_synthesized: int
    estimated_cost_inr: float
    stems: List[StemOut] = []
    engine_used: str = "free"
    fallback_reason: Optional[str] = None


# ── Estimation Endpoint ──────────────────────────────────────────────
@router.post("/script/estimate")
def estimate_script_tts(
    req: ScriptTTSRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """Pre-flight balance and quota check before running full generation."""
    spoken_chars = count_spoken_characters(req.script)
    from .voices import seed_default_voices
    seed_default_voices(db)

    voice_lookup: dict[str, Voice] = {}
    for artist in req.artists:
        voice = db.query(Voice).filter(Voice.id == artist.voice_id).first()
        if voice:
            voice_lookup[artist.voice_id] = voice

    # Parse segments to count premium characters
    artist_dicts = [a.model_dump() for a in req.artists]
    parse_result = parse_script(req.script, artist_dicts)

    premium_chars = 0
    for seg in parse_result.segments:
        if isinstance(seg, DialogueSegment):
            cfg = next((a for a in req.artists if a.id == seg.artist_id), None)
            if cfg and cfg.voice_id in voice_lookup:
                v = voice_lookup[cfg.voice_id]
                if v.tier in ("premium", "featured") or v.provider in ("sarvam", "elevenlabs", "fish") or cfg.voice_id.startswith(("sarvam_", "eleven_", "fish_")):
                    premium_chars += len(seg.text.strip())

    is_eligible = True
    fallback_reason = None
    if premium_chars > 0:
        is_eligible, fallback_reason = QuotaService.check_premium_eligibility(
            db, user, premium_chars
        )

    quota = QuotaService.get_user_quota_summary(db, user) if user else {
        "is_trial_active": False,
        "days_left": 0,
        "premium_daily_chars_left": 0,
        "premium_total_chars_left": 0,
        "free_daily_chars_left": settings.FREE_FALLBACK_DAILY_CHARS,
        "current_engine": "free",
        "ineligibility_reason": "unauthenticated"
    }

    return {
        "spoken_chars": spoken_chars,
        "premium_chars": premium_chars,
        "estimated_cost_inr": round(premium_chars * 0.0015, 4),
        "is_eligible": is_eligible,
        "fallback_reason": fallback_reason,
        "suggest_free_fallback": not is_eligible and premium_chars > 0,
        "quota": quota
    }


# ── Generation Endpoint ─────────────────────────────────────────────
@router.post("/script", response_model=ScriptTTSResponse)
async def generate_script_tts(
    req: ScriptTTSRequest,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    # ── 1. Spoken Character Limit Validation ───────────────────
    spoken_chars = count_spoken_characters(req.script)
    if spoken_chars > settings.MAX_CHAR_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Script exceeds the {settings.MAX_CHAR_LIMIT}-character limit "
                f"(spoken text has {spoken_chars} characters, excluding @tags and pauses)."
            ),
        )
    if spoken_chars == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Script contains no spoken dialogue text.",
        )

    # ── 2. Validate Every voice_id Exists in DB ────────────────
    from .voices import seed_default_voices
    seed_default_voices(db)

    voice_lookup: dict[str, Voice] = {}
    for artist in req.artists:
        voice = db.query(Voice).filter(Voice.id == artist.voice_id).first()
        if not voice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Voice '{artist.voice_id}' not found for artist '{artist.name}'.",
            )
        voice_lookup[artist.voice_id] = voice

    # ── 3. Parse Script ─────────────────────────────────────────
    artist_dicts = [a.model_dump() for a in req.artists]
    parse_result = parse_script(req.script, artist_dicts)

    if parse_result.errors:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=" | ".join(parse_result.errors),
        )

    parsed_segments = parse_result.segments
    if not parsed_segments:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parser produced no segments — check your script.",
        )

    artist_config = {a.id: a for a in req.artists}

    # ── 4. Verify Allowlist & Check Quota for Premium Artists ───
    total_premium_chars = 0
    has_premium_artist = False
    for seg in parsed_segments:
        if isinstance(seg, DialogueSegment):
            cfg = artist_config[seg.artist_id]
            v = voice_lookup[cfg.voice_id]
            clean_vid = cfg.voice_id.lower()
            if v.tier in ("premium", "featured") or v.provider in ("sarvam", "elevenlabs", "fish") or clean_vid.startswith(("sarvam_", "eleven_", "fish_")):
                has_premium_artist = True
                if clean_vid not in PREMIUM_VOICE_IDS and clean_vid not in PREMIUM_SPEAKER_NAMES:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Voice '{cfg.voice_id}' for artist '{cfg.name}' is not in the curated premium voice allowlist."
                    )
                total_premium_chars += len(seg.text.strip())

    script_engine = "free"
    script_fallback_reason = None

    if has_premium_artist:
        is_eligible, reason = QuotaService.check_premium_eligibility(db, user, total_premium_chars)
        if is_eligible:
            script_engine = "premium"
        else:
            script_engine = "free"
            script_fallback_reason = reason

    # ── 5. Synthesize Dialogue Segments & Prepare Timeline ──────
    stitch_items = []
    segment_outputs: list[SegmentOut] = []
    internal_meta_segments: list[dict] = []
    cursor_ms = 0
    any_cached = True
    spoken_chunks_count = 0

    chars_cached = 0
    chars_synthesized = 0

    for i, seg in enumerate(parsed_segments):
        if isinstance(seg, PauseSegment):
            dur_ms = seg.duration_ms
            stitch_items.append({"type": "pause", "duration_ms": dur_ms})
            seg_dict = {
                "type": "pause",
                "artist": None,
                "artist_id": None,
                "text": None,
                "start_ms": cursor_ms,
                "end_ms": cursor_ms + dur_ms,
                "duration_ms": dur_ms,
                "source_start": seg.source_start,
                "source_end": seg.source_end,
                "chunk_path": None,
            }
            segment_outputs.append(SegmentOut(**{k: v for k, v in seg_dict.items() if k != "chunk_path"}))
            internal_meta_segments.append(seg_dict)
            cursor_ms += dur_ms
        elif isinstance(seg, DialogueSegment):
            cfg = artist_config[seg.artist_id]
            voice = voice_lookup[cfg.voice_id]
            clean_vid = cfg.voice_id.lower()
            is_artist_premium = (voice.tier in ("premium", "featured") or voice.provider in ("sarvam", "elevenlabs", "fish") or clean_vid.startswith(("sarvam_", "eleven_", "fish_")))

            if is_artist_premium and script_engine == "premium":
                provider_name = voice.provider if voice.provider in ("sarvam", "elevenlabs", "fish") else "sarvam"
                voice_id_to_use = voice.provider_voice_id if provider_name in ("sarvam", "elevenlabs", "fish") else cfg.voice_id
            else:
                provider_name = "mock"
                voice_id_to_use = "priya" if voice.gender == "female" else "neeraj"

            mapped_speed = map_speed(cfg.speed)
            seg_chars = len(seg.text.strip())

            try:
                filename, file_url, duration, was_cached = (
                    await AudioService.generate_speech(
                        text=seg.text,
                        voice_id=voice_id_to_use,
                        speed=mapped_speed,
                        pitch=1.0,
                        stability=cfg.stability,
                        audio_format=req.audio_format,
                        provider_name=provider_name,
                    )
                )
            except Exception as sarvam_err:
                # Automatic failover to free generator if premium provider errors
                script_engine = "free"
                script_fallback_reason = "provider_error"
                fallback_voice = "priya" if voice.gender == "female" else "neeraj"
                try:
                    filename, file_url, duration, was_cached = (
                        await AudioService.generate_speech(
                            text=seg.text,
                            voice_id=fallback_voice,
                            speed=mapped_speed,
                            pitch=1.0,
                            stability=cfg.stability,
                            audio_format=req.audio_format,
                            provider_name="mock",
                        )
                    )
                except Exception as fallback_err:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=(
                            f"Failed to synthesize segment for '{seg.artist_name}': {fallback_err}"
                        ),
                    )

            if was_cached:
                chars_cached += seg_chars
            else:
                chars_synthesized += seg_chars
                any_cached = False

            dur_ms = int(duration * 1000)
            chunk_path = settings.AUDIO_DIR / filename
            stitch_items.append({"type": "audio", "path": chunk_path})
            spoken_chunks_count += 1

            seg_dict = {
                "type": "dialogue",
                "artist": seg.artist_name,
                "artist_id": seg.artist_id,
                "text": seg.text,
                "start_ms": cursor_ms,
                "end_ms": cursor_ms + dur_ms,
                "duration_ms": dur_ms,
                "source_start": seg.source_start,
                "source_end": seg.source_end,
                "chunk_path": str(chunk_path.resolve()),
            }
            segment_outputs.append(SegmentOut(**{k: v for k, v in seg_dict.items() if k != "chunk_path"}))
            internal_meta_segments.append(seg_dict)
            cursor_ms += dur_ms

            # Default conversational gap (300ms) between adjacent dialogue lines if not followed by explicit pause
            if i < len(parsed_segments) - 1 and isinstance(parsed_segments[i + 1], DialogueSegment):
                gap_ms = 300
                stitch_items.append({"type": "pause", "duration_ms": gap_ms})
                gap_dict = {
                    "type": "pause",
                    "artist": None,
                    "artist_id": None,
                    "text": None,
                    "start_ms": cursor_ms,
                    "end_ms": cursor_ms + gap_ms,
                    "duration_ms": gap_ms,
                    "source_start": None,
                    "source_end": None,
                    "chunk_path": None,
                }
                internal_meta_segments.append(gap_dict)
                cursor_ms += gap_ms

    # ── 5. Stitch Sequence (Audio Chunks + Explicit Pauses) ────
    if spoken_chunks_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No spoken audio chunks generated.",
        )

    try:
        final_path = AudioStitcher.stitch_sequence(
            items=stitch_items,
            output_format=req.audio_format,
        )
    except Exception as stitch_err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Audio stitching failed: {stitch_err}",
        )

    final_filename = final_path.name
    script_id = final_filename.split(".")[0]
    total_duration = AudioService.get_audio_duration(final_path)
    total_dur_ms = int(total_duration * 1000)

    # ── 6. Persist Timeline & Metadata for Exports ─────────────
    # Standard ₹0.0015 per character for commercial neural synthesis (e.g. Sarvam/Azure)
    estimated_cost = round(chars_synthesized * 0.0015, 4)

    meta_payload = {
        "id": script_id,
        "format": req.audio_format,
        "duration_seconds": total_duration,
        "duration_ms": total_dur_ms,
        "segments": internal_meta_segments,
        "artists": [a.model_dump() for a in req.artists],
        "characters_submitted": spoken_chars,
        "characters_cached": chars_cached,
        "characters_synthesized": chars_synthesized,
        "estimated_cost_inr": estimated_cost,
    }

    meta_file = settings.AUDIO_DIR / f"{script_id}_meta.json"
    temp_meta = settings.AUDIO_DIR / f".tmp_{os.getpid()}_{script_id}_meta.json"
    with open(temp_meta, "w", encoding="utf-8") as f:
        json.dump(meta_payload, f, ensure_ascii=False, indent=2)
    temp_meta.replace(meta_file)

    # ── 7. Build Stem Links ────────────────────────────────────
    stems = [
        StemOut(
            artist_id=a.id,
            artist_name=a.name,
            stem_url=f"/api/tts/script/{script_id}/stem/{a.id}",
        )
        for a in req.artists
    ]

    is_cached_final = any_cached and (final_path.exists() and final_path.stat().st_size > 0)

    # ── 8. Deduct Quota Atomically (Non-Cached Spoken Chars Only) ────
    if chars_synthesized > 0 and user:
        QuotaService.deduct_quota_atomic(
            db=db,
            user_id=user.id,
            engine_used=script_engine,
            chars_synthesized=chars_synthesized,
        )

    return ScriptTTSResponse(
        id=script_id,
        audio_url=f"/api/audio/{final_filename}",
        download_url=f"/api/audio/{final_filename}?download=true",
        srt_url=f"/api/tts/script/{script_id}/export?format=srt",
        transcript_url=f"/api/tts/script/{script_id}/export?format=json",
        duration_seconds=total_duration,
        segments=segment_outputs,
        cached=is_cached_final,
        ai_label=f"AI-Generated Multi-Voice Script ({script_engine.title()} Tier - AwaazAI)",
        format=req.audio_format,
        spoken_char_count=spoken_chars,
        characters_submitted=spoken_chars,
        characters_cached=chars_cached,
        characters_synthesized=chars_synthesized,
        estimated_cost_inr=estimated_cost,
        stems=stems,
        engine_used=script_engine,
        fallback_reason=script_fallback_reason,
    )


# ── Timeline & Subtitle Export Endpoint ─────────────────────────────
@router.get("/script/{script_id}/export")
def export_script_timeline(
    script_id: str,
    format: str = Query("srt", pattern="^(srt|json)$"),
):
    clean_id = script_id.strip()
    if not SCRIPT_ID_REGEX.match(clean_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid script ID format.")

    meta_file = settings.AUDIO_DIR / f"{clean_id}_meta.json"
    if not meta_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script session not found.")

    with open(meta_file, "r", encoding="utf-8") as f:
        meta_data = json.load(f)

    segments = meta_data.get("segments", [])
    total_duration = meta_data.get("duration_seconds", 0.0)

    if format == "srt":
        srt_content = ExporterService.generate_srt(segments)
        return Response(
            content=srt_content,
            media_type="text/plain; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="awaazai_{clean_id}.srt"',
                "X-AI-Generated-Voice": "AwaazAI-Verified",
            },
        )
    else:
        transcript = ExporterService.generate_transcript_json(
            script_id=clean_id,
            segments=segments,
            total_duration_sec=total_duration,
            metadata={
                "characters_submitted": meta_data.get("characters_submitted", 0),
                "characters_cached": meta_data.get("characters_cached", 0),
                "characters_synthesized": meta_data.get("characters_synthesized", 0),
                "estimated_cost_inr": meta_data.get("estimated_cost_inr", 0.0),
                "artists": meta_data.get("artists", []),
            },
        )
        return JSONResponse(
            content=transcript,
            headers={
                "Content-Disposition": f'attachment; filename="awaazai_{clean_id}_transcript.json"',
            },
        )


# ── Speaker Stem Download Endpoint ──────────────────────────────────
@router.get("/script/{script_id}/stem/{artist_id}")
def get_speaker_stem(
    script_id: str,
    artist_id: str,
):
    clean_script_id = script_id.strip()
    clean_artist_id = artist_id.strip()
    if not SCRIPT_ID_REGEX.match(clean_script_id) or not SCRIPT_ID_REGEX.match(clean_artist_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid identifier format.")

    meta_file = settings.AUDIO_DIR / f"{clean_script_id}_meta.json"
    if not meta_file.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Script session not found.")

    with open(meta_file, "r", encoding="utf-8") as f:
        meta_data = json.load(f)

    artists = meta_data.get("artists", [])
    artist_obj = next((a for a in artists if a.get("id") == clean_artist_id), None)
    artist_name = artist_obj["name"] if artist_obj else clean_artist_id
    audio_format = meta_data.get("format", "wav")
    total_dur_ms = meta_data.get("duration_ms", 0)

    try:
        stem_path = ExporterService.generate_speaker_stem(
            artist_id=clean_artist_id,
            artist_name=artist_name,
            segments=meta_data.get("segments", []),
            total_duration_ms=total_dur_ms,
            output_format=audio_format,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate stem: {e}")

    ext = stem_path.suffix.lower().replace(".", "")
    media_type = f"audio/{ext}" if ext in ["wav", "mp3"] else "application/octet-stream"

    return FileResponse(
        path=str(stem_path),
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="awaazai_{clean_script_id}_{artist_name}_stem.{ext}"',
            "Accept-Ranges": "bytes",
            "X-AI-Generated-Voice": "AwaazAI-Verified",
        },
    )
