import os
import json
import uuid
import base64
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from pydantic import BaseModel, Field

from ..config import settings
from .auth import require_admin, get_optional_user

router = APIRouter(tags=["Featured Voices"])

DATA_FILE = Path(settings.STORAGE_DIR) / "featured_voices.json"
UPLOADS_DIR = Path(settings.STORAGE_DIR) / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_SEEDED_VOICES = [
    {
        "id": "fish_narration",
        "name": "Narration",
        "voice_id": "0de8162a9e384545a0106046b57488a7",
        "provider": "fish_audio",
        "label": "Deep, Expressive Storytelling",
        "sample_text": "नमस्ते, आवाज़ एआई में आपका स्वागत है। चलिए एक नई और शानदार कहानी की शुरुआत करते हैं।",
        "image_url": "",
        "order": 1,
        "active": True
    },
    {
        "id": "fish_indian_girl",
        "name": "Indian Girl (19)",
        "voice_id": "2b9e2a84cb664489a7ab9ca71af5dff5",
        "provider": "fish_audio",
        "label": "Indian girl, 19 years — Sweet & Conversational",
        "sample_text": "हेलो, आवाज़ एआई पर आपका स्वागत है! क्या आज हम कुछ नया और एक्साइटिंग बनाएं?",
        "image_url": "",
        "order": 2,
        "active": True
    },
    {
        "id": "fish_gojo",
        "name": "Gojo",
        "voice_id": "528f686ef2154885b368dd4b93fb8728",
        "provider": "fish_audio",
        "label": "Gojo-style character — Cool & Heroic",
        "sample_text": "फिक्र मत करो, जब तक मैं यहाँ हूँ, सब एकदम परफेक्ट होगा!",
        "image_url": "",
        "order": 3,
        "active": True
    },
    {
        "id": "fish_funny_man",
        "name": "Funny Man",
        "voice_id": "d219c65920e540509486a30373f5c5c0",
        "provider": "fish_audio",
        "label": "Middle-aged funny man — Humorous & Lively",
        "sample_text": "अरे अरे भाई साहब! मुस्कुराइए, क्योंकि अब आवाज़ एआई का जलवा शुरू होने वाला है!",
        "image_url": "",
        "order": 4,
        "active": True
    }
]

def _read_data() -> List[dict]:
    if not DATA_FILE.exists():
        _write_data(DEFAULT_SEEDED_VOICES)
        return DEFAULT_SEEDED_VOICES
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not data:
                _write_data(DEFAULT_SEEDED_VOICES)
                return DEFAULT_SEEDED_VOICES
            return data
    except Exception:
        return DEFAULT_SEEDED_VOICES

def _write_data(data: List[dict]):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp_file = DATA_FILE.with_suffix(".tmp")
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_file.replace(DATA_FILE)

class FeaturedVoiceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    voice_id: str = Field(..., min_length=1, max_length=100)
    provider: str = Field("fish_audio", max_length=50)
    label: str = Field("", max_length=200)
    sample_text: Optional[str] = Field("नमस्ते, आवाज़ एआई में आपका स्वागत है।", max_length=500)
    image_url: Optional[str] = Field("", max_length=500)
    order: int = Field(1, ge=0)
    active: bool = Field(True)

class FeaturedVoiceUpdate(BaseModel):
    name: Optional[str] = None
    voice_id: Optional[str] = None
    provider: Optional[str] = None
    label: Optional[str] = None
    sample_text: Optional[str] = None
    image_url: Optional[str] = None
    order: Optional[int] = None
    active: Optional[bool] = None

# Public endpoint
@router.get("/api/featured-voices")
def get_public_featured_voices():
    data = _read_data()
    active_voices = [v for v in data if v.get("active", True)]
    active_voices.sort(key=lambda x: x.get("order", 0))
    return active_voices

# Admin endpoints
@router.get("/api/admin/featured-voices")
def get_admin_featured_voices(admin_user=Depends(require_admin)):
    data = _read_data()
    data.sort(key=lambda x: x.get("order", 0))
    return data

@router.post("/api/admin/featured-voices", status_code=status.HTTP_201_CREATED)
def create_featured_voice(req: FeaturedVoiceCreate, admin_user=Depends(require_admin)):
    data = _read_data()
    new_voice = {
        "id": f"fv_{uuid.uuid4().hex[:8]}",
        "name": req.name.strip(),
        "voice_id": req.voice_id.strip(),
        "provider": req.provider.strip() or "fish_audio",
        "label": req.label.strip(),
        "sample_text": (req.sample_text or "नमस्ते, आवाज़ एआई में आपका स्वागत है।").strip(),
        "image_url": (req.image_url or "").strip(),
        "order": req.order,
        "active": req.active
    }
    data.append(new_voice)
    _write_data(data)
    return new_voice

@router.put("/api/admin/featured-voices/{item_id}")
def update_featured_voice(item_id: str, req: FeaturedVoiceUpdate, admin_user=Depends(require_admin)):
    data = _read_data()
    found = False
    for v in data:
        if v["id"] == item_id:
            if req.name is not None: v["name"] = req.name.strip()
            if req.voice_id is not None: v["voice_id"] = req.voice_id.strip()
            if req.provider is not None: v["provider"] = req.provider.strip()
            if req.label is not None: v["label"] = req.label.strip()
            if req.sample_text is not None: v["sample_text"] = req.sample_text.strip()
            if req.image_url is not None: v["image_url"] = req.image_url.strip()
            if req.order is not None: v["order"] = req.order
            if req.active is not None: v["active"] = req.active
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail="Featured voice not found")
    _write_data(data)
    return {"message": "Updated successfully"}

@router.delete("/api/admin/featured-voices/{item_id}")
def delete_featured_voice(item_id: str, admin_user=Depends(require_admin)):
    data = _read_data()
    orig_len = len(data)
    data = [v for v in data if v["id"] != item_id]
    if len(data) == orig_len:
        raise HTTPException(status_code=404, detail="Featured voice not found")
    _write_data(data)
    return {"message": "Deleted successfully"}

@router.post("/api/admin/featured-voices/upload-image")
async def upload_featured_voice_image(file: UploadFile = File(...), admin_user=Depends(require_admin)):
    if not file.content_type in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid image type. Allowed: jpg, png, webp")
    
    contents = await file.read()
    if len(contents) > 2 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image size exceeds 2 MB limit")
    
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "png"
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        ext = "png"
    filename = f"fv_{uuid.uuid4().hex[:12]}.{ext}"
    dest_path = UPLOADS_DIR / filename
    with open(dest_path, "wb") as f:
        f.write(contents)
    
    return {"image_url": f"/api/uploads/{filename}"}
