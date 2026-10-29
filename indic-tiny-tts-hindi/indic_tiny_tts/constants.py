"""Fixed id tables shared by data, model and checkpoints. Order is frozen: rows never move."""

LANGS = ["en", "hi", "pa", "bn", "or", "ml", "te", "ta", "kn", "mr", "gu", "as"]
SPEAKERS = [f"{lang}_{g}" for lang in LANGS for g in ("F", "M")]
STYLES = ["read", "conv", "command", "unknown"]  # "unknown" = label-dropout row
STYLE_DROPOUT = 0.15

LANG_ID = {l: i for i, l in enumerate(LANGS)}
SPK_ID = {s: i for i, s in enumerate(SPEAKERS)}
STYLE_ID = {s: i for i, s in enumerate(STYLES)}

SAMPLE_RATE = 24000
N_FFT = 1024
HOP = 256
WIN = 1024
N_MELS = 100
F_MIN = 0.0
F_MAX = 12000.0


def mel_frames(n_samples: int) -> int:
    """Frames produced by a center-padded STFT for n samples."""
    return n_samples // HOP + 1
