import os
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import List
from ..config import settings
from .audio_service import AudioService

class AudioStitcher:
    @staticmethod
    def create_silence_wav(pause_ms: int, target_path: Path, sample_rate: int = 24000) -> None:
        """Create a silent WAV file of duration pause_ms safely."""
        duration_sec = max(0.05, min(10.0, pause_ms / 1000.0))  # Capped between 50ms and 10s
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r={sample_rate}:cl=mono",
            "-t", f"{duration_sec:.3f}",
            "-ac", "1",
            "-ar", str(sample_rate),
            str(target_path.resolve())
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to generate silence audio: {res.stderr}")

    @classmethod
    def stitch_audio_files(
        cls,
        audio_paths: List[Path],
        pause_ms: int = 300,
        output_format: str = "wav",
        cache_id: str = None
    ) -> Path:
        """
        Stitch an ordered list of audio file paths with natural pause_ms silence between each.
        Returns the Path to the generated stitched file.
        """
        if not audio_paths:
            raise ValueError("No audio files provided for stitching")

        if len(audio_paths) > 200:
            raise ValueError("Exceeded maximum line limit for conversation stitching (max 200).")

        base_audio_dir = settings.AUDIO_DIR.resolve()

        # Validate that all input paths exist and are safely within AUDIO_DIR or SAMPLE_DIR
        for p in audio_paths:
            resolved_p = p.resolve()
            if not resolved_p.exists() or not resolved_p.is_file():
                raise FileNotFoundError(f"Audio chunk not found: {p.name}")
            if not (resolved_p.is_relative_to(base_audio_dir) or resolved_p.is_relative_to(settings.SAMPLE_DIR.resolve())):
                raise PermissionError("Access denied: chunk path outside designated audio directories.")

        if len(audio_paths) == 1 and pause_ms == 0:
            return audio_paths[0]

        # Determine target file path based on hash
        if not cache_id:
            h = hashlib.sha256()
            h.update(str(pause_ms).encode())
            h.update(output_format.encode())
            for p in audio_paths:
                h.update(p.name.encode())
            cache_id = f"stitched_{h.hexdigest()}"

        final_filename = f"{cache_id}.{output_format.lower()}"
        final_path = base_audio_dir / final_filename

        # If already exists in cache, return immediately
        if final_path.exists() and final_path.stat().st_size > 0:
            return final_path

        # Generate temporary silence file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as silence_file:
            silence_path = Path(silence_file.name)
        
        try:
            cls.create_silence_wav(pause_ms, silence_path)

            # Build list of files to concatenate
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as list_file:
                list_path = Path(list_file.name)
                for i, audio_p in enumerate(audio_paths):
                    p_str = audio_p.resolve().as_posix().replace("'", "'\\''")
                    list_file.write(f"file '{p_str}'\n")
                    if i < len(audio_paths) - 1 and pause_ms > 0:
                        s_str = silence_path.resolve().as_posix().replace("'", "'\\''")
                        list_file.write(f"file '{s_str}'\n")

            # Run ffmpeg to concatenate with re-encoding to guarantee clean alignment
            temp_out = base_audio_dir / f"tmp_{final_filename}"
            if output_format.lower() == "mp3":
                codec_args = ["-c:a", "libmp3lame", "-b:a", "128k", "-ar", "24000", "-ac", "1"]
            else:
                codec_args = ["-c:a", "pcm_s16le", "-ar", "24000", "-ac", "1"]

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_path.resolve()),
                *codec_args,
                str(temp_out.resolve())
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if res.returncode != 0:
                raise RuntimeError(f"FFmpeg stitching failed: {res.stderr}")

            # Atomically rename
            if temp_out.exists():
                if final_path.exists():
                    final_path.unlink()
                temp_out.rename(final_path)

            # Embed AI metadata
            AudioService.apply_ai_metadata(final_path, output_format)

            return final_path

        finally:
            # Cleanup temp files safely
            for temp_p in (silence_path, list_path if 'list_path' in locals() else None):
                if temp_p and temp_p.exists():
                    try:
                        temp_p.unlink()
                    except Exception:
                        pass
