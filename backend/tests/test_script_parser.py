"""
test_script_parser.py
─────────────────────
Comprehensive tests for script parser, tokenization, offsets,
Devanagari support, pauses, and deterministic mocked TTS endpoint.
"""

from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from app.services.script_parser import (
    DialogueSegment,
    PauseSegment,
    count_spoken_characters,
    parse_script,
    validate_artist_name,
)
from app.main import app

# ── Test Casts ─────────────────────────────────────────────────────
CAST_2 = [
    {"id": "art_101", "name": "Riya",  "voice_id": "priya",  "speed": 0, "stability": 0.5},
    {"id": "art_102", "name": "Arjun", "voice_id": "neeraj", "speed": 0, "stability": 0.5},
]

CAST_DEVANAGARI = [
    {"id": "art_201", "name": "रिया",  "voice_id": "priya",  "speed": 0, "stability": 0.5},
    {"id": "art_202", "name": "अर्जुन", "voice_id": "neeraj", "speed": 0, "stability": 0.5},
]


# ── Name Validation Tests ──────────────────────────────────────────
class TestNameValidation:
    def test_valid_ascii(self):
        assert validate_artist_name("Narrator") is None

    def test_valid_underscore_digits(self):
        assert validate_artist_name("Voice_1") is None

    def test_valid_devanagari(self):
        assert validate_artist_name("दादाजी") is None

    def test_empty_rejected(self):
        assert validate_artist_name("") is not None

    def test_too_long_rejected(self):
        assert validate_artist_name("A" * 21) is not None

    def test_spaces_rejected(self):
        assert validate_artist_name("Riya Sharma") is not None

    def test_special_chars_rejected(self):
        assert validate_artist_name("Riya#1") is not None


# ── Spoken Character Count Tests ───────────────────────────────────
class TestSpokenCharacterCount:
    def test_strips_tags_and_pauses(self):
        text = "@Riya Namaste [pause:500ms] @Arjun Hello [pause:200] Ji"
        count = count_spoken_characters(text)
        # Stripping @Riya and @Arjun leaves " Namaste [pause:500ms]  Hello [pause:200] Ji"
        # Stripping [pause:...] leaves " Namaste   Hello  Ji"
        # Trimming whitespace leaves "Namaste   Hello  Ji" -> 22 chars
        assert count == len(" Namaste   Hello  Ji".strip())

    def test_unicode_combining_characters(self):
        text = "@रिया नमस्ते भारत [pause:300ms]"
        assert count_spoken_characters(text) == len("नमस्ते भारत")


# ── Pause Parsing & Validation Tests ───────────────────────────────
class TestPauseParsing:
    def test_valid_pause_ms(self):
        r = parse_script("@Riya Hello [pause:500ms] World", CAST_2)
        assert not r.errors
        assert len(r.segments) == 3
        assert isinstance(r.segments[0], DialogueSegment)
        assert r.segments[0].text == "Hello"
        assert isinstance(r.segments[1], PauseSegment)
        assert r.segments[1].duration_ms == 500
        assert isinstance(r.segments[2], DialogueSegment)
        assert r.segments[2].text == "World"

    def test_valid_pause_integer_only(self):
        r = parse_script("@Riya Hello [pause:300] World", CAST_2)
        assert not r.errors
        assert r.segments[1].duration_ms == 300

    def test_malformed_pause_syntax(self):
        r = parse_script("@Riya Hello [pause:abc] World", CAST_2)
        assert len(r.errors) > 0
        assert "Invalid pause syntax" in r.errors[0]

    def test_missing_pause_duration(self):
        r = parse_script("@Riya Hello [pause] World", CAST_2)
        assert len(r.errors) > 0
        assert "Invalid pause syntax" in r.errors[0]

    def test_out_of_range_pause(self):
        r = parse_script("@Riya Hello [pause:20ms] World", CAST_2)
        assert len(r.errors) > 0
        assert "out of range" in r.errors[0]


# ── Source Offsets & Stable Identity Tests ─────────────────────────
class TestSourceOffsetsAndIdentity:
    def test_source_offsets_exact(self):
        script = "@Riya Namaste [pause:400ms] @Arjun Alvida"
        r = parse_script(script, CAST_2)
        assert not r.errors
        assert len(r.segments) == 3

        # First segment
        s1 = r.segments[0]
        assert s1.artist_id == "art_101"
        assert script[s1.source_start:s1.source_end].strip() == "Namaste"

        # Pause segment
        s2 = r.segments[1]
        assert script[s2.source_start:s2.source_end] == "[pause:400ms]"

        # Third segment
        s3 = r.segments[2]
        assert s3.artist_id == "art_102"
        assert script[s3.source_start:s3.source_end].strip() == "Alvida"

    def test_artist_id_stable_across_case_insensitive_tags(self):
        script = "@riya Hello @ARJUN World"
        r = parse_script(script, CAST_2)
        assert not r.errors
        assert r.segments[0].artist_id == "art_101"
        assert r.segments[1].artist_id == "art_102"


# ── Edge Cases & Unknown Artists ───────────────────────────────────
class TestParserEdgeCases:
    def test_text_before_first_tag_defaults_to_first_artist(self):
        r = parse_script("Welcome everyone @Arjun Thank you", CAST_2)
        assert not r.errors
        assert r.segments[0].artist_id == "art_101"
        assert r.segments[0].text == "Welcome everyone"

    def test_consecutive_same_artist_merged(self):
        r = parse_script("@Riya Part 1 @Riya Part 2", CAST_2)
        assert not r.errors
        assert len(r.segments) == 1
        assert r.segments[0].text == "Part 1 Part 2"

    def test_unknown_tag_reported_explicitly(self):
        r = parse_script("@Riya Hi @Ghost Bye", CAST_2)
        assert len(r.errors) > 0
        assert "@Ghost" in r.errors[0]

    def test_empty_script_reported(self):
        r = parse_script("", CAST_2)
        assert len(r.errors) > 0

    def test_devanagari_names_and_script(self):
        script = "@रिया नमस्ते जी @अर्जुन सब ठीक है"
        r = parse_script(script, CAST_DEVANAGARI)
        assert not r.errors
        assert r.segments[0].artist_id == "art_201"
        assert r.segments[0].text == "नमस्ते जी"
        assert r.segments[1].artist_id == "art_202"
        assert r.segments[1].text == "सब ठीक है"


# ── Exporter Tests ────────────────────────────────────────────────
class TestExporterService:
    def test_format_srt_timestamp(self):
        from app.services.exporter import format_srt_timestamp
        assert format_srt_timestamp(0) == "00:00:00,000"
        assert format_srt_timestamp(1500) == "00:00:01,500"
        assert format_srt_timestamp(65432) == "00:01:05,432"
        assert format_srt_timestamp(3661005) == "01:01:01,005"

    def test_generate_srt_omits_pauses(self):
        from app.services.exporter import ExporterService
        segments = [
            {"type": "dialogue", "artist": "Riya", "text": "Namaste", "start_ms": 0, "end_ms": 1200},
            {"type": "pause", "duration_ms": 400, "start_ms": 1200, "end_ms": 1600},
            {"type": "dialogue", "artist": "Arjun", "text": "Dhanyawaad", "start_ms": 1600, "end_ms": 2800},
        ]
        srt = ExporterService.generate_srt(segments)
        # Should have 2 cues, not 3
        assert "1\n00:00:00,000 --> 00:00:01,200\n[Riya]: Namaste" in srt
        assert "2\n00:00:01,600 --> 00:00:02,800\n[Arjun]: Dhanyawaad" in srt
        assert "Pause" not in srt


# ── Canonical Cache Key Tests ──────────────────────────────────────
class TestCanonicalCacheKey:
    def test_cache_key_invariance_to_unrelated_context(self):
        from app.services.audio_service import AudioService
        key1 = AudioService.compute_cache_key(
            voice_id="priya",
            text="नमस्ते आप कैसे हैं",
            speed=1.0,
            pitch=1.0,
            stability=0.5,
            audio_format="wav",
            provider="mock"
        )
        # Same text with slight edge whitespace or Unicode composition variations
        import unicodedata
        nfd_text = unicodedata.normalize("NFD", "नमस्ते आप कैसे हैं")
        key2 = AudioService.compute_cache_key(
            voice_id="priya",
            text="  " + nfd_text + "  ",
            speed=1.0,
            pitch=1.0,
            stability=0.5,
            audio_format="wav",
            provider="mock"
        )
        assert key1 == key2

    def test_cache_key_sensitivity_to_synthesis_parameters(self):
        from app.services.audio_service import AudioService
        base_key = AudioService.compute_cache_key("priya", "Hello", 1.0, 1.0, 0.5, "wav", "mock")
        diff_speed = AudioService.compute_cache_key("priya", "Hello", 1.25, 1.0, 0.5, "wav", "mock")
        diff_voice = AudioService.compute_cache_key("neeraj", "Hello", 1.0, 1.0, 0.5, "wav", "mock")
        diff_format = AudioService.compute_cache_key("priya", "Hello", 1.0, 1.0, 0.5, "mp3", "mock")

        assert base_key != diff_speed
        assert base_key != diff_voice
        assert base_key != diff_format


# ── Deterministic Mocked Endpoint Tests ────────────────────────────
class TestScriptEndpointMocked:
    @classmethod
    def setup_class(cls):
        cls.client = TestClient(app)

    @patch("app.routers.script_tts.AudioStitcher.stitch_sequence")
    @patch("app.routers.script_tts.AudioService.get_audio_duration")
    @patch("app.routers.script_tts.AudioService.generate_speech", new_callable=AsyncMock)
    def test_generate_script_endpoint_mocked(self, mock_generate, mock_duration, mock_stitch):
        from pathlib import Path
        mock_generate.return_value = ("mock_01.wav", "/api/audio/mock_01.wav", 1.8, True)
        mock_stitch.return_value = Path("storage/audio/stitched_test.wav")
        mock_duration.return_value = 3.9

        payload = {
            "artists": [
                {"id": "a1", "name": "Riya",  "voice_id": "priya",  "speed": 0, "stability": 0.5},
                {"id": "a2", "name": "Arjun", "voice_id": "neeraj", "speed": 1, "stability": 0.6},
            ],
            "script": "@Riya hello [pause:300ms] @Arjun haanji",
            "audio_format": "wav",
        }
        res = self.client.post("/api/tts/script", json=payload)
        assert res.status_code == 200, res.text
        data = res.json()

        assert "audio_url" in data
        assert "spoken_char_count" in data
        assert "srt_url" in data
        assert "transcript_url" in data
        assert "characters_submitted" in data
        assert "characters_cached" in data
        assert "characters_synthesized" in data
        assert "estimated_cost_inr" in data
        assert "stems" in data
        assert len(data["stems"]) == 2
        assert len(data["segments"]) == 3
        assert data["segments"][0]["type"] == "dialogue"
        assert data["segments"][0]["artist"] == "Riya"
        assert data["segments"][1]["type"] == "pause"
        assert data["segments"][1]["duration_ms"] == 300
        assert data["segments"][2]["type"] == "dialogue"
        assert data["segments"][2]["artist"] == "Arjun"
        assert mock_stitch.called

        # Test export SRT endpoint
        script_id = data["id"]
        srt_res = self.client.get(f"/api/tts/script/{script_id}/export?format=srt")
        assert srt_res.status_code == 200
        assert "[Riya]: hello" in srt_res.text
        assert "[Arjun]: haanji" in srt_res.text
        assert "-->" in srt_res.text

        # Test export JSON endpoint
        json_res = self.client.get(f"/api/tts/script/{script_id}/export?format=json")
        assert json_res.status_code == 200
        json_data = json_res.json()
        assert json_data["script_id"] == script_id
        assert len(json_data["segments"]) >= 3

    def test_malformed_pause_returns_422(self):
        payload = {
            "artists": [
                {"id": "a1", "name": "Riya", "voice_id": "priya", "speed": 0, "stability": 0.5},
            ],
            "script": "@Riya hello [pause:invalid]",
            "audio_format": "wav",
        }
        res = self.client.post("/api/tts/script", json=payload)
        assert res.status_code == 422
        assert "Invalid pause syntax" in res.json()["detail"]
