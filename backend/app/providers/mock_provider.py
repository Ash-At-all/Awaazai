import asyncio
import io
import os
import math
import struct
import wave
import tempfile
import subprocess
from pathlib import Path
from typing import List, Dict, Any

from .base import TTSProvider

class MockTTSProvider(TTSProvider):
    """
    Mock & Offline-first Indian TTS Provider.
    Uses high-quality Neural voices (hi-IN, en-IN) via edge-tts when available,
    and seamlessly falls back to a procedural acoustic formant synthesizer
    if offline, requiring NO external paid API keys.
    """
    name = "mock"

    VOICE_MAPPING = {
        # Male voices
        "neeraj": "hi-IN-MadhurNeural",
        "aarav": "en-IN-PrabhatNeural",
        "vikram": "hi-IN-MadhurNeural",
        "ishaan": "en-IN-PrabhatNeural",
        "rohan": "en-IN-PrabhatNeural",
        # Female voices
        "priya": "hi-IN-SwaraNeural",
        "ananya": "en-IN-NeerjaExpressiveNeural",
        "kavita": "hi-IN-SwaraNeural",
        "meera": "en-IN-NeerjaNeural",
        "default": "hi-IN-MadhurNeural"
    }

    VOICE_PITCH_OFFSETS = {
        "male": 130.0,
        "female": 240.0
    }

    def __init__(self):
        pass

    async def health_check(self) -> bool:
        return True

    def get_supported_voices(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "neeraj",
                "display_name": "Neeraj Sharma",
                "gender": "male",
                "age_style": "middle aged",
                "tone": "news",
                "language": "Hindi",
                "accent": "Delhi Urban",
                "description": "Authoritative, crisp, and deep voice ideal for news, documentaries, and explainers.",
                "sample_text": "नमस्कार, आवाज़ एआई में आपका स्वागत है। आज का मुख्य समाचार सुनिए।",
                "license_type": "Exclusive License",
                "consent_proof_url": "https://awaazai.internal/consents/neeraj-signed-v1.pdf",
                "avatar_color": "from-blue-600 to-indigo-800"
            },
            {
                "id": "priya",
                "display_name": "Priya Sen",
                "gender": "female",
                "age_style": "young adult",
                "tone": "storytelling",
                "language": "Hindi",
                "accent": "Varanasi Pure",
                "description": "Warm, emotional, and expressive voice designed for audiobooks, narratives, and poetry.",
                "sample_text": "एक समय की बात है, जब हिमालय की वादियों में एक शांत नदी बहती थी।",
                "license_type": "Voice Actor Agreement",
                "consent_proof_url": "https://awaazai.internal/consents/priya-agreement-2026.pdf",
                "avatar_color": "from-rose-500 to-pink-700"
            },
            {
                "id": "aarav",
                "display_name": "Aarav Mehta",
                "gender": "male",
                "age_style": "young adult",
                "tone": "energetic",
                "language": "Hinglish",
                "accent": "Mumbai Tech",
                "description": "Energetic, modern Hinglish voice perfect for podcasts, tech reviews, and startup videos.",
                "sample_text": "Hey everyone! Welcome back to the channel. Aaj hum review karenge best AI audio tech.",
                "license_type": "Standard Commercial",
                "consent_proof_url": "https://awaazai.internal/consents/aarav-commercial-2026.pdf",
                "avatar_color": "from-emerald-500 to-teal-700"
            },
            {
                "id": "ananya",
                "display_name": "Ananya Roy",
                "gender": "female",
                "age_style": "young adult",
                "tone": "calm",
                "language": "Hinglish",
                "accent": "Bengaluru Conversational",
                "description": "Soothing, friendly, and articulate tone suited for customer support, meditation, and chats.",
                "sample_text": "Hello! Main aapki help kaise kar sakti hoon? Let me know whenever you're ready.",
                "license_type": "Synthetic Royalty-Free",
                "consent_proof_url": "https://awaazai.internal/consents/ananya-royaltyfree.pdf",
                "avatar_color": "from-purple-500 to-violet-700"
            },
            {
                "id": "vikram",
                "display_name": "Vikram Rathore",
                "gender": "male",
                "age_style": "senior",
                "tone": "storytelling",
                "language": "Hindi",
                "accent": "Rajasthan Deep",
                "description": "Resonant, baritone elder voice for historical tales, mythologies, and cinematic narration.",
                "sample_text": "सदियों पहले इस धरती पर वीरों की गाथाएं गूंजती थीं।",
                "license_type": "Exclusive License",
                "consent_proof_url": "https://awaazai.internal/consents/vikram-rathore-signed.pdf",
                "avatar_color": "from-amber-600 to-yellow-800"
            },
            {
                "id": "kavita",
                "display_name": "Kavita Rao",
                "gender": "female",
                "age_style": "middle aged",
                "tone": "news",
                "language": "Hindi",
                "accent": "Lucknow Refined",
                "description": "Refined and clear diction suitable for formal presentations, edtech, and announcements.",
                "sample_text": "भारतीय विज्ञान संस्थान द्वारा आयोजित इस विशेष सत्र में आप सभी का स्वागत है।",
                "license_type": "Voice Actor Agreement",
                "consent_proof_url": "https://awaazai.internal/consents/kavita-rao-contract.pdf",
                "avatar_color": "from-cyan-600 to-blue-700"
            },
            {
                "id": "ishaan",
                "display_name": "Ishaan Verma",
                "gender": "male",
                "age_style": "young adult",
                "tone": "conversational",
                "language": "Hinglish",
                "accent": "Delhi Youth",
                "description": "Casual, buddy-like Hinglish tone great for casual dialogue, gaming, and lifestyle content.",
                "sample_text": "Arre yaar, weekend pe chalte hain movie dekhne. What do you think?",
                "license_type": "Standard Commercial",
                "consent_proof_url": "https://awaazai.internal/consents/ishaan-commercial.pdf",
                "avatar_color": "from-orange-500 to-red-600"
            },
            {
                "id": "meera",
                "display_name": "Meera Joshi",
                "gender": "female",
                "age_style": "young adult",
                "tone": "energetic",
                "language": "Hinglish",
                "accent": "Pune Urban",
                "description": "Upbeat, lively and engaging voice for social media reels, ads, and entertainment.",
                "sample_text": "Check out this super cool new feature! You won't believe how easy it is.",
                "license_type": "Synthetic Royalty-Free",
                "consent_proof_url": "https://awaazai.internal/consents/meera-royaltyfree.pdf",
                "avatar_color": "from-fuchsia-500 to-pink-600"
            }
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
        voice_key = voice_id.lower().strip()
        neural_voice = self.VOICE_MAPPING.get(
            voice_key,
            voice_id.strip() if voice_id.startswith(("hi-IN-", "en-IN-")) else "hi-IN-MadhurNeural",
        )

        # Format rate and pitch adjustments for edge-tts
        # rate: e.g. "+10%", "-20%"
        rate_pct = int((speed - 1.0) * 100)
        rate_str = f"{rate_pct:+d}%"

        # pitch: e.g. "+5Hz", "-10Hz"
        pitch_pct = int((pitch - 1.0) * 50)
        pitch_str = f"{pitch_pct:+d}Hz"

        try:
            import edge_tts
            communicate = edge_tts.Communicate(
                text=text,
                voice=neural_voice,
                rate=rate_str,
                pitch=pitch_str
            )

            mp3_bytes = bytearray()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    mp3_bytes.extend(chunk["data"])

            if len(mp3_bytes) > 0:
                raw_audio = bytes(mp3_bytes)
                if audio_format.lower() == "wav":
                    return self._convert_mp3_to_wav(raw_audio)
                return raw_audio

        except Exception as e:
            # Fallback to procedural formant synthesis if network/edge-tts is unavailable
            print(f"[MockTTSProvider] Falling back to procedural audio: {e}")

        is_female = voice_key in ["priya", "ananya", "kavita", "meera"]
        base_f0 = 230.0 if is_female else 135.0
        return self._generate_procedural_wav(text, base_pitch=base_f0 * pitch, speed=speed)

    def _convert_mp3_to_wav(self, mp3_data: bytes) -> bytes:
        """Convert MP3 bytes to standard WAV format using temp files and ffmpeg."""
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as in_file, \
                 tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_file:
                in_path = in_file.name
                out_path = out_file.name
                in_file.write(mp3_data)

            cmd = ["ffmpeg", "-y", "-i", in_path, "-ac", "1", "-ar", "24000", out_path]
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
        except Exception as err:
            print(f"FFmpeg conversion error: {err}")
        return mp3_data

    def _generate_procedural_wav(self, text: str, base_pitch: float = 150.0, speed: float = 1.0) -> bytes:
        """
        Generates pleasant procedural speech-like audio with natural vowel formant harmonics
        and rhythmic cadence tailored to the input text and words.
        """
        sample_rate = 22050
        words = text.strip().split()
        if not words:
            words = ["a"]

        # Word duration scales with speed
        base_word_dur = 0.28 / max(0.4, speed)
        pause_dur = 0.08 / max(0.4, speed)

        total_audio_samples = []

        # Formant frequencies for vowels (simulating vocal tract resonance)
        formants = [
            (base_pitch, 0.45),
            (base_pitch * 2.1, 0.25),
            (base_pitch * 3.4, 0.15),
            (base_pitch * 5.2, 0.08),
        ]

        for i, word in enumerate(words):
            word_len = len(word)
            dur = base_word_dur * (0.8 + min(0.6, word_len * 0.05))
            num_samples = int(sample_rate * dur)

            # Slight pitch inflection on word
            inflection = 1.0 + 0.05 * math.sin(i * 1.2)

            for s in range(num_samples):
                t = s / sample_rate
                # Attack-decay envelope for each syllable/word
                env = math.sin(math.pi * (s / num_samples)) ** 0.8

                sample_val = 0.0
                for f_mult, amp in formants:
                    freq = base_pitch * inflection * (f_mult / base_pitch)
                    # Add subtle vibrato
                    freq += 1.5 * math.sin(2 * math.pi * 5.0 * t)
                    sample_val += amp * math.sin(2 * math.pi * freq * t)

                # Clamp & scale to 16-bit PCM
                sample_int = int(max(-1.0, min(1.0, sample_val * env)) * 24000)
                total_audio_samples.append(sample_int)

            # Insert pause between words
            pause_samples = int(sample_rate * pause_dur)
            total_audio_samples.extend([0] * pause_samples)

        # Build WAV file
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            raw_frames = struct.pack(f"<{len(total_audio_samples)}h", *total_audio_samples)
            wav_file.writeframes(raw_frames)

        return buffer.getvalue()
