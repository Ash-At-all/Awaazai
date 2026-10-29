"""from https://github.com/jaywalnut310/glow-tts (via matcha/utils/model.py)

Vendored subset: sequence_mask, fix_len_compatibility, convert_pad_shape, generate_path, duration_loss.
Local modifications: see UPSTREAM.txt (normalize/denormalize dropped; fix_len_compatibility accepts ints).
"""

import torch


def sequence_mask(length, max_length=None):
    if max_length is None:
        max_length = length.max()
    x = torch.arange(max_length, dtype=length.dtype, device=length.device)
    return x.unsqueeze(0) < length.unsqueeze(1)


def fix_len_compatibility(length, num_downsamplings_in_unet=2):
    factor = 2**num_downsamplings_in_unet
    if isinstance(length, torch.Tensor):
        if torch.onnx.is_in_onnx_export():
            return (torch.ceil(length / factor) * factor).to(length.dtype)
        length = int(length.item())
    return int(-(-int(length) // factor) * factor)


def convert_pad_shape(pad_shape):
    inverted_shape = pad_shape[::-1]
    pad_shape = [item for sublist in inverted_shape for item in sublist]
    return pad_shape


def generate_path(duration, mask):
    b, t_x, t_y = mask.shape
    cum_duration = torch.cumsum(duration, 1)

    cum_duration_flat = cum_duration.view(b * t_x)
    path = sequence_mask(cum_duration_flat, t_y).to(mask.dtype)
    path = path.view(b, t_x, t_y)
    path = path - torch.nn.functional.pad(path, convert_pad_shape([[0, 0], [1, 0], [0, 0]]))[:, :-1]
    path = path * mask
    return path


def duration_loss(logw, logw_, lengths):
    loss = torch.sum((logw - logw_) ** 2) / torch.sum(lengths)
    return loss
