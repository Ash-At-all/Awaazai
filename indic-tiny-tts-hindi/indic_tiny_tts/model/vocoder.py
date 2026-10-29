"""Pretrained Vocos (charactr/vocos-mel-24khz, MIT) on the vendored classes: the V0 eval vocoder.

load_vocos_v0(device) -> VocosV0 with .decode(mel[B,100,T] raw log-mel) -> wav[B,S] (24 kHz, fp32).
Weights are public; no token is used. The feature-extractor keys of the checkpoint (torchaudio mel buffers) are
dropped (our mel is tts/data/mel.py); every backbone/head key must match exactly (strict load).
"""
from __future__ import annotations

import torch
import torch.nn as nn

from indic_tiny_tts.vendor.vocos.heads import ISTFTHead
from indic_tiny_tts.vendor.vocos.models import VocosBackbone

REPO_ID = "charactr/vocos-mel-24khz"


class VocosV0(nn.Module):
    def __init__(self, backbone_args: dict, head_args: dict):
        super().__init__()
        self.backbone = VocosBackbone(**backbone_args)
        self.head = ISTFTHead(**head_args)

    @torch.no_grad()
    def decode(self, mel: torch.Tensor) -> torch.Tensor:
        dev = mel.device.type
        with torch.autocast(device_type=dev, enabled=False):  # iSTFT and exp(mag) must stay fp32
            return self.head(self.backbone(mel.float()))

    forward = decode


def load_vocos_v0(device="cpu", repo_id: str = REPO_ID, revision: str | None = None) -> VocosV0:
    import yaml  # lazy: the release runtime builds VocosV0 from config.json and never needs yaml
    from huggingface_hub import hf_hub_download

    cfg_path = hf_hub_download(repo_id=repo_id, filename="config.yaml", revision=revision, token=False)
    w_path = hf_hub_download(repo_id=repo_id, filename="pytorch_model.bin", revision=revision, token=False)
    with open(cfg_path) as f:
        cfg = yaml.safe_load(f)
    assert cfg["backbone"]["class_path"].endswith("VocosBackbone"), cfg["backbone"]
    assert cfg["head"]["class_path"].endswith("ISTFTHead"), cfg["head"]
    model = VocosV0(cfg["backbone"]["init_args"], cfg["head"]["init_args"])
    sd = torch.load(w_path, map_location="cpu", weights_only=True)
    sd = {k: v for k, v in sd.items() if not k.startswith("feature_extractor.")}
    model.load_state_dict(sd, strict=True)
    return model.eval().to(device)
