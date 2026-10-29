"""
fish_audio_provider.py
──────────────────────
Fish Audio S2.1 Pro TTS Provider for AwaazAI.
Uses the Fish Audio REST API with reference_id-based voice selection.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
import httpx

from ..config import settings
from .base import TTSProvider


# ── Featured voice config (single source of truth) ──────────────────
FISH_FEATURED_VOICES = [
    {
        "id": "fish_narration",
        "display_name": "Narration (Fish Audio)",
        "reference_id": "0de8162a9e384545a0106046b57488a7",
        "gender": "male",
        "age_style": "middle aged",
        "tone": "narration",
        "language": "Hindi / Hinglish",
        "accent": "Calm & Professional",
        "description": "Narration voice — expressive, deep and clear, ideal for audiobooks and documentaries.",
        "sample_text": "नमस्ते, आवाज़ एआई में आपका स्वागत है। चलिए एक नई और शानदार कहानी की शुरुआत करते हैं।",
        "license_type": "Fish Audio Platform",
        "consent_proof_url": "https://fish.audio",
        "avatar_color": "from-sky-500 to-blue-700",
        "label": "Narration",
    },
    {
        "id": "fish_indian_girl",
        "display_name": "Indian Girl (Fish Audio)",
        "reference_id": "2b9e2a84cb664489a7ab9ca71af5dff5",
        "gender": "female",
        "age_style": "young adult",
        "tone": "conversational",
        "language": "Hindi / Hinglish",
        "accent": "Sweet & Natural",
        "description": "Indian girl, 19 years — natural, youthful conversational voice for modern reels and chats.",
        "sample_text": "हेलो, आवाज़ एआई पर आपका स्वागत है! क्या आज हम कुछ नया और एक्साइटिंग बनाएं?",
        "license_type": "Fish Audio Platform",
        "consent_proof_url": "https://fish.audio",
        "avatar_color": "from-pink-500 to-rose-600",
        "label": "Indian girl, 19 years",
    },
    {
        "id": "fish_gojo",
        "display_name": "Gojo-style (Fish Audio)",
        "reference_id": "528f686ef2154885b368dd4b93fb8728",
        "gender": "male",
        "age_style": "young adult",
        "tone": "energetic",
        "language": "Hindi / Hinglish",
        "accent": "Cool & Heroic",
        "description": "Gojo-style community character voice. Energetic and stylish for anime content.",
        "sample_text": "फिक्र मत करो, जब तक मैं यहाँ हूँ, सब एकदम परफेक्ट होगा!",
        "license_type": "Community Voice — verify rights",
        "consent_proof_url": "https://fish.audio",
        "avatar_color": "from-indigo-500 to-violet-700",
        "label": "Gojo-style character",
    },
    {
        "id": "fish_funny_man",
        "display_name": "Funny Man (Fish Audio)",
        "reference_id": "d219c65920e540509486a30373f5c5c0",
        "gender": "male",
        "age_style": "middle aged",
        "tone": "comedy",
        "language": "Hindi / Hinglish",
        "accent": "Humorous & Lively",
        "description": "Middle-aged funny man — comedic, dramatic and entertaining character voice.",
        "sample_text": "अरे अरे भाई साहब! मुस्कुराइए, क्योंकि अब आवाज़ एआई का जलवा शुरू होने वाला है!",
        "license_type": "Fish Audio Platform",
        "consent_proof_url": "https://fish.audio",
        "avatar_color": "from-amber-500 to-orange-600",
        "label": "Middle-aged funny man",
    },
]


class FishAudioTTSProvider(TTSProvider):
    name: str = "fish"

    API_URL = "https://api.fish.audio/v1/tts"
    DEFAULT_MODEL = "s2.1-pro-free"

    # Map AwaazAI internal voice IDs → Fish Audio reference_id
    VOICE_MAPPING = {v["id"]: v["reference_id"] for v in FISH_FEATURED_VOICES}

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.FISH_AUDIO_API_KEY

    async def health_check(self) -> bool:
        """Verify API key is configured."""
        return bool(self.api_key and len(self.api_key) >= 10)

    def get_supported_voices(self) -> List[Dict[str, Any]]:
        """Return Fish Audio featured voice catalog."""
        return [
            {
                "id": v["id"],
                "display_name": v["display_name"],
                "gender": v["gender"],
                "age_style": v["age_style"],
                "tone": v["tone"],
                "language": v["language"],
                "accent": v["accent"],
                "description": v["description"],
                "sample_text": v["sample_text"],
                "license_type": v["license_type"],
                "consent_proof_url": v["consent_proof_url"],
                "avatar_color": v["avatar_color"],
            }
            for v in FISH_FEATURED_VOICES
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
        Synthesize speech using Fish Audio v1 TTS API.
        Returns raw audio bytes (wav or mp3).
        """
        if not self.api_key:
            raise ValueError("FISH_AUDIO_API_KEY is not configured in backend/.env")

        clean_voice = voice_id.lower().strip()
        reference_id = self.VOICE_MAPPING.get(clean_voice, clean_voice)

        # Fish Audio supports mp3, wav, opus, pcm
        out_format = audio_format.lower() if audio_format.lower() in ("mp3", "wav", "opus", "pcm") else "mp3"

        payload = {
            "text": text.strip(),
            "reference_id": reference_id,
            "format": out_format,
        }

        # Only add speed if not default (Fish Audio accepts 0.5–2.0)
        if speed != 1.0:
            payload["speed"] = max(0.5, min(2.0, round(speed, 2)))

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "model": self.DEFAULT_MODEL,
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(self.API_URL, json=payload, headers=headers)

            if response.status_code == 401:
                raise RuntimeError("Fish Audio API: Invalid or expired API key.")
            elif response.status_code == 429:
                raise RuntimeError("Fish Audio API: Rate limit exceeded. Please wait and try again.")
            elif response.status_code != 200:
                raise RuntimeError(
                    f"Fish Audio API error ({response.status_code}): {response.text[:200]}"
                )

            raw_bytes = response.content

            if not raw_bytes or len(raw_bytes) < 100:
                raise RuntimeError("Fish Audio API returned empty or invalid audio response.")

            # If user requested wav but API returned mp3, convert
            if audio_format.lower() == "wav" and out_format == "mp3":
                return self._convert_mp3_to_wav(raw_bytes)

            return raw_bytes

    def _convert_mp3_to_wav(self, mp3_data: bytes) -> bytes:
        """Convert MP3 bytes to WAV format using FFmpeg."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as in_f, \
                 tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_f:
                in_path = in_f.name
                out_path = out_f.name
                in_f.write(mp3_data)

            cmd = ["ffmpeg", "-y", "-i", in_path, "-ar", "24000", "-ac", "1", out_path]
            res = subprocess.run(cmd, capture_output=True, timeout=10)
            if res.returncode == 0:
                with open(out_path, "rb") as f:
                    wav_data = f.read()
                try:
                    os.unlink(in_path)
                    os.unlink(out_path)
                except Exception:
                    pass
                return wav_data
        except Exception:
            pass
        return mp3_data
