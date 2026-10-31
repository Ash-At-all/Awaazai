"""Run from backend/:  python list_eleven_voices.py
Prints voice names + IDs available to YOUR ElevenLabs key."""
import os, httpx
from dotenv import load_dotenv
load_dotenv()
key = os.getenv("ELEVENLABS_API_KEY", "").strip().strip('"')
r = httpx.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": key}, timeout=30)
print("status:", r.status_code)
if r.status_code == 200:
    for v in r.json().get("voices", []):
        print(f"{v['voice_id']}  {v['name']}  ({v.get('category')})")
else:
    print(r.text[:300])
