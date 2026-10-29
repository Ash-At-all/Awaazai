---
license: cc-by-4.0
language:
- hi
pipeline_tag: text-to-speech
datasets:
- ai4bharat/Rasa
tags:
- text-to-speech
- tts
- hindi
- speech-synthesis
- on-device
- cpu
inference: false
---

# Indic Tiny TTS: Hindi

A small, fast Hindi text-to-speech model. Give it Hindi text in Devanagari script and it speaks it in a female or a male voice. It runs many times faster than real time on an ordinary laptop CPU, so no GPU is needed.

| | |
|---|---|
| Language | Hindi (Devanagari script) |
| Voices | `female`, `male` |
| Audio | 24 kHz, mono |
| Size | 22.5 million parameters (about 90 MB download) |
| Runs on | CPU (Windows, Linux, Mac), NVIDIA GPU (CUDA), Apple silicon |
| Needs | Python 3.9+ and PyTorch. No eSpeak or other system packages. |

**Listen:** [female sample](samples/female.wav) · [male sample](samples/male.wav)

## Quick start

```bash
pip install torch numpy safetensors huggingface_hub
```

```python
import sys
from huggingface_hub import snapshot_download

sys.path.insert(0, snapshot_download("sulabhkatiyar/indic-tiny-tts-hindi"))  # downloads the model and its small Python package
from indic_tiny_tts import TinyTTS

tts = TinyTTS.from_pretrained("sulabhkatiyar/indic-tiny-tts-hindi")  # uses the NVIDIA GPU if there is one, else the CPU
wav = tts.synthesize("नमस्ते! आज मौसम बहुत सुहाना है।", voice="female")
tts.save_wav(wav, "hello.wav")
```

`wav` is a NumPy array of 24 kHz audio. `voice` is `"female"` or `"male"`. Optional: `speed=1.2` speaks faster, and `seed=0` gives the same output every time.

### Choose where it runs

```python
tts = TinyTTS.from_pretrained("sulabhkatiyar/indic-tiny-tts-hindi", device="cpu")               # any computer
tts = TinyTTS.from_pretrained("sulabhkatiyar/indic-tiny-tts-hindi", device="cuda")              # NVIDIA GPU
tts = TinyTTS.from_pretrained("sulabhkatiyar/indic-tiny-tts-hindi", device="cpu", threads=1)    # Mac with Apple silicon (fastest there)
```

On a Mac, `device="mps"` (the Apple GPU) also works, but for a model this small the CPU with one thread is faster.

### Install as a package (optional)

This adds an `indic-tiny-tts` command:

```bash
hf download sulabhkatiyar/indic-tiny-tts-hindi --local-dir indic-tiny-tts-hindi
pip install ./indic-tiny-tts-hindi
indic-tiny-tts "नमस्ते, आप कैसे हैं?" --model ./indic-tiny-tts-hindi --voice male -o hello.wav
```

## Speed

The table shows the **real-time factor**: the time it takes to make the audio, divided by the length of the audio. Lower is faster. For example, 0.05 means 10 seconds of speech is ready in half a second.

| Hardware | Setting | Real-time factor | Time for a typical 3.6 s sentence |
|---|---|---:|---:|
| Apple M1 Mac (8 GB), CPU | 1 thread | 0.026 | 0.10 s |
| Apple M1 Mac (8 GB), Apple GPU (`mps`) | | 0.043 | 0.20 s |
| Kaggle CPU notebook (4 vCPU) | 1 thread | 0.119 | about 0.43 s |
| Kaggle CPU notebook (4 vCPU) | 4 threads | 0.080 | about 0.29 s |
| NVIDIA T4 GPU (Kaggle) | | 0.016 | 0.07 s |

How we measured: 30 Hindi sentences (3.6 s of speech each, typically), after one warm-up sentence. The time covers everything from text to audio, with standard 32-bit PyTorch (version 2.14 on the Mac, 2.11 on Kaggle). On the Mac, more CPU threads made it slower, not faster, so use `threads=1` there. To measure on your own machine, run this inside the downloaded folder:

```bash
python -m indic_tiny_tts.latency --model . --device cpu --threads 1
```

## How good is it?

On 300 held-out sentences, a speech recogniser understood this model's speech about as well as the original human recordings: it misheard 3.0 % of the characters, against 3.6 % for the real recordings. Comparisons with other Hindi TTS models will be added later.

## Good to know

- **Hindi script only.** English words in Latin letters (`hello`) are skipped with a warning. Write them in Devanagari (`हेलो`).
- **Numbers are read out in Hindi:** `25` becomes पच्चीस, `3.5%` becomes तीन दशमलव पाँच प्रतिशत, and `₹500` becomes पाँच सौ रुपये. Phone numbers, dates and times are read as plain numbers, so write them out in words if that matters.
- **Long text is fine.** It is split into sentences at `।`, `?`, `!` and `.`, which are spoken one after another.
- **Style:** a calm reading voice. The model learned from about 16 hours of studio speech by two speakers.
- **Please use it responsibly.** Do not use it to pass yourself off as the original speakers or to mislead people.

## Training data and credits

- **Voices: the Rasa dataset by AI4Bharat** ([ai4bharat/Rasa](https://huggingface.co/datasets/ai4bharat/Rasa)), licence CC-BY-4.0. We used about 8 hours from each of the Hindi female and Hindi male speakers: the read, conversation and command recordings, leaving out the emotional ones. Our changes: audio resampled from 48 kHz to 24 kHz, clips shorter than 0.5 s or longer than 20 s left out, and text normalised (for example, numbers written out in words).
- **Vocoder** (the part that turns the model's output into sound): [Vocos](https://github.com/gemelo-ai/vocos), with the pretrained [charactr/vocos-mel-24khz](https://huggingface.co/charactr/vocos-mel-24khz) weights used unchanged (MIT licence; trained by its authors on LibriTTS).
- **Model design:** based on [Matcha-TTS](https://github.com/shivammehta25/Matcha-TTS) (MIT licence), trained from scratch on the data above.
- **Number reading:** word tables adapted from AI4Bharat's [indic-numtowords](https://github.com/AI4Bharat/indic-numtowords) (MIT licence).

## Licence

- Model weights (`model.safetensors`): **CC-BY-4.0**. You may use them, also commercially, if you give credit to this model and to the Rasa dataset (see Citation). Vocoder weights (`vocoder.safetensors`): the unchanged pretrained Vocos weights, **MIT** licence by their authors.
- Code (`indic_tiny_tts/`): **MIT**.
- Details and third-party notices: [LICENSE.md](LICENSE.md).

## Citation

If you use this model, please cite it:

```bibtex
@misc{katiyar2026indictinyttshindi,
  author       = {Sulabh Katiyar},
  title        = {Indic Tiny TTS: Hindi},
  year         = {2026},
  publisher    = {Hugging Face},
  howpublished = {\url{https://huggingface.co/sulabhkatiyar/indic-tiny-tts-hindi}}
}
```

Please also cite the dataset and the work it builds on:

```bibtex
@inproceedings{ai4bharat2024rasa,
  author    = {Praveen Srinivasa Varadhan and Ashwin Sankar and Giri Raju and Mitesh M. Khapra},
  title     = {{Rasa: Building Expressive Speech Synthesis Systems for Indian Languages in Low-resource Settings}},
  booktitle = {Proc. INTERSPEECH 2024},
  year      = {2024}
}

@inproceedings{mehta2024matcha,
  author    = {Shivam Mehta and Ruibo Tu and Jonas Beskow and {\'E}va Sz{\'e}kely and Gustav Eje Henter},
  title     = {{Matcha-TTS}: A fast {TTS} architecture with conditional flow matching},
  booktitle = {Proc. ICASSP 2024},
  year      = {2024}
}

@inproceedings{siuzdak2024vocos,
  author    = {Hubert Siuzdak},
  title     = {Vocos: Closing the gap between time-domain and Fourier-based neural vocoders for high-quality audio synthesis},
  booktitle = {Proc. ICLR 2024},
  year      = {2024}
}
```
