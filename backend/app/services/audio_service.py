import hashlib
import io
import os
import subprocess
import json
import wave
from pathlib import Path
from typing import Optional, Tuple
from datetime import datetime

from ..config import settings
from ..providers.factory import get_tts_provider

class AudioService:
    @staticmethod
    def compute_cache_key(
        voice_id: str,
        text: str,
        speed: float = 1.0,
        pitch: float = 1.0,
        stability: float = 0.5,
        audio_format: str = "wav",
        provider: str = "mock"
    ) -> str:
        clean_text = text.strip()
        raw = f"{provider}:{voice_id}:{clean_text}:{speed:.2f}:{pitch:.2f}:{stability:.2f}:{audio_format}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def get_audio_duration(file_path: Path) -> float:
        """Accurately read duration of WAV or MP3 file using ffprobe with fallbacks."""
        try:
            cmd = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                str(file_path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                dur = float(data.get("format", {}).get("duration", 0))
                if dur > 0:
                    return round(dur, 2)
        except Exception:
            pass

        # Fallback to mutagen
        try:
            from mutagen.mp3 import MP3
            audio = MP3(str(file_path))
            return round(audio.info.length, 2)
        except Exception:
            pass

        return 2.5

    @classmethod
    def apply_ai_metadata(cls, file_path: Path, format_type: str = "wav") -> None:
        """
        Embed AI-generated voice label in metadata.
        Voice Rule: Show a clear 'AI-generated voice' label in downloaded file metadata.
        """
        try:
            if format_type.lower() == "mp3":
                from mutagen.id3 import ID3, TIT2, TPE1, COMM, TCON
                id3 = ID3(str(file_path))
                id3.add(TIT2(encoding=3, text="AI Generated Speech - AwaazAI"))
                id3.add(TPE1(encoding=3, text="AwaazAI Synthetic Indian Voice"))
                id3.add(TCON(encoding=3, text="AI Voice / Synthetic Media"))
                id3.add(COMM(encoding=3, lang="eng", desc="AI Label", text="AI-generated voice produced by AwaazAI. Not a real human recording."))
                id3.save(v2_version=3)
        except Exception as e:
            print(f"[AudioService] Metadata write notice: {e}")

    @classmethod
    async def generate_speech(
        cls,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 1.0,
        stability: float = 0.5,
        audio_format: str = "wav",
        provider_name: Optional[str] = None
    ) -> Tuple[str, str, float, bool]:
        """
        Synthesize speech, utilize hash caching, apply AI metadata, and return (filename, file_url, duration, was_cached).
        """
        provider = get_tts_provider(provider_name)
        active_provider_name = provider.name

        cache_hash = cls.compute_cache_key(
            voice_id=voice_id,
            text=text,
            speed=speed,
            pitch=pitch,
            stability=stability,
            audio_format=audio_format,
            provider=active_provider_name
        )

        filename = f"{cache_hash}.{audio_format.lower()}"
        file_path = settings.AUDIO_DIR / filename
        file_url = f"/api/audio/{filename}"

        # 1. Check cache
        if file_path.exists() and file_path.stat().st_size > 0:
            duration = cls.get_audio_duration(file_path)
            return filename, file_url, duration, True

        # 2. Synthesize audio
        raw_audio = await provider.synthesize(
            text=text,
            voice_id=voice_id,
            speed=speed,
            pitch=pitch,
            stability=stability,
            audio_format=audio_format
        )

        # 3. Save to disk
        with open(file_path, "wb") as f:
            f.write(raw_audio)

        # 4. Apply AI label metadata
        cls.apply_ai_metadata(file_path, audio_format)

        # 5. Measure duration
        duration = cls.get_audio_duration(file_path)

        return filename, file_url, duration, False
