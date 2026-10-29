"""Smoke test for auth endpoints, voice tiers, and quota."""
import sys
sys.path.insert(0, ".")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def main():
    import time
    test_email = f"smoke_{int(time.time())}@example.com"

    # 1. Health check
    r = client.get("/api/health")
    print("=== HEALTH ===")
    print(r.status_code, r.json())
    assert r.status_code == 200

    # 2. /me unauthenticated
    print("\n=== ME (unauthenticated) ===")
    r = client.get("/api/auth/me")
    print(r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["authenticated"] is False

    # 3. Signup
    print("\n=== SIGNUP ===")
    r = client.post("/api/auth/signup", json={"email": test_email, "password": "SmokeTest123!"})
    print(r.status_code, r.json())
    assert r.status_code == 201
    token = r.json()["verification_token"]

    # 4. Verify email (starts trial)
    print("\n=== VERIFY EMAIL ===")
    r = client.post("/api/auth/verify-email", json={"token": token})
    print(r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["user"]["is_verified"] is True
    assert r.json()["quota"]["is_trial_active"] is True
    assert r.json()["quota"]["days_left"] > 0

    # 5. /me authenticated via cookie
    print("\n=== ME (authenticated via cookie) ===")
    r = client.get("/api/auth/me")
    print(r.status_code, r.json())
    assert r.status_code == 200
    assert r.json()["authenticated"] is True

    # 6. Logout
    print("\n=== LOGOUT ===")
    r = client.post("/api/auth/logout")
    print(r.status_code, r.json())
    assert r.status_code == 200

    # 7. /me after logout
    print("\n=== ME (after logout) ===")
    r = client.get("/api/auth/me")
    assert r.json()["authenticated"] is False

    # 8. Login
    print("\n=== LOGIN ===")
    r = client.post("/api/auth/login", json={"email": test_email, "password": "SmokeTest123!"})
    print(r.status_code, r.json())
    assert r.status_code == 200

    # 9. Duplicate signup blocked
    print("\n=== DUPLICATE SIGNUP ===")
    r = client.post("/api/auth/signup", json={"email": test_email, "password": "AnotherPass1!"})
    print(r.status_code, r.json())
    assert r.status_code == 400

    # 10. Premium voices = exactly 10
    print("\n=== PREMIUM VOICES ===")
    r = client.get("/api/voices?tier=premium")
    premium = r.json()
    print(r.status_code, "count:", len(premium), "ids:", [v["id"] for v in premium])
    assert len(premium) == 10
    for v in premium:
        assert v["tier"] == "premium"

    # 11. Free voices still present
    print("\n=== FREE VOICES ===")
    r = client.get("/api/voices?tier=free")
    free = r.json()
    print(r.status_code, "count:", len(free), "ids:", [v["id"] for v in free])
    assert len(free) >= 4
    for v in free:
        assert v["tier"] == "free"

    # 12. Wrong password lockout
    print("\n=== WRONG PASSWORD ===")
    for i in range(6):
        r = client.post("/api/auth/login", json={"email": test_email, "password": "WrongPass!"})
        print(f"  attempt {i+1}: {r.status_code}")
    assert r.status_code == 429  # locked out

    # 13. Test Server-side Fallback & Allowlist Enforcement
    print("\n=== TTS ALLOWLIST & ROUTING ===")
    
    # 13a. Non-allowlisted premium voice strictly rejected
    r_bad_voice = client.post("/api/tts", json={
        "text": "अवैध आवाज़ परीक्षण",
        "voice_id": "sarvam_unknown_hacker_voice"
    })
    print("Rejected bad premium voice:", r_bad_voice.status_code, r_bad_voice.json())
    assert r_bad_voice.status_code == 400
    assert "curated premium voice allowlist" in r_bad_voice.json()["detail"]

    # 13b. Unauthenticated request to premium voice automatically falls back to free
    # Create unauthenticated client
    unauth_client = TestClient(app)
    from unittest.mock import patch, AsyncMock
    with patch("app.services.audio_service.AudioService.generate_speech", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = ("fallback_audio.wav", "/api/audio/fallback_audio.wav", 1.5, False)
        r_unauth_fallback = unauth_client.post("/api/tts", json={
            "text": "नमस्ते दोस्तों",
            "voice_id": "sarvam_shubh"
        })
        print("Unauthenticated fallback:", r_unauth_fallback.status_code, r_unauth_fallback.json().get("engine_used"), r_unauth_fallback.json().get("fallback_reason"))
        assert r_unauth_fallback.status_code == 200
        assert r_unauth_fallback.json()["engine_used"] == "free"
        assert r_unauth_fallback.json()["fallback_reason"] == "unauthenticated"

    # 13c. Script estimation endpoint pre-check
    r_est = unauth_client.post("/api/tts/script/estimate", json={
        "artists": [
            {"id": "a1", "name": "Shubh", "voice_id": "sarvam_shubh", "speed": 0, "stability": 0.5}
        ],
        "script": "@Shubh नमस्कार दोस्तों [pause:200ms] स्वागत है",
        "audio_format": "wav"
    })
    print("Script estimation:", r_est.status_code, r_est.json())
    assert r_est.status_code == 200
    est_data = r_est.json()
    assert est_data["premium_chars"] > 0
    assert est_data["suggest_free_fallback"] is True  # unauth -> fallback suggested

    print("\n=== ALL SMOKE TESTS PASSED ===")

if __name__ == "__main__":
    main()
