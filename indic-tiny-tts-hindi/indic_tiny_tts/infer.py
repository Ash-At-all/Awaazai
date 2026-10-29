"""Inference runtime for released indic-tiny-tts models (one language per model; text -> 24 kHz audio).

    from indic_tiny_tts.infer import TinyTTS                     # in the released package: from indic_tiny_tts import TinyTTS
    tts = TinyTTS.from_pretrained("sulabhkatiyar/indic-tiny-tts-hindi")    # HF repo id or a local folder
    wav = tts.synthesize("नमस्ते, आप कैसे हैं?", voice="female")            # float32 numpy array, tts.sample_rate Hz
    tts.save_wav(wav, "hello.wav")

Release folder (written by `python -m tts.release.build_hf`):
  config.json          language, voices, model/vocoder config, vocabulary, mel stats, synthesis defaults, provenance
  model.safetensors    acoustic model (Matcha-style, EMA weights)
  vocoder.safetensors  Vocos mel vocoder (charactr/vocos-mel-24khz, MIT)

Dependencies: torch, numpy, safetensors (+ huggingface_hub to download by repo id). Character input through the
stdlib-only `textnorm`; no eSpeak or any other GPL component is imported (a test enforces this).
"""
from __future__ import annotations

import json
import re
import warnings
import wave
from pathlib import Path

import numpy as np
import torch

from indic_tiny_tts.constants import LANG_ID, SPK_ID, STYLE_ID
from indic_tiny_tts.frontend.tokenizer import Tokenizer
from indic_tiny_tts.model.acoustic import MultiCondMatcha
from indic_tiny_tts.model.vocoder import VocosV0
from indic_tiny_tts import textnorm
CONFIG = "config.json"
ACOUSTIC = "model.safetensors"
VOCODER = "vocoder.safetensors"
DEFAULT_REPO = "sulabhkatiyar/indic-tiny-tts-hindi"  # rewritten by tts.release.build_hf

# characters a model's vocabulary may lack, mapped to the nearest pause it knows (anything else unknown is dropped)
_PAUSE_LIKE = {":": ",", ";": ",", "…": ".", "–": ",", "—": ","}
_SENTENCE_END = re.compile(r"(?<=[।?!.])\s+")
_MAX_CHUNK = 250  # characters; longer sentences are split at commas


def pick_device(device=None) -> torch.device:
    """None/'auto' -> cuda if available, else cpu. (Apple 'mps' works but is slower than cpu for this small model.)"""
    if device in (None, "auto"):
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device(device)


def _resolve(path_or_repo: str, revision: str | None = None) -> Path:
    p = Path(path_or_repo).expanduser()
    if p.is_dir():
        return p
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(path_or_repo, revision=revision, allow_patterns=[CONFIG, ACOUSTIC, VOCODER]))


class TinyTTS:
    def __init__(self, folder: str | Path, device=None, threads: int | None = None):
        from safetensors.torch import load_file

        folder = Path(folder)
        self.config = cfg = json.loads((folder / CONFIG).read_text(encoding="utf-8"))
        if threads:
            torch.set_num_threads(int(threads))
        self.device = pick_device(device)
        self.lang = cfg["language"]
        self.sample_rate = int(cfg["sample_rate"])
        self.voices = dict(cfg["voices"])  # friendly name -> internal speaker id, e.g. {"female": "hi_F"}
        self.default_voice = cfg.get("default_voice", next(iter(self.voices)))
        self.tokenizer = Tokenizer.from_dict(cfg["vocab"])  # strict: refuses a different text normaliser version

        acoustic = MultiCondMatcha(cfg["model_cfg"], len(self.tokenizer))
        acoustic.load_state_dict(load_file(str(folder / ACOUSTIC)), strict=True)
        acoustic.set_mel_stats(*cfg["mel_stats"])
        self.acoustic = acoustic.to(self.device).eval()
        voc = VocosV0(cfg["vocoder"]["backbone"], cfg["vocoder"]["head"])
        voc.load_state_dict(load_file(str(folder / VOCODER)), strict=True)
        self.vocoder = voc.to(self.device).eval()

        syn = cfg.get("synthesis", {})
        self.n_timesteps = int(syn.get("n_timesteps", 4))
        self.temperature = float(syn.get("temperature", 0.667))
        self.length_scale = dict(syn.get("length_scale", {}))  # per internal speaker id
        self.style = syn.get("style", "read")
        self.pause_s = float(syn.get("sentence_pause_s", 0.15))

    @classmethod
    def from_pretrained(cls, path_or_repo: str, device=None, revision: str | None = None,
                        threads: int | None = None) -> "TinyTTS":
        return cls(_resolve(path_or_repo, revision), device=device, threads=threads)

    # ------------------------------------------------------------------ text
    def normalize(self, text: str) -> str:
        """Raw text -> the exact character string the model reads (numbers spelled out, unknown symbols handled)."""
        norm = textnorm.text_for_chars(text, self.lang)
        known = self.tokenizer.id
        out, dropped = [], set()
        for ch in norm:
            if "c:" + ch in known or ch == " ":
                out.append(ch)
            elif _PAUSE_LIKE.get(ch) and "c:" + _PAUSE_LIKE[ch] in known:
                out.append(_PAUSE_LIKE[ch])
            else:
                dropped.add(ch)
                out.append(" ")
        if dropped:
            warnings.warn(f"unsupported characters skipped: {''.join(sorted(dropped))!r} "
                          f"(this model reads {self.lang} script only)", stacklevel=3)
        return re.sub(r"\s+", " ", "".join(out)).strip()

    def _chunks(self, norm: str) -> list[str]:
        chunks = []
        for sent in _SENTENCE_END.split(norm):
            while len(sent) > _MAX_CHUNK:
                cut = sent.rfind(",", 0, _MAX_CHUNK)
                cut = cut + 1 if cut > 0 else sent.rfind(" ", 0, _MAX_CHUNK)
                if cut <= 0:
                    cut = _MAX_CHUNK
                chunks.append(sent[:cut].strip())
                sent = sent[cut:].strip()
            chunks.append(sent.strip())
        return [c for c in chunks if any(ch.isalpha() for ch in c)]

    def _ids(self, chunk: str) -> list[int]:
        ids = [self.tokenizer.id["c:" + ch] for ch in chunk]
        if self.tokenizer.add_blank:  # Matcha convention: blank (id 0) between and around every symbol
            out = [0] * (2 * len(ids) + 1)
            out[1::2] = ids
            ids = out
        return ids

    # ------------------------------------------------------------------ audio
    @torch.inference_mode()
    def synthesize(self, text: str, voice: str | None = None, speed: float = 1.0, seed: int | None = None) -> np.ndarray:
        """Text -> mono float32 waveform in [-1, 1] at `self.sample_rate`. speed > 1 talks faster."""
        voice = voice or self.default_voice
        if voice not in self.voices:
            raise ValueError(f"unknown voice {voice!r}; choose from {sorted(self.voices)}")
        spk = self.voices[voice]
        length_scale = float(self.length_scale.get(spk, 1.0)) / float(speed)
        dev = self.device
        gen = torch.Generator(device=dev).manual_seed(int(seed)) if seed is not None else None
        lang_t = torch.tensor([LANG_ID[self.lang]], device=dev)
        spk_t = torch.tensor([SPK_ID[spk]], device=dev)
        style_t = torch.tensor([STYLE_ID[self.style]], device=dev)
        pause = np.zeros(int(self.pause_s * self.sample_rate), dtype=np.float32)
        pieces = []
        for chunk in self._chunks(self.normalize(text)):
            ids = self._ids(chunk)
            res = self.acoustic.synthesise(torch.tensor([ids], device=dev), torch.tensor([len(ids)], device=dev),
                                           lang_t, spk_t, style_t, n_timesteps=self.n_timesteps,
                                           temperature=self.temperature, length_scale=length_scale, generator=gen)
            mel = res["mel"][:, :, :int(res["mel_lengths"][0])]
            wav = self.vocoder.decode(mel.float()).squeeze(0).clamp(-1, 1).float().cpu().numpy()
            if pieces:
                pieces.append(pause)
            pieces.append(wav)
        return np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)

    def save_wav(self, wav: np.ndarray, path: str | Path) -> None:
        """16-bit PCM WAV via the standard library (no soundfile needed)."""
        pcm = (np.clip(wav, -1.0, 1.0) * 32767.0).astype("<i2")
        with wave.open(str(path), "wb") as fh:
            fh.setnchannels(1)
            fh.setsampwidth(2)
            fh.setframerate(self.sample_rate)
            fh.writeframes(pcm.tobytes())

    def tts_to_file(self, text: str, path: str | Path, **kw) -> Path:
        self.save_wav(self.synthesize(text, **kw), path)
        return Path(path)


def _main(argv=None) -> int:
    import argparse
    import time

    ap = argparse.ArgumentParser(description="Synthesize speech with a released indic-tiny-tts model.")
    ap.add_argument("text")
    ap.add_argument("--model", default=DEFAULT_REPO, help="HF repo id or local folder")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--device", default=None, help="cpu | cuda | mps (default: cuda if available, else cpu)")
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("-o", "--out", default="out.wav")
    a = ap.parse_args(argv)
    tts = TinyTTS.from_pretrained(a.model, device=a.device, threads=a.threads)
    t0 = time.perf_counter()
    wav = tts.synthesize(a.text, voice=a.voice, speed=a.speed, seed=a.seed)
    dt = time.perf_counter() - t0
    tts.save_wav(wav, a.out)
    dur = len(wav) / tts.sample_rate
    print(f"wrote {a.out}: {dur:.2f} s audio in {dt:.2f} s (real-time factor {dt / max(dur, 1e-9):.3f})")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
