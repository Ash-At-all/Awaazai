"""
Additive SQLite schema migrations for AwaazAI.
Safely adds new tables and new columns without dropping data or requiring external migration tools.
"""
import sqlite3
from pathlib import Path
from .config import settings
from .database import engine, Base
from .models import User, UserQuota, GlobalSpend, Voice, AudioGeneration

def run_migrations():
    # 1. Ensure all new tables are created
    Base.metadata.create_all(bind=engine)

    # 2. Additive column updates for SQLite if existing database lacks newly added columns
    db_file = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
    if not db_file.exists():
        return

    conn = sqlite3.connect(str(db_file))
    cursor = conn.cursor()

    try:
        # Check voices table columns
        cursor.execute("PRAGMA table_info(voices)")
        voice_cols = [row[1] for row in cursor.fetchall()]
        if "tier" not in voice_cols:
            cursor.execute("ALTER TABLE voices ADD COLUMN tier VARCHAR DEFAULT 'free'")
        if "is_active" not in voice_cols:
            cursor.execute("ALTER TABLE voices ADD COLUMN is_active BOOLEAN DEFAULT 1")

        # Check audio_generations table columns
        cursor.execute("PRAGMA table_info(audio_generations)")
        audio_cols = [row[1] for row in cursor.fetchall()]
        if "user_id" not in audio_cols:
            cursor.execute("ALTER TABLE audio_generations ADD COLUMN user_id VARCHAR")
        if "engine_used" not in audio_cols:
            cursor.execute("ALTER TABLE audio_generations ADD COLUMN engine_used VARCHAR DEFAULT 'free'")
        if "fallback_reason" not in audio_cols:
            cursor.execute("ALTER TABLE audio_generations ADD COLUMN fallback_reason VARCHAR")

        conn.commit()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migrations()
    print("Additive migrations completed successfully.")
