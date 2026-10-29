
import sys
from huggingface_hub import snapshot_download

print("Finding Hindi TTS model...")

model_path = snapshot_download(
    "sulabhkatiyar/indic-tiny-tts-hindi"
)

sys.path.insert(0, model_path)

from indic_tiny_tts import TinyTTS

print("Loading Hindi TTS model on CPU...")

tts = TinyTTS.from_pretrained(
    "sulabhkatiyar/indic-tiny-tts-hindi",
    device="cpu",
)

text = "नमस्ते! आपका स्वागत है। यह आवाज़ एआई के लिए एक परीक्षण है।"

audio = tts.synthesize(text, voice="female")
tts.save_wav(audio, "hindi_test.wav")

print("Success! Audio saved as hindi_test.wav")
