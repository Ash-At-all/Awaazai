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
    FISH_AUDIO_API_KEY: str = os.getenv("FISH_AUDIO_API_KEY", "")
    FISH_AUDIO_MODEL: str = os.getenv("FISH_AUDIO_MODEL", "s2-pro")
    
    # Rate Limiting & Limits
    MAX_CHAR_LIMIT: int = int(os.getenv("MAX_CHAR_LIMIT", "2500"))
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    
    # 30-Day Premium Trial & Quota Settings
    TRIAL_DAYS: int = int(os.getenv("TRIAL_DAYS", "30"))
    TRIAL_TOTAL_PREMIUM_CHARS: int = int(os.getenv("TRIAL_TOTAL_PREMIUM_CHARS", "10000"))
    TRIAL_DAILY_PREMIUM_CHARS: int = int(os.getenv("TRIAL_DAILY_PREMIUM_CHARS", "1000"))
    MAX_CHARS_PER_REQUEST_PREMIUM: int = int(os.getenv("MAX_CHARS_PER_REQUEST_PREMIUM", "500"))
    MAX_CHARS_PER_REQUEST_FREE: int = int(os.getenv("MAX_CHARS_PER_REQUEST_FREE", "2500"))
    FREE_FALLBACK_DAILY_CHARS: int = int(os.getenv("FREE_FALLBACK_DAILY_CHARS", "3000"))
    
    # Global Spend Guard & Kill Switch
    GLOBAL_DAILY_PREMIUM_SPEND_CAP_INR: float = float(os.getenv("GLOBAL_DAILY_PREMIUM_SPEND_CAP_INR", "500.0"))
    PREMIUM_KILL_SWITCH: bool = os.getenv("PREMIUM_KILL_SWITCH", "False").lower() in ("true", "1")
    
    # Auth & Sessions
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "awaazai-production-grade-jwt-secret-key-replace-in-env")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ]

settings = Settings()
settings.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
settings.SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
