"""
exporter.py
───────────
Service for generating timeline-accurate exports:
- SRT subtitles (standard HH:MM:SS,mmm formatting)
- Structured transcript JSON
- Synchronized individual speaker stems (same duration & timeline origin as master)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import subprocess
import tempfile
import os

from ..config import settings


def format_srt_timestamp(ms: int) -> str:
    """Format millisecond integer into standard SRT timestamp 'HH:MM:SS,mmm'."""
    hours = ms // 3600000
    ms %= 3600000
    minutes = ms // 60000
    ms %= 60000
    seconds = ms // 1000
    millis = ms % 1000
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


class ExporterService:
    @staticmethod
    def generate_srt(segments: List[Dict[str, Any]]) -> str:
        """
        Produce a valid SubRip (.srt) subtitle string from timeline segments.
        Pauses are excluded from displaying as subtitle cues.
        """
        srt_lines = []
        cue_index = 1

        for seg in segments:
            # Skip pause segments in subtitle display
            if seg.get("type") == "pause" or not seg.get("text"):
                continue

            start_str = format_srt_timestamp(int(seg["start_ms"]))
            end_str = format_srt_timestamp(int(seg["end_ms"]))
            artist = seg.get("artist", "Speaker")
            text = seg.get("text", "").strip()

            srt_lines.append(f"{cue_index}")
            srt_lines.append(f"{start_str} --> {end_str}")
            srt_lines.append(f"[{artist}]: {text}")
            srt_lines.append("")
            cue_index += 1

        return "\n".join(srt_lines)

    @staticmethod
    def generate_transcript_json(
        script_id: str,
        segments: List[Dict[str, Any]],
        total_duration_sec: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Produce structured transcript JSON with full timeline metadata."""
        return {
            "version": "1.0",
            "script_id": script_id,
            "total_duration_seconds": total_duration_sec,
            "metadata": metadata or {},
            "segments": segments,
        }

    @staticmethod
    def generate_speaker_stem(
        artist_id: str,
        artist_name: str,
        segments: List[Dict[str, Any]],
        total_duration_ms: int,
        output_format: str = "wav",
    ) -> Path:
        """
        Generate an isolated speaker stem file with the exact same total duration
        and timeline origin as the combined master track. Spoken segments for other
        artists and pauses are rendered as silence.
        """
        base_dir = settings.AUDIO_DIR.resolve()
        stem_filename = f"stem_{artist_id}_{total_duration_ms}.{output_format.lower()}"
        stem_path = base_dir / stem_filename

        if stem_path.exists() and stem_path.stat().st_size > 0:
            return stem_path

        # Build list of chunks (audio for this artist, silence for others)
        chunks: List[Dict[str, Any]] = []
        cursor_ms = 0

        for seg in segments:
            start_ms = int(seg["start_ms"])
            end_ms = int(seg["end_ms"])
            dur_ms = end_ms - start_ms

            if dur_ms <= 0:
                continue

            if seg.get("type") == "dialogue" and seg.get("artist_id") == artist_id and seg.get("chunk_path"):
                chunk_file = Path(seg["chunk_path"])
                if chunk_file.exists():
                    chunks.append({"type": "audio", "path": chunk_file})
                else:
                    chunks.append({"type": "pause", "duration_ms": dur_ms})
            else:
                chunks.append({"type": "pause", "duration_ms": dur_ms})

        if not chunks:
            chunks.append({"type": "pause", "duration_ms": max(100, total_duration_ms)})

        from .stitcher import AudioStitcher
        return AudioStitcher.stitch_sequence(items=chunks, output_format=output_format, cache_id=f"stem_{artist_id}")
