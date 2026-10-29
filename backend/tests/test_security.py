import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "active_provider" in data
    # Verify security headers are injected
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"

def test_list_voices_and_security_headers():
    response = client.get("/api/voices")
    assert response.status_code == 200
    voices = response.json()
    assert isinstance(voices, list)
    assert len(voices) > 0
    # Check voice model schema integrity
    first_voice = voices[0]
    assert "id" in first_voice
    assert "display_name" in first_voice
    assert "license_type" in first_voice
    assert "consent_proof_url" in first_voice

def test_path_traversal_protection_audio():
    # Attempt directory traversal via encoded and raw patterns
    bad_filenames = [
        "../../.env",
        "..%2F..%2F.env",
        "..\\..\\awaazai.db",
        "nested/path/audio.wav",
        "audio.wav;rm -rf",
        "/etc/passwd",
        "C:\\Windows\\win.ini"
    ]
    for bad_name in bad_filenames:
        response = client.get(f"/api/audio/{bad_name}")
        # Must strictly reject with 400 or 404/403, never 200 leak
        assert response.status_code in (400, 403, 404), f"Failed for {bad_name}: got {response.status_code}"

def test_path_traversal_protection_voice_sample():
    bad_ids = ["../secret", "voice;id", "id/with/slash"]
    for bad_id in bad_ids:
        response = client.get(f"/api/voices/{bad_id}/sample")
        assert response.status_code in (400, 404, 422)

def test_tts_input_validation():
    # 1. Empty text
    res = client.post("/api/tts", json={"text": "", "voice_id": "neeraj"})
    assert res.status_code == 422

    # 2. Oversized text (> 2500 chars)
    oversized = "A" * 2600
    res = client.post("/api/tts", json={"text": oversized, "voice_id": "neeraj"})
    assert res.status_code == 422

    # 3. Invalid speed range
    res = client.post("/api/tts", json={"text": "Test", "voice_id": "neeraj", "speed": 5.0})
    assert res.status_code == 422

    # 4. Invalid format
    res = client.post("/api/tts", json={"text": "Test", "voice_id": "neeraj", "format": "exe"})
    assert res.status_code == 422

from unittest.mock import patch, AsyncMock

def test_tts_generation_and_caching():
    req_body = {
        "text": "सुरक्षा और निष्पादन परीक्षण संपन्न हुआ।",
        "voice_id": "neeraj",
        "speed": 1.0,
        "pitch": 1.0,
        "stability": 0.5,
        "format": "wav"
    }
    # First call: synthesis
    res1 = client.post("/api/tts", json=req_body)
    assert res1.status_code == 200
    data1 = res1.json()
    assert "audio_url" in data1
    assert "AI-Generated Voice" in data1["ai_label"]
    assert "AwaazAI" in data1["ai_label"]
    filename = data1["filename"]

    # Verify audio file retrieval
    audio_res = client.get(f"/api/audio/{filename}")
    assert audio_res.status_code == 200
    assert audio_res.headers.get("x-ai-generated-voice") == "AwaazAI-Verified"
    assert len(audio_res.content) > 0

    # Second call with identical parameters: should be instantaneous cache hit
    res2 = client.post("/api/tts", json=req_body)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["cached"] is True
    assert data2["filename"] == filename

@patch("app.services.audio_service.AudioService.generate_speech", new_callable=AsyncMock)
def test_rate_limiter_enforcement(mock_gen):
    mock_gen.return_value = ("rate_mock.wav", "/api/audio/rate_mock.wav", 1.0, True)
    # Trigger repeated requests to test throttle threshold
    exceeded = False
    for i in range(70):
        res = client.post("/api/tts", json={
            "text": f"Flood probe line {i}",
            "voice_id": "neeraj"
        })
        if res.status_code == 429:
            exceeded = True
            data = res.json()
            assert "Rate limit exceeded" in data["detail"]
            assert "retry_after_seconds" in data
            break
    assert exceeded is True, "Rate limiter did not throttle excessive POST requests"
