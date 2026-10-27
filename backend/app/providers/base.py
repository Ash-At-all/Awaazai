from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class TTSProvider(ABC):
    """
    Abstract base class for all TTS providers in AwaazAI.
    Plug in Sarvam, Azure Neural, Google Cloud, ElevenLabs, Indic Parler-TTS, or Mock.
    """
    name: str = "base"

    @abstractmethod
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
        Synthesize speech from text. Returns audio raw bytes.
        """
        pass

    @abstractmethod
    def get_supported_voices(self) -> List[Dict[str, Any]]:
        """
        Return the list of voice metadata supported by this provider.
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if provider is available and configured.
        """
        pass
