"""
sarvam_provider.py
──────────────────
Production Indian TTS Provider using Sarvam AI's Bulbul API.
Direct integration supporting Hindi and Hinglish neural synthesis,
pace control, 24kHz studio-quality audio, and graceful fallback.
"""

from __future__ import annotations

import base64
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
import httpx

from ..config import settings
from .base import TTSProvider


class SarvamTTSProvider(TTSProvider):
    name: str = "sarvam"

    API_URL = "https://api.sarvam.ai/text-to-speech"
    DEFAULT_MODEL = "bulbul:v3"

    # Map AwaazAI internal voice IDs to Sarvam Bulbul speaker identities
    VOICE_MAPPING = {
        "neeraj": "shubh",
        "priya": "priya",
        "aarav": "aditya",
        "ananya": "neha",
        "vikram": "ashutosh",
        "kavita": "kavya",
        "ishaan": "rahul",
        "meera": "shreya",
        "shubh": "shubh",
        "aditya": "aditya",
        "rahul": "rahul",
        "ashutosh": "ashutosh",
        "rohan": "rohan",
        "ritu": "ritu",
        "neha": "neha",
        "kavya": "kavya",
        "shreya": "shreya",
        "pooja": "pooja",
        "simran": "simran",
        "default": "shubh",
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.SARVAM_API_KEY

    async def health_check(self) -> bool:
        """Verify API key is configured."""
        return bool(self.api_key and len(self.api_key) >= 10)

    def get_supported_voices(self) -> List[Dict[str, Any]]:
        """Return Sarvam voice catalog compatible with AwaazAI voice roster."""
        return [
            {
                "id": "shubh",
                "display_name": "Shubh (Sarvam)",
                "gender": "male",
                "age_style": "middle aged",
                "tone": "news",
                "language": "Hindi / Hinglish",
                "accent": "Delhi Urban",
                "description": "Clear, authoritative and deep Hindi voice via Sarvam Bulbul.",
                "sample_text": "नमस्कार, आवाज़ एआई में आपका स्वागत है।",
                "license_type": "Commercial API License",
                "consent_proof_url": "https://sarvam.ai",
                "avatar_color": "from-blue-600 to-indigo-800",
            },
            {
                "id": "priya",
                "display_name": "Priya (Sarvam)",
                "gender": "female",
                "age_style": "young adult",
                "tone": "storytelling",
                "language": "Hindi / Hinglish",
                "accent": "Standard Hindi",
                "description": "Warm, natural and expressive female voice via Sarvam Bulbul.",
                "sample_text": "एक समय की बात है, जब वादियों में एक शांत नदी बहती थी।",
                "license_type": "Commercial API License",
                "consent_proof_url": "https://sarvam.ai",
                "avatar_color": "from-rose-500 to-pink-700",
            },
            {
                "id": "aditya",
                "display_name": "Aditya (Sarvam)",
                "gender": "male",
                "age_style": "young adult",
                "tone": "energetic",
                "language": "Hinglish",
                "accent": "Mumbai Tech",
                "description": "Upbeat, contemporary Hinglish voice for conversations and podcasts.",
                "sample_text": "Hey everyone! Welcome back to the channel.",
                "license_type": "Commercial API License",
                "consent_proof_url": "https://sarvam.ai",
                "avatar_color": "from-emerald-500 to-teal-700",
            },
            {
                "id": "neha",
                "display_name": "Neha (Sarvam)",
                "gender": "female",
                "age_style": "young adult",
                "tone": "calm",
                "language": "Hinglish",
                "accent": "Bengaluru Conversational",
                "description": "Friendly, soothing and articulate conversational female voice.",
                "sample_text": "Hello! Main aapki help kaise kar sakti hoon?",
                "license_type": "Commercial API License",
                "consent_proof_url": "https://sarvam.ai",
                "avatar_color": "from-purple-500 to-violet-700",
            },
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
        """
        Synthesize speech using Sarvam AI Bulbul API with pace control.
        """
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY is not configured in backend/.env")

        clean_voice = voice_id.lower().strip()
        speaker = self.VOICE_MAPPING.get(clean_voice, "shubh")

        # Sarvam Bulbul accepts pace between 0.5 and 2.0
        clamped_pace = max(0.5, min(2.0, round(speed, 2)))

        payload = {
            "inputs": [text.strip()],
            "target_language_code": "hi-IN",
            "speaker": speaker,
            "model": self.DEFAULT_MODEL,
            "pace": clamped_pace,
            "speech_sample_rate": 24000,
            "enable_preprocessing": True,
        }

        headers = {
            "api-subscription-key": self.api_key,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.API_URL, json=payload, headers=headers)
            if response.status_code != 200:
                raise RuntimeError(
                    f"Sarvam AI API error ({response.status_code}): {response.text}"
                )

            data = response.json()
            audios = data.get("audios", [])
            if not audios or not audios[0]:
                raise RuntimeError("Sarvam AI returned empty audio response.")

            raw_bytes = base64.b64decode(audios[0])

            if audio_format.lower() == "mp3":
                return self._convert_wav_to_mp3(raw_bytes)

            return raw_bytes

    def _convert_wav_to_mp3(self, wav_data: bytes) -> bytes:
        """Convert WAV bytes to MP3 format using FFmpeg."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as in_f, \
                 tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as out_f:
                in_path = in_f.name
                out_path = out_f.name
                in_f.write(wav_data)

            cmd = ["ffmpeg", "-y", "-i", in_path, "-c:a", "libmp3lame", "-b:a", "128k", out_path]
            res = subprocess.run(cmd, capture_output=True, timeout=10)
            if res.returncode == 0:
                with open(out_path, "rb") as f:
                    mp3_data = f.read()
                try:
                    os.unlink(in_path)
                    os.unlink(out_path)
                except Exception:
                    pass
                return mp3_data
        except Exception:
            pass
        return wav_data
