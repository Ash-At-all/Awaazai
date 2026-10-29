import os
import subprocess
import tempfile
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Union
from ..config import settings
from .audio_service import AudioService

class AudioStitcher:
    @staticmethod
    def create_silence_wav(pause_ms: int, target_path: Path, sample_rate: int = 24000) -> None:
        """Create a silent WAV file of duration pause_ms safely using lavfi."""
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
        Backward-compatible helper: stitch an ordered list of audio file paths
        with constant pause_ms silence between each chunk.
        """
        items: List[Dict[str, Any]] = []
        for i, p in enumerate(audio_paths):
            items.append({"type": "audio", "path": p})
            if i < len(audio_paths) - 1 and pause_ms > 0:
                items.append({"type": "pause", "duration_ms": pause_ms})

        return cls.stitch_sequence(items=items, output_format=output_format, cache_id=cache_id)

    @classmethod
    def stitch_sequence(
        cls,
        items: List[Dict[str, Any]],
        output_format: str = "wav",
        cache_id: str = None
    ) -> Path:
        """
        Stitch an ordered sequence of audio chunks and explicit silence pauses.
        
        Parameters
        ----------
        items : List[Dict[str, Any]]
            Ordered elements:
            - {"type": "audio", "path": Path}
            - {"type": "pause", "duration_ms": int}
        output_format : str
            "wav" or "mp3"
        cache_id : str, optional
            Deterministic cache identifier
        """
        if not items:
            raise ValueError("No items provided for stitching sequence.")

        audio_items = [it for it in items if it.get("type") == "audio"]
        if not audio_items:
            raise ValueError("Stitching sequence must contain at least one audio segment.")

        if len(items) > 300:
            raise ValueError("Exceeded maximum items limit for sequence stitching (max 300).")

        base_audio_dir = settings.AUDIO_DIR.resolve()

        # Validate that all input audio paths exist and are safely within designated storage
        for it in audio_items:
            p = it["path"]
            resolved_p = p.resolve()
            if not resolved_p.exists() or not resolved_p.is_file():
                raise FileNotFoundError(f"Audio chunk not found: {p.name}")
            if not (resolved_p.is_relative_to(base_audio_dir) or resolved_p.is_relative_to(settings.SAMPLE_DIR.resolve())):
                raise PermissionError("Access denied: chunk path outside designated audio directories.")

        # Determine target file path based on hash of ordered sequence
        if not cache_id:
            h = hashlib.sha256()
            h.update(output_format.lower().encode())
            for it in items:
                if it["type"] == "audio":
                    h.update(f"audio:{it['path'].name}".encode())
                elif it["type"] == "pause":
                    h.update(f"pause:{int(it.get('duration_ms', 300))}".encode())
            cache_id = f"stitched_{h.hexdigest()}"

        final_filename = f"{cache_id}.{output_format.lower()}"
        final_path = base_audio_dir / final_filename

        # If already exists in cache, return immediately
        if final_path.exists() and final_path.stat().st_size > 0:
            return final_path

        # Generate unique temporary silence files for each distinct pause duration
        temp_files_to_cleanup: List[Path] = []
        silence_cache: Dict[int, Path] = {}

        try:
            # Prepare concat list
            with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as list_file:
                list_path = Path(list_file.name)
                temp_files_to_cleanup.append(list_path)

                for it in items:
                    if it["type"] == "audio":
                        p_str = it["path"].resolve().as_posix().replace("'", "'\\''")
                        list_file.write(f"file '{p_str}'\n")
                    elif it["type"] == "pause":
                        ms = int(it.get("duration_ms", 300))
                        if ms not in silence_cache:
                            s_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                            s_path = Path(s_file.name)
                            s_file.close()
                            cls.create_silence_wav(ms, s_path)
                            temp_files_to_cleanup.append(s_path)
                            silence_cache[ms] = s_path

                        s_str = silence_cache[ms].resolve().as_posix().replace("'", "'\\''")
                        list_file.write(f"file '{s_str}'\n")

            # Run ffmpeg concat with uniform standard encoding (24000Hz mono)
            temp_out = base_audio_dir / f".tmp_{os.getpid()}_{final_filename}"
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
                temp_out.replace(final_path)

            # Embed AI metadata
            AudioService.apply_ai_metadata(final_path, output_format)

            return final_path

        finally:
            # Cleanup temp files safely
            for temp_p in temp_files_to_cleanup:
                if temp_p and temp_p.exists():
                    try:
                        temp_p.unlink()
                    except Exception:
                        pass
