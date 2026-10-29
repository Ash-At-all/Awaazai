from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
from .config import settings
from .database import engine, Base
from .migrations import run_migrations
from .routers import voices, tts, script_tts, auth, featured_voices
from .security import RateLimitMiddleware, SecurityHeadersMiddleware

# Initialize and migrate database schema safely
run_migrations()

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
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
)

# Static Uploads directory
uploads_dir = Path(settings.STORAGE_DIR) / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/api/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Include Routers
app.include_router(auth.router)
app.include_router(voices.router)
app.include_router(tts.router)
app.include_router(script_tts.router)
app.include_router(featured_voices.router)

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
