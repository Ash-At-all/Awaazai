# Vendored from shivammehta25/Matcha-TTS matcha/models/components/flow_matching.py (MIT).
# LOCAL MODS (see UPSTREAM.txt): no pylogger; cfm_params may be a dict; inference_mode -> no_grad; optional
# `generator` for reproducible noise; compute_loss: t/z drawn in fp32, MSE reduction in fp32 (fp16 AMP safety).
from abc import ABC

import torch

from indic_tiny_tts.vendor.matcha.decoder import Decoder


class BASECFM(torch.nn.Module, ABC):
    def __init__(
        self,
        n_feats,
        cfm_params,
        n_spks=1,
        spk_emb_dim=128,
    ):
        super().__init__()
        self.n_feats = n_feats
        self.n_spks = n_spks
        self.spk_emb_dim = spk_emb_dim
        cfm_params = dict(cfm_params) if isinstance(cfm_params, dict) else vars(cfm_params)
        self.solver = cfm_params.get("solver", "euler")
        self.sigma_min = float(cfm_params.get("sigma_min", 1e-4))

        self.estimator = None

    @torch.no_grad()
    def forward(self, mu, mask, n_timesteps, temperature=1.0, spks=None, cond=None, generator=None):
        """Forward diffusion

        Args:
            mu (torch.Tensor): output of encoder
                shape: (batch_size, n_feats, mel_timesteps)
            mask (torch.Tensor): output_mask
                shape: (batch_size, 1, mel_timesteps)
            n_timesteps (int): number of diffusion steps
            temperature (float, optional): temperature for scaling noise. Defaults to 1.0.
            spks (torch.Tensor, optional): speaker ids. Defaults to None.
                shape: (batch_size, spk_emb_dim)
            cond: Not used but kept for future purposes

        Returns:
            sample: generated mel-spectrogram
                shape: (batch_size, n_feats, mel_timesteps)
        """
        z = torch.randn(mu.shape, generator=generator, device=mu.device, dtype=mu.dtype) * temperature
        t_span = torch.linspace(0, 1, n_timesteps + 1, device=mu.device)
        return self.solve_euler(z, t_span=t_span, mu=mu, mask=mask, spks=spks, cond=cond)

    def solve_euler(self, x, t_span, mu, mask, spks, cond):
        """
        Fixed euler solver for ODEs.
        Args:
            x (torch.Tensor): random noise
            t_span (torch.Tensor): n_timesteps interpolated
                shape: (n_timesteps + 1,)
            mu (torch.Tensor): output of encoder
                shape: (batch_size, n_feats, mel_timesteps)
            mask (torch.Tensor): output_mask
                shape: (batch_size, 1, mel_timesteps)
            spks (torch.Tensor, optional): speaker ids. Defaults to None.
                shape: (batch_size, spk_emb_dim)
            cond: Not used but kept for future purposes
        """
        t, _, dt = t_span[0], t_span[-1], t_span[1] - t_span[0]

        # I am storing this because I can later plot it by putting a debugger here and saving it to a file
        # Or in future might add like a return_all_steps flag
        sol = []

        for step in range(1, len(t_span)):
            dphi_dt = self.estimator(x, mask, mu, t, spks, cond)

            x = x + dt * dphi_dt
            t = t + dt
            sol.append(x)
            if step < len(t_span) - 1:
                dt = t_span[step + 1] - t

        return sol[-1]

    def compute_loss(self, x1, mask, mu, spks=None, cond=None, generator=None):
        """Computes diffusion loss

        Args:
            x1 (torch.Tensor): Target
                shape: (batch_size, n_feats, mel_timesteps)
            mask (torch.Tensor): target mask
                shape: (batch_size, 1, mel_timesteps)
            mu (torch.Tensor): output of encoder
                shape: (batch_size, n_feats, mel_timesteps)
            spks (torch.Tensor, optional): speaker embedding. Defaults to None.
                shape: (batch_size, spk_emb_dim)

        Returns:
            loss: conditional flow matching loss
            y: conditional flow
                shape: (batch_size, n_feats, mel_timesteps)
        """
        b, _, t = mu.shape

        x1, mu = x1.float(), mu.float()
        # random timestep
        t = torch.rand([b, 1, 1], device=mu.device, dtype=torch.float32, generator=generator)
        # sample noise p(x_0)
        z = torch.randn(x1.shape, device=x1.device, dtype=torch.float32, generator=generator)

        y = (1 - (1 - self.sigma_min) * t) * z + t * x1
        u = x1 - (1 - self.sigma_min) * z

        # LOCAL MOD: t.squeeze() -> t.view(b) (batch of 1 gave a 0-d tensor); loss reduced in fp32. Upstream's
        # mse_loss(reduction="sum") also summed padded frames (estimator output is masked, u is not); here the
        # squared error is masked so padded frames contribute nothing.
        pred = self.estimator(y, mask, mu, t.view(b), spks).float()
        with torch.autocast(device_type=pred.device.type, enabled=False):
            loss = torch.sum((pred - u) ** 2 * mask) / (torch.sum(mask) * u.shape[1])
        return loss, y


class CFM(BASECFM):
    def __init__(self, in_channels, out_channel, cfm_params, decoder_params, n_spks=1, spk_emb_dim=64):
        super().__init__(
            n_feats=in_channels,
            cfm_params=cfm_params,
            n_spks=n_spks,
            spk_emb_dim=spk_emb_dim,
        )

        in_channels = in_channels + (spk_emb_dim if n_spks > 1 else 0)
        # Just change the architecture of the estimator here
        self.estimator = Decoder(in_channels=in_channels, out_channels=out_channel, **decoder_params)
