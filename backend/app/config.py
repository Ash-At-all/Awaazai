import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    APP_NAME: str = os.getenv("APP_NAME", "AwaazAI")
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'awaazai.db'}")
    
    # Storage
    STORAGE_DIR: Path = BASE_DIR / "storage"
    AUDIO_DIR: Path = BASE_DIR / "storage" / "audio"
    SAMPLE_DIR: Path = BASE_DIR / "storage" / "samples"
    
    # Active Provider ("mock", "azure", "sarvam", "google", "elevenlabs", "indic_parler")
    DEFAULT_PROVIDER: str = os.getenv("DEFAULT_PROVIDER", "mock")
    
    # API Keys (loaded from env)
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")
    AZURE_SPEECH_KEY: str = os.getenv("AZURE_SPEECH_KEY", "")
    AZURE_SPEECH_REGION: str = os.getenv("AZURE_SPEECH_REGION", "centralindia")
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    
    # Rate Limiting & Limits
    MAX_CHAR_LIMIT: int = int(os.getenv("MAX_CHAR_LIMIT", "2500"))
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

settings = Settings()
settings.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
