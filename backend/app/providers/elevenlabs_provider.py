"""
elevenlabs_provider.py
──────────────────────
ElevenLabs TTS provider for AwaazAI.
Drop this file into backend/app/providers/
"""

from __future__ import annotations

import io
import wave
from typing import Any, Dict, List, Optional

import httpx

from ..config import settings
from .base import TTSProvider

# ── Featured ElevenLabs voices (single source of truth) ─────────────
# Premade ElevenLabs voices work on the free plan via API.
# Swap any "voice_id" for one from your own account (run list_eleven_voices.py).
def _voice(internal_id: str, name: str, provider_id: str, gender: str,
           tone: str, description: str, color: str) -> Dict[str, str]:
    return {
        "id": internal_id,
        "display_name": f"{name} (ElevenLabs)",
        "voice_id": provider_id,
        "gender": gender,
        "age_style": "young adult",
        "tone": tone,
        "language": "Hindi / Hinglish",
        "accent": "Multilingual Hindi",
        "description": description,
        "sample_text": "नमस्ते! AwaazAI के साथ अपनी हिंदी और हिंग्लिश कहानियों को एक नई आवाज़ दें।",
        "avatar_color": color,
    }


# These IDs were checked against the configured account's available voice list.
# Its catalog no longer contains Rachel, Josh, Elli, or Antoni, so don't publish
# those stale IDs. Multilingual v2 supports Hindi for the available voices.
ELEVEN_FEATURED_VOICES = [
    _voice("eleven_sarah", "Sarah", "EXAVITQu4vr4xnSDxMaL", "female", "reassuring", "Mature, reassuring delivery for explainers and narration.", "from-emerald-500 to-teal-600"),
    _voice("eleven_adam", "Adam", "pNInz6obpgDQGcFmaJgB", "male", "narration", "Firm, deep delivery for documentaries and serious narration.", "from-sky-500 to-blue-700"),
    _voice("eleven_george", "George", "JBFqnCBsd6RMkjVDRZzb", "male", "storytelling", "Warm storyteller for audiobooks and long-form narration.", "from-amber-500 to-orange-600"),
    _voice("eleven_alice", "Alice", "Xb7hH8MSUJpSbSDYk0k2", "female", "clear", "Clear, engaging delivery for learning and announcements.", "from-purple-500 to-violet-700"),
    _voice("eleven_jessica", "Jessica", "cgSgspJ2msm6clMCkdW9", "female", "playful", "Bright, playful voice for social content and lively dialogue.", "from-fuchsia-500 to-purple-600"),
    _voice("eleven_liam", "Liam", "TX3LPaxmHKxFdv7VOQHJ", "male", "energetic", "Energetic creator style for reels, shorts, and vlogs.", "from-indigo-500 to-violet-700"),
    _voice("eleven_matilda", "Matilda", "XrExE9yKIg1WjnnlVkGX", "female", "professional", "Polished, professional delivery for presentations and explainers.", "from-rose-500 to-pink-700"),
    _voice("eleven_lily", "Lily", "pFZP5JQG7iQjIQuC4Bku", "female", "expressive", "Expressive, smooth delivery for stories and character dialogue.", "from-pink-500 to-rose-600"),
    _voice("eleven_bella_v2", "Bella", "hpp4J3VqNfWAUOO0d1Us", "female", "friendly", "Friendly, bright delivery for conversational content.", "from-orange-500 to-rose-600"),
    _voice("eleven_samay", "Samay", "SgjhfihPlST9xrf1Z8gG", "male", "explainer", "Clear social media explainer style, suited to Hindi creator content.", "from-cyan-500 to-blue-700"),
    _voice("eleven_yatin", "Yatin", "7M0JpWdLkoBBL8M1moPi", "male", "playful", "Fun, playful character voice for short videos and skits.", "from-lime-500 to-emerald-700"),
    _voice("eleven_prayan", "Prayan", "qN8pbJT5MZmCpNfGnOjd", "male", "conversational", "Charming creator voice for casual Hindi and Hinglish narration.", "from-violet-500 to-indigo-700"),
    _voice("eleven_krish", "Krish", "xoiRqQNYNTfj1xSWG43x", "male", "character", "Expressive character performance for stories and sketches.", "from-teal-500 to-cyan-700"),
    _voice("eleven_boyd", "Boyd", "gfRt6Z3Z8aTbpLfexQ7N", "male", "natural", "Versatile, natural delivery for conversational narration.", "from-stone-500 to-slate-700"),
    _voice("eleven_roger", "Roger", "CwhRBWXzGAHq8TQ4Fs17", "male", "casual", "Laid-back, resonant style for relaxed narration and podcasts.", "from-blue-500 to-indigo-700"),
]


class ElevenLabsTTSProvider(TTSProvider):
    name: str = "elevenlabs"

    API_BASE = "https://api.elevenlabs.io/v1/text-to-speech"
    DEFAULT_MODEL = "eleven_multilingual_v2"  # supports Hindi
    PCM_RATE = 24000  # pcm_24000 is allowed on all plans

    VOICE_MAPPING = {v["id"]: v["voice_id"] for v in ELEVEN_FEATURED_VOICES}

    def __init__(self, api_key: Optional[str] = None):
        key = api_key or settings.ELEVENLABS_API_KEY or ""
        self.api_key = key.strip().strip('"').strip("'")
        self.model = (getattr(settings, "ELEVENLABS_MODEL", "") or self.DEFAULT_MODEL).strip()

    async def health_check(self) -> bool:
        return bool(self.api_key and len(self.api_key) >= 10)

    def get_supported_voices(self) -> List[Dict[str, Any]]:
        return [
            {k: v[k] for k in ("id", "display_name", "gender", "age_style", "tone",
                               "language", "accent", "description", "sample_text", "avatar_color")}
            for v in ELEVEN_FEATURED_VOICES
        ]

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 1.0,
        stability: float = 0.5,
        audio_format: str = "wav",
    ) -> bytes:
        if not self.api_key:
            raise ValueError("ELEVENLABS_API_KEY is not configured in backend/.env")

        internal = voice_id.lower().strip()
        # internal id -> real ElevenLabs id; otherwise treat as a raw id (case-sensitive!)
        real_voice_id = self.VOICE_MAPPING.get(internal, voice_id.strip())

        want_wav = audio_format.lower() == "wav"
        output_format = f"pcm_{self.PCM_RATE}" if want_wav else "mp3_44100_128"

        payload = {
            "text": text.strip(),
            "model_id": self.model,
            "voice_settings": {
                "stability": max(0.0, min(1.0, stability)),
                "similarity_boost": 0.75,
                # ElevenLabs speed range is 0.7 – 1.2
                "speed": max(0.7, min(1.2, round(speed, 2))),
            },
        }
        headers = {"xi-api-key": self.api_key, "Content-Type": "application/json"}
        url = f"{self.API_BASE}/{real_voice_id}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, params={"output_format": output_format},
                                     json=payload, headers=headers)

        if resp.status_code == 401:
            raise RuntimeError("ElevenLabs API: Invalid API key (or key lacks text_to_speech permission).")
        if resp.status_code == 402:
            raise RuntimeError("ElevenLabs API: Payment required / plan does not allow this voice or format.")
        if resp.status_code == 404:
            raise RuntimeError(f"ElevenLabs API: voice '{real_voice_id}' not found.")
        if resp.status_code == 429:
            raise RuntimeError("ElevenLabs API: Rate limit or credit quota exceeded.")
        if resp.status_code != 200:
            raise RuntimeError(f"ElevenLabs API error ({resp.status_code}): {resp.text[:300]}")

        data = resp.content
        if not data or len(data) < 100:
            raise RuntimeError("ElevenLabs API returned empty audio.")

        return self._pcm_to_wav(data) if want_wav else data

    def _pcm_to_wav(self, pcm: bytes) -> bytes:
        """Wrap raw 16-bit mono PCM into a WAV container (no ffmpeg needed)."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(self.PCM_RATE)
            w.writeframes(pcm)
        return buf.getvalue()
