from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .database import engine, Base
from .routers import voices, tts

# Initialize database schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="ElevenLabs-style Text-to-Speech Platform focused exclusively on Indian Voices (Hindi & Hinglish)",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
