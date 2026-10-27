import sys
import unittest
from fastapi.testclient import TestClient
from app.main import app

class SecurityAndPerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_01_health_endpoint_and_security_headers(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("active_provider", data)
        self.assertEqual(res.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(res.headers.get("x-frame-options"), "DENY")
        self.assertEqual(res.headers.get("referrer-policy"), "strict-origin-when-cross-origin")

    def test_02_list_voices_and_schema(self):
        res = self.client.get("/api/voices")
        self.assertEqual(res.status_code, 200)
        voices = res.json()
        self.assertIsInstance(voices, list)
        self.assertGreater(len(voices), 0)
        first_voice = voices[0]
        self.assertIn("id", first_voice)
        self.assertIn("display_name", first_voice)
        self.assertIn("license_type", first_voice)
        self.assertIn("consent_proof_url", first_voice)

    def test_03_path_traversal_protection(self):
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
            res = self.client.get(f"/api/audio/{bad_name}")
            self.assertIn(res.status_code, (400, 403, 404))

    def test_04_voice_id_format_sanitization(self):
        bad_ids = ["../secret", "voice;id", "id/with/slash"]
        for bad_id in bad_ids:
            res = self.client.get(f"/api/voices/{bad_id}/sample")
            self.assertIn(res.status_code, (400, 404, 422))

    def test_05_tts_schema_and_boundary_validation(self):
        # Empty text
        res = self.client.post("/api/tts", json={"text": "", "voice_id": "neeraj"})
        self.assertEqual(res.status_code, 422)

        # Oversized text (> 2500 chars)
        res = self.client.post("/api/tts", json={"text": "A" * 2600, "voice_id": "neeraj"})
        self.assertEqual(res.status_code, 422)

        # Invalid speed
        res = self.client.post("/api/tts", json={"text": "Test", "voice_id": "neeraj", "speed": 10.0})
        self.assertEqual(res.status_code, 422)

        # Invalid format
        res = self.client.post("/api/tts", json={"text": "Test", "voice_id": "neeraj", "format": "sh"})
        self.assertEqual(res.status_code, 422)

    def test_06_tts_generation_and_deterministic_cache(self):
        req_body = {
            "text": "भारतीय आवाज़ एआई सुरक्षा जांच सफल रही।",
            "voice_id": "neeraj",
            "speed": 1.0,
            "pitch": 1.0,
            "stability": 0.5,
            "format": "wav"
        }
        # First call: synthesize
        res1 = self.client.post("/api/tts", json=req_body)
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        self.assertIn("audio_url", data1)
        self.assertEqual(data1["ai_label"], "AI-Generated Voice (AwaazAI)")
        filename = data1["filename"]

        # Fetch synthesized audio
        audio_res = self.client.get(f"/api/audio/{filename}")
        self.assertEqual(audio_res.status_code, 200)
        self.assertEqual(audio_res.headers.get("x-ai-generated-voice"), "AwaazAI-Verified")
        self.assertGreater(len(audio_res.content), 0)

        # Second call with identical input: should hit cache
        res2 = self.client.post("/api/tts", json=req_body)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        self.assertTrue(data2["cached"])
        self.assertEqual(data2["filename"], filename)

    def test_07_rate_limit_throttling(self):
        throttled = False
        for i in range(40):
            res = self.client.post("/api/tts", json={
                "text": f"Flood probe line {i}",
                "voice_id": "neeraj"
            })
            if res.status_code == 429:
                throttled = True
                data = res.json()
                self.assertIn("Rate limit exceeded", data["detail"])
                self.assertIn("retry_after_seconds", data)
                break
        self.assertTrue(throttled, "Rate limiter did not throttle excessive POST requests.")

if __name__ == "__main__":
    unittest.main()
