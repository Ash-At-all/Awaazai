from typing import Dict, Type
from .base import TTSProvider
from .mock_provider import MockTTSProvider
from ..config import settings

class ProviderRegistry:
    _providers: Dict[str, TTSProvider] = {}

    @classmethod
    def get_provider(cls, name: str = None) -> TTSProvider:
        provider_name = (name or settings.DEFAULT_PROVIDER).lower().strip()
        
        if provider_name not in cls._providers:
            if provider_name == "mock":
                cls._providers["mock"] = MockTTSProvider()
            else:
                # Default to mock provider for unknown/unconfigured providers in Phase 1
                print(f"[ProviderRegistry] Provider '{provider_name}' not yet initialized, using mock.")
                cls._providers[provider_name] = MockTTSProvider()

        return cls._providers[provider_name]

    @classmethod
    def register(cls, name: str, provider_instance: TTSProvider):
        cls._providers[name.lower()] = provider_instance

def get_tts_provider(name: str = None) -> TTSProvider:
    return ProviderRegistry.get_provider(name)
