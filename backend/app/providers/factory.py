from typing import Dict, Type
from .base import TTSProvider
from .mock_provider import MockTTSProvider
from .sarvam_provider import SarvamTTSProvider
from .fish_audio_provider import FishAudioTTSProvider
from .elevenlabs_provider import ElevenLabsTTSProvider
from ..config import settings

class ProviderRegistry:
    _providers: Dict[str, TTSProvider] = {}

    @classmethod
    def get_provider(cls, name: str = None) -> TTSProvider:
        provider_name = (name or settings.DEFAULT_PROVIDER).lower().strip()
        
        if provider_name not in cls._providers:
            if provider_name == "sarvam":
                cls._providers["sarvam"] = SarvamTTSProvider()
            elif provider_name in ("fish", "fish_audio"):
                cls._providers[provider_name] = FishAudioTTSProvider()
            elif provider_name == "mock":
                cls._providers["mock"] = MockTTSProvider()
            elif provider_name == "elevenlabs":
                cls._providers["elevenlabs"] = ElevenLabsTTSProvider()
            else:
                # Default to mock provider for unconfigured providers
                print(f"[ProviderRegistry] Provider '{provider_name}' defaulting to mock.")
                cls._providers[provider_name] = MockTTSProvider()

        return cls._providers[provider_name]

    @classmethod
    def register(cls, name: str, provider_instance: TTSProvider):
        cls._providers[name.lower()] = provider_instance

def get_tts_provider(name: str = None) -> TTSProvider:
    return ProviderRegistry.get_provider(name)
