# Licences

## Model weights: CC-BY-4.0

`model.safetensors` (the acoustic model) is licensed under the Creative Commons Attribution 4.0 International licence (https://creativecommons.org/licenses/by/4.0/legalcode). It was trained on the Hindi part of the Rasa dataset by AI4Bharat (CC-BY-4.0, https://huggingface.co/datasets/ai4bharat/Rasa).

When you use or share it, credit this model (link to its Hugging Face page) and the Rasa dataset (citation in README.md).

Changes made to the Rasa data before training: audio resampled from 48 kHz to 24 kHz; emotional-style recordings and clips shorter than 0.5 s or longer than 20 s removed; about 8 hours per speaker selected; text normalised (Unicode NFC, numbers written out in words).

`vocoder.safetensors` is an unchanged copy of the pretrained Vocos weights `charactr/vocos-mel-24khz` (revision 0feb3fdd929bcd6649e0e7c5a688cf7dd012ef21), released under the MIT licence by its authors and trained on LibriTTS (CC-BY-4.0).

## Code: MIT

The Python package in `indic_tiny_tts/` is released under the MIT licence:

```
MIT License

Copyright (c) 2026 Sulabh Katiyar

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Third-party code included

| Folder | Source | Licence | Licence text |
|---|---|---|---|
| `indic_tiny_tts/vendor/matcha/` | Matcha-TTS, https://github.com/shivammehta25/Matcha-TTS (modified, see `UPSTREAM.txt`) | MIT | `indic_tiny_tts/vendor/matcha/LICENSE` |
| `indic_tiny_tts/vendor/vocos/` | Vocos, https://github.com/gemelo-ai/vocos (subset, see `UPSTREAM.txt`) | MIT | `indic_tiny_tts/vendor/vocos/LICENSE` |
| `indic_tiny_tts/textnorm/_number_tables.py` | number word tables adapted from AI4Bharat indic-numtowords | MIT | `indic_tiny_tts/textnorm/LICENSE-indic_numtowords` |

No GPL component (such as eSpeak) is used or needed at any point of inference.
