"""indic-tiny-tts: small single-language text-to-speech models (PyTorch, CPU/CUDA/MPS). See README.md."""
from .infer import TinyTTS, pick_device

__all__ = ["TinyTTS", "pick_device"]
__version__ = "0.1.0"
