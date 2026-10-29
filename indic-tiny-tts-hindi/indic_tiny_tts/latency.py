"""Measure synthesis speed of a released model on this machine (shipped as `python -m indic_tiny_tts.latency`).

    python -m tts.latency --model FOLDER_OR_REPO [--device cpu|cuda|mps] [--threads N] [--texts FILE] [--repeat 1]

Method (same as the CPU benchmark `tts.bench.run`): one warm-up sentence, then every sentence once (x --repeat);
real-time factor (RTF) = total synthesis time / total audio duration (text normalisation + acoustic model +
vocoder; lower is faster; 0.1 = 10 s of speech in 1 s). Also reports the median per-sentence latency.
--texts: a .txt (one sentence per line) or .jsonl (field "text"; rows with a "lang" field are filtered to the
model's language). Default: a built-in set of everyday sentences (Hindi so far). Prints one JSON object.
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import statistics
import time
from pathlib import Path

import torch

from indic_tiny_tts.infer import DEFAULT_REPO, TinyTTS

SENTENCES = {"hi": [
    "नमस्ते, आप कैसे हैं?",
    "आज मौसम बहुत सुहाना है।",
    "कृपया अगले स्टेशन पर उतरने के लिए तैयार रहें।",
    "भारत एक विशाल देश है जहाँ अनेक भाषाएँ बोली जाती हैं।",
    "मुझे सुबह जल्दी उठकर पार्क में टहलना बहुत पसंद है, क्योंकि उस समय हवा ताज़ी होती है।",
    "इस किताब में बच्चों के लिए कई रोचक कहानियाँ हैं, जिन्हें पढ़कर वे बहुत कुछ सीख सकते हैं।",
    "डॉक्टर ने कहा कि रोज़ थोड़ा व्यायाम करने से स्वास्थ्य अच्छा रहता है।",
    "हमारी ट्रेन शाम सात बजे दिल्ली से निकलेगी और सुबह मुंबई पहुँचेगी।",
]}  # built-in sets; other languages: pass --texts


def load_texts(path: str | None, lang: str, n: int | None) -> list[str]:
    if not path:
        if lang not in SENTENCES:
            raise SystemExit(f"no built-in sentences for {lang!r}; pass --texts FILE")
        texts = list(SENTENCES[lang])
    elif path.endswith(".jsonl"):
        rows = [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]
        texts = [r["text"] for r in rows if r.get("lang", lang) == lang]
    else:
        texts = [line.strip() for line in open(path, encoding="utf-8") if line.strip()]
    return texts[:n] if n else texts


def device_name(dev: torch.device) -> str:
    if dev.type == "cuda":
        return torch.cuda.get_device_name(dev)
    if dev.type == "mps":
        return f"Apple GPU (mps) on {platform.machine()}"
    proc = platform.processor() or platform.machine()
    try:
        if platform.system() == "Darwin":
            import subprocess

            proc = subprocess.run(["sysctl", "-n", "machdep.cpu.brand_string"], capture_output=True,
                                  text=True).stdout.strip() or proc
        elif Path("/proc/cpuinfo").exists():
            for line in open("/proc/cpuinfo"):
                if line.startswith("model name"):
                    proc = line.split(":", 1)[1].strip()
                    break
    except Exception:
        pass
    return f"{proc} ({os.cpu_count()} logical cores)"


def measure(tts: TinyTTS, texts: list[str], voice: str | None = None, repeat: int = 1) -> dict:
    tts.synthesize(texts[0], voice=voice, seed=0)  # warm-up (allocations, kernel selection)
    lat, audio = [], []
    for _ in range(repeat):
        for k, t in enumerate(texts):
            t0 = time.perf_counter()
            wav = tts.synthesize(t, voice=voice, seed=k)
            if tts.device.type == "cuda":
                torch.cuda.synchronize()
            lat.append(time.perf_counter() - t0)
            audio.append(len(wav) / tts.sample_rate)
    return {"n": len(lat), "rtf": sum(lat) / sum(audio), "median_latency_s": statistics.median(lat),
            "median_audio_s": statistics.median(audio), "total_audio_s": sum(audio)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default=DEFAULT_REPO)
    ap.add_argument("--device", default=None)
    ap.add_argument("--threads", type=int, default=None, help="CPU threads (default: torch's choice)")
    ap.add_argument("--texts", default=None)
    ap.add_argument("--n", type=int, default=None, help="use the first N texts")
    ap.add_argument("--voice", default=None)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--out", default=None, help="also write the JSON here")
    a = ap.parse_args(argv)
    t0 = time.perf_counter()
    tts = TinyTTS.from_pretrained(a.model, device=a.device, threads=a.threads)
    load_s = time.perf_counter() - t0
    res = {"device": tts.device.type, "device_name": device_name(tts.device), "threads": torch.get_num_threads(),
           "torch": torch.__version__, "load_s": round(load_s, 2),
           **measure(tts, load_texts(a.texts, tts.lang, a.n), a.voice, a.repeat)}
    s = json.dumps(res, indent=1)
    print(s)
    if a.out:
        Path(a.out).write_text(s + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
