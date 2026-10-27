from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .routers import voices, tts
from .security import RateLimitMiddleware, SecurityHeadersMiddleware

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ElevenLabs-style Text-to-Speech Platform focused exclusively on Indian Voices (Hindi & Hinglish)",
)

# Apply Security Headers
app.add_middleware(SecurityHeadersMiddleware)

# Apply Rate Limiting
app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
)

# Include Routers
app.include_router(voices.router)
app.include_router(tts.router)

@app.get("/")
def read_root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "tagline": "Indian Speech Synthesis - Hindi & Hinglish Focus",
        "docs": "/docs"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "active_provider": settings.DEFAULT_PROVIDER,
        "max_char_limit": settings.MAX_CHAR_LIMIT
    }
