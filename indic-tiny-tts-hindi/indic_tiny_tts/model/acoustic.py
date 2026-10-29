"""MultiCondMatcha: Matcha-TTS (vendored) with language + speaker + style conditioning.

Conditioning vector c = concat(lang_emb[12 x Dl], spk_emb[24 x Ds], style_emb[4 x Dst]) is passed exactly where
upstream Matcha passes its speaker embedding `spks` (concatenated to the encoder input, so it also reaches the
duration predictor and the mean projection, and concatenated to the U-Net decoder input).

Precision: encoder / decoder may run under fp16 autocast. MAS, the prior loss, the duration loss and every loss
reduction run in fp32 with autocast disabled (see `forward`). Mel normalisation lives inside the model
(`mel_mean`, `mel_std` buffers); `forward` takes RAW log-mels and `synthesise` returns de-normalised log-mels.

`python -m tts.model.acoustic --count` prints exact parameter counts for configs S and T.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import torch
import torch.nn as nn

from indic_tiny_tts.constants import LANGS, N_MELS, SPEAKERS, STYLES
from indic_tiny_tts.model.mas import maximum_path
from indic_tiny_tts.vendor.matcha.flow_matching import CFM
from indic_tiny_tts.vendor.matcha.model_utils import duration_loss, fix_len_compatibility, generate_path, sequence_mask
from indic_tiny_tts.vendor.matcha.text_encoder import TextEncoder

CONFIG_DIR = Path(__file__).resolve().parent.parent / "configs"


def load_config(name_or_path: str) -> dict:
    """'S' / 'T' -> tts/configs/<name>.yaml, else a path. Returns the full yaml dict."""
    import yaml

    p = Path(name_or_path)
    if not p.suffix:
        p = CONFIG_DIR / f"{name_or_path}.yaml"
    with open(p) as f:
        return yaml.safe_load(f)


class MultiCondMatcha(nn.Module):
    def __init__(self, model_cfg: dict, n_vocab: int):
        super().__init__()
        cfg = model_cfg
        self.n_vocab = n_vocab
        self.n_feats = int(cfg.get("n_feats", N_MELS))
        cond = cfg.get("cond", {})
        self.lang_dim = int(cond.get("lang_dim", 32))
        self.spk_dim = int(cond.get("spk_dim", 64))
        self.style_dim = int(cond.get("style_dim", 16))
        self.cond_dim = self.lang_dim + self.spk_dim + self.style_dim
        self.prior_loss_enabled = bool(cfg.get("prior_loss", True))
        self.mas_impl = cfg.get("mas_impl", "auto")

        # fixed-size tables: rows never move (tts/constants.py)
        self.lang_emb = nn.Embedding(len(LANGS), self.lang_dim)
        self.spk_emb = nn.Embedding(len(SPEAKERS), self.spk_dim)
        self.style_emb = nn.Embedding(len(STYLES), self.style_dim)

        enc = dict(cfg["encoder"])
        enc["n_feats"] = self.n_feats
        width = enc["n_channels"] + self.cond_dim
        # upstream RoPE rotates int(head_dim * 0.5) features and needs that number to be even
        assert width % enc["n_heads"] == 0 and int(width // enc["n_heads"] * 0.5) % 2 == 0, (
            f"encoder width {width} (n_channels + cond_dim) / n_heads must be divisible by 4")
        dp = {
            "filter_channels_dp": enc.get("filter_channels_dp", 256),
            "kernel_size": cfg.get("duration_predictor", {}).get("kernel_size", 3),
            "p_dropout": cfg.get("duration_predictor", {}).get("p_dropout", enc.get("p_dropout", 0.1)),
        }
        # n_spks=2 just switches on Matcha's "concat spks" path; the vector itself is our conditioning vector
        self.encoder = TextEncoder("RoPE Encoder", enc, dp, n_vocab, n_spks=2, spk_emb_dim=self.cond_dim)

        dec = dict(cfg["decoder"])
        dec["channels"] = tuple(dec["channels"])
        self.n_down = len(dec["channels"]) - 1  # U-Net downsamplings (Matcha: one per channel entry but the last)
        self.decoder = CFM(
            in_channels=2 * self.n_feats,
            out_channel=self.n_feats,
            cfm_params=cfg.get("cfm", {"solver": "euler", "sigma_min": 1e-4}),
            decoder_params=dec,
            n_spks=2,
            spk_emb_dim=self.cond_dim,
        )

        self.register_buffer("mel_mean", torch.tensor(0.0))
        self.register_buffer("mel_std", torch.tensor(1.0))

    # ------------------------------------------------------------------ helpers
    def set_mel_stats(self, mean: float, std: float) -> None:
        self.mel_mean.fill_(float(mean))
        self.mel_std.fill_(float(std))

    def cond(self, lang, spk, style) -> torch.Tensor:
        return torch.cat([self.lang_emb(lang), self.spk_emb(spk), self.style_emb(style)], dim=-1)

    def len_factor(self) -> int:
        return 2**self.n_down

    # ------------------------------------------------------------------ training
    def forward(self, x, x_lengths, y, y_lengths, lang, spk, style, out_size: int | None = None) -> dict:
        dev = x.device.type
        spks = self.cond(lang, spk, style)
        mu_x, logw, x_mask = self.encoder(x, x_lengths, spks)

        with torch.autocast(device_type=dev, enabled=False):
            mu_x = mu_x.float()
            logw = logw.float()
            x_mask = x_mask.float()
            y = (y.float() - self.mel_mean) / self.mel_std
            y_max_length = y.shape[-1]
            y_mask = sequence_mask(y_lengths, y_max_length).unsqueeze(1).to(x_mask)
            attn_mask = x_mask.unsqueeze(-1) * y_mask.unsqueeze(2)

            # MAS on the Gaussian log-likelihood log N(y | mu_x, I) (upstream Matcha), fp32, no grad
            with torch.no_grad():
                const = -0.5 * math.log(2 * math.pi) * self.n_feats
                factor = -0.5 * torch.ones_like(mu_x)
                y_square = torch.matmul(factor.transpose(1, 2), y**2)
                y_mu_double = torch.matmul(2.0 * (factor * mu_x).transpose(1, 2), y)
                mu_square = torch.sum(factor * (mu_x**2), 1).unsqueeze(-1)
                log_prior = y_square - y_mu_double + mu_square + const
                attn = maximum_path(log_prior, attn_mask.squeeze(1), impl=self.mas_impl).detach()

            logw_ = torch.log(1e-8 + torch.sum(attn.unsqueeze(1), -1)) * x_mask
            dur_loss = duration_loss(logw, logw_, x_lengths)

            if out_size is not None:
                out_size = fix_len_compatibility(int(out_size), self.n_down)
                y, attn_seg, y_mask = self._cut(y, attn, y_lengths, out_size)
            else:
                pad = fix_len_compatibility(y_max_length, self.n_down) - y_max_length
                attn_seg = attn
                if pad:
                    y = nn.functional.pad(y, (0, pad))
                    y_mask = nn.functional.pad(y_mask, (0, pad))
                    attn_seg = nn.functional.pad(attn, (0, pad))

            mu_y = torch.matmul(attn_seg.transpose(1, 2), mu_x.transpose(1, 2)).transpose(1, 2)

            if self.prior_loss_enabled:
                prior_loss = torch.sum(0.5 * ((y - mu_y) ** 2 + math.log(2 * math.pi)) * y_mask)
                prior_loss = prior_loss / (torch.sum(y_mask) * self.n_feats)
            else:
                prior_loss = torch.zeros((), device=y.device)

        # decoder under the caller's autocast; its loss is reduced in fp32 inside compute_loss
        diff_loss, _ = self.decoder.compute_loss(x1=y, mask=y_mask, mu=mu_y, spks=spks)
        return {
            "dur_loss": dur_loss.float(),
            "prior_loss": prior_loss.float(),
            "diff_loss": diff_loss.float(),
            "attn": attn.detach(),
        }

    @staticmethod
    def _cut(y, attn, y_lengths, out_size):
        """Random out_size-frame segment per item (Grad-TTS/Matcha trick). Uses the torch CPU RNG."""
        b = y.shape[0]
        y_lengths_cpu = y_lengths.detach().cpu()
        max_offset = (y_lengths_cpu - out_size).clamp(min=0)
        offset = (torch.rand(b) * (max_offset + 1).float()).long().clamp(max=max_offset)
        seg_len = torch.clamp(y_lengths_cpu, max=out_size)
        idx = offset.unsqueeze(1) + torch.arange(out_size).unsqueeze(0)  # [B, out]
        valid = torch.arange(out_size).unsqueeze(0) < seg_len.unsqueeze(1)
        idx = torch.where(valid, idx, torch.zeros_like(idx)).clamp(max=y.shape[-1] - 1).to(y.device)
        valid = valid.to(y.device).unsqueeze(1).to(y.dtype)  # [B,1,out]
        y_cut = torch.gather(y, 2, idx.unsqueeze(1).expand(-1, y.shape[1], -1)) * valid
        attn_cut = torch.gather(attn, 2, idx.unsqueeze(1).expand(-1, attn.shape[1], -1)) * valid
        return y_cut, attn_cut, valid

    # ------------------------------------------------------------------ inference
    @torch.no_grad()
    def synthesise(self, x, x_lengths, lang, spk, style, n_timesteps=4, temperature=0.667, length_scale=1.0,
                   generator: torch.Generator | None = None) -> dict:
        spks = self.cond(lang, spk, style)
        mu_x, logw, x_mask = self.encoder(x, x_lengths, spks)
        mu_x, logw, x_mask = mu_x.float(), logw.float(), x_mask.float()
        w = torch.exp(logw) * x_mask
        w_ceil = torch.ceil(w) * length_scale
        y_lengths = torch.clamp_min(torch.sum(w_ceil, [1, 2]), 1).long()
        y_max_length = int(y_lengths.max())
        y_max_length_ = fix_len_compatibility(y_max_length, self.n_down)

        y_mask = sequence_mask(y_lengths, y_max_length_).unsqueeze(1).to(x_mask.dtype)
        attn_mask = x_mask.unsqueeze(-1) * y_mask.unsqueeze(2)
        attn = generate_path(w_ceil.squeeze(1), attn_mask.squeeze(1))
        mu_y = torch.matmul(attn.transpose(1, 2), mu_x.transpose(1, 2)).transpose(1, 2)

        dec = self.decoder(mu_y, y_mask, n_timesteps, temperature, spks, generator=generator).float()
        dec = dec[:, :, :y_max_length]
        mel = dec * self.mel_std + self.mel_mean
        mel = mel * sequence_mask(y_lengths, y_max_length).unsqueeze(1).to(mel.dtype)
        return {"mel": mel, "mel_lengths": y_lengths, "durations": w_ceil.squeeze(1).round().long()}


# ---------------------------------------------------------------------- param counts
def count_params(model: MultiCondMatcha) -> dict:
    def n(m):
        return sum(p.numel() for p in m.parameters())

    enc = model.encoder
    token = n(enc.emb)
    cond = n(model.lang_emb) + n(model.spk_emb) + n(model.style_emb)
    dp = n(enc.proj_w)
    encoder = n(enc) - token - dp
    decoder = n(model.decoder)
    total = n(model)
    assert total == token + cond + encoder + dp + decoder
    return {"token_emb": token, "cond_emb": cond, "encoder": encoder, "duration_predictor": dp,
            "decoder": decoder, "total": total}


def _main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--configs", default="S,T")
    ap.add_argument("--n-vocab", type=int, default=320)
    a = ap.parse_args()
    if a.count:
        rows = []
        for name in a.configs.split(","):
            m = MultiCondMatcha(load_config(name)["model"], a.n_vocab)
            rows.append((name, count_params(m)))
        keys = list(rows[0][1].keys())
        print(f"n_vocab={a.n_vocab}")
        print("component".ljust(20) + "".join(r[0].rjust(14) for r in rows))
        for k in keys:
            print(k.ljust(20) + "".join(f"{r[1][k]:>14,}" for r in rows))


if __name__ == "__main__":
    _main()
