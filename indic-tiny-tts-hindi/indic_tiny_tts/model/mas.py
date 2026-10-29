"""Monotonic alignment search (MAS), no compiled extension required.

Semantics follow upstream Matcha/Glow-TTS `maximum_path_c` (vendored as tts/vendor/matcha/monotonic_align_core.pyx.txt):
  value [B, Tx, Ty] float (log-likelihoods), mask [B, Tx, Ty] (1 = valid) -> path [B, Tx, Ty] (0/1, value's dtype)
  Each text token gets >= 1 frame, path is monotonic, starts at (0,0) and ends at (t_x-1, t_y-1).
  Ties in the backtrack go to "stay on the same token" (move diagonal only if strictly better), as upstream.
  Requires t_y >= t_x per item (callers/audit enforce frames >= tokens).

Implementations:
  * `maximum_path_numpy`  - reference: numba-jitted port of the Cython kernel when numba is importable, otherwise a
    pure numpy per-item loop (vectorised over Tx).
  * `maximum_path_torch`  - vectorised over B and Tx, loops over Ty on the value's device (GPU/ROCm-friendly);
    backtrack on device as well.
`maximum_path(value, mask, impl="auto")` dispatches: "auto" = torch on value's device for CUDA/ROCm tensors; for CPU
tensors numba when importable, else torch. Explicit: "torch" | "numpy" (numba if present) | "numpy_py" (never numba).
Threads: numba's prange uses NUMBA_NUM_THREADS and torch CPU ops use OMP_NUM_THREADS / torch.set_num_threads, both
read from the environment at import time (nothing here overrides them).
CPU timings B=32, Tx=200, Ty=900 (M-series Mac): numba 11 ms, upstream Cython 20 ms, torch 68 ms, numpy_py 420 ms.
GPU timings come from tts/train/probe.py; set `model.mas_impl` in the config to override.
"""
from __future__ import annotations

import numpy as np
import torch

try:  # optional (Kaggle images ship numba; the Mac venv does not)
    import numba

    _HAVE_NUMBA = True
except Exception:  # pragma: no cover - depends on env
    numba = None
    _HAVE_NUMBA = False

NEG = -1e9


# ----------------------------------------------------------------------------- numpy / numba reference
def _mp_each_py(path, value, t_x, t_y, max_neg_val=NEG):
    """Pure-numpy port of maximum_path_each (vectorised over x for each y). Mutates value."""
    v = value
    for y in range(1, t_y):
        lo, hi = max(0, t_x + y - t_y), min(t_x, y + 1)
        if lo >= hi:
            continue
        xs = np.arange(lo, hi)
        v_cur = np.where(xs == y, max_neg_val, v[np.minimum(xs, t_x - 1), y - 1])
        prev_idx = np.maximum(xs - 1, 0)
        v_prev = np.where(xs == 0, max_neg_val, v[prev_idx, y - 1])
        v[lo:hi, y] = np.maximum(v_cur, v_prev) + v[lo:hi, y]
    # y == 0: only x == 0 is in-band, v_prev = 0 -> value unchanged
    index = t_x - 1
    for y in range(t_y - 1, -1, -1):
        path[index, y] = 1
        if index != 0 and (index == y or v[index, y - 1] < v[index - 1, y - 1]):
            index -= 1


if _HAVE_NUMBA:

    @numba.njit(cache=False, nogil=True)
    def _mp_each_nb(path, value, t_x, t_y, max_neg_val):  # pragma: no cover - needs numba
        for y in range(t_y):
            for x in range(max(0, t_x + y - t_y), min(t_x, y + 1)):
                if x == y:
                    v_cur = max_neg_val
                else:
                    v_cur = value[x, y - 1]
                if x == 0:
                    if y == 0:
                        v_prev = 0.0
                    else:
                        v_prev = max_neg_val
                else:
                    v_prev = value[x - 1, y - 1]
                value[x, y] = max(v_cur, v_prev) + value[x, y]
        index = t_x - 1
        for y in range(t_y - 1, -1, -1):
            path[index, y] = 1
            if index != 0 and (index == y or value[index, y - 1] < value[index - 1, y - 1]):
                index = index - 1

    @numba.njit(parallel=True, cache=False)
    def _mp_batch_nb(paths, values, t_xs, t_ys, max_neg_val):  # pragma: no cover - needs numba
        for i in numba.prange(values.shape[0]):
            _mp_each_nb(paths[i], values[i], t_xs[i], t_ys[i], max_neg_val)


def maximum_path_numpy(value: torch.Tensor, mask: torch.Tensor, use_numba: bool | None = None) -> torch.Tensor:
    device, dtype = value.device, value.dtype
    value = (value * mask).detach().float().cpu().numpy().astype(np.float32)
    mask_np = mask.detach().cpu().numpy()
    path = np.zeros(value.shape, dtype=np.int32)
    t_xs = mask_np.sum(1)[:, 0].astype(np.int32)
    t_ys = mask_np.sum(2)[:, 0].astype(np.int32)
    if use_numba is None:
        use_numba = _HAVE_NUMBA
    if use_numba:
        _mp_batch_nb(path, value, t_xs, t_ys, np.float32(NEG))
    else:
        for i in range(value.shape[0]):
            _mp_each_py(path[i], value[i], int(t_xs[i]), int(t_ys[i]))
    return torch.from_numpy(path).to(device=device, dtype=dtype)


# ----------------------------------------------------------------------------- torch (device) version
@torch.no_grad()
def maximum_path_torch(value: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
    """Forward DP on value.device (vectorised over B and Tx, 2 kernels per frame); the backtrack decisions are
    computed on device in one shot, then the O(Ty) walk runs on host over a [B, Ty-1, Tx] bool tensor (few ms),
    and the path is built on device with one one_hot. fp32 internally."""
    dtype, device = value.dtype, value.device
    b, t_x, t_y = value.shape
    mask_f = mask.float()
    v = (value.float() * mask_f).transpose(1, 2).contiguous()  # [B, Ty, Tx]
    t_xs = mask_f.sum(1)[:, 0].long()
    t_ys = mask_f.sum(2)[:, 0].long()

    # acc[:, y, 1 + x] = best score of a monotonic path ending at (x, y); column 0 is a -inf sentinel (x = -1).
    # Cells with x > y stay -inf (unreachable) - what the Cython kernel's `x == y -> max_neg_val` rule emulates;
    # lower-band cells are computed but never read by the backtrack.
    acc = torch.full((b, t_y, t_x + 1), float("-inf"), device=device)
    acc[:, 0, 1] = v[:, 0, 0]
    for y in range(1, t_y):
        row = acc[:, y, 1:]
        torch.maximum(acc[:, y - 1, 1:], acc[:, y - 1, :-1], out=row)
        row.add_(v[:, y])

    # backtrack decisions for every cell: at frame y (>= 1) on token x, step to token x-1 iff
    # x != 0 and (x == y or acc[x, y-1] < acc[x-1, y-1])  (ties stay on the token, as upstream)
    xs = torch.arange(t_x, device=device)
    ys = torch.arange(1, t_y, device=device)
    move = (xs != 0)[None, None, :] & ((xs[None, None, :] == ys[None, :, None])
                                       | (acc[:, :-1, 1:] < acc[:, :-1, :-1]))  # [B, Ty-1, Tx]
    move_np = move.cpu().numpy()
    t_xs_np, t_ys_np = t_xs.cpu().numpy(), t_ys.cpu().numpy()
    index = np.maximum(t_xs_np - 1, 0)
    ar = np.arange(b)
    idx = np.zeros((b, t_y), dtype=np.int64)
    for y in range(t_y - 1, -1, -1):
        idx[:, y] = index
        if y > 0:
            index = index - (move_np[ar, y - 1, index] & (y < t_ys_np))
    idx_t = torch.from_numpy(idx).to(device)
    path = torch.nn.functional.one_hot(idx_t, t_x).transpose(1, 2).float()  # [B, Tx, Ty]
    path = path * mask_f
    return path.to(dtype)


def maximum_path(value: torch.Tensor, mask: torch.Tensor, impl: str = "auto") -> torch.Tensor:
    if impl == "auto":
        # GPU tensors: torch on device (no host copy). CPU tensors: numba (fastest measured on CPU) when importable,
        # else torch (~6x faster than the pure-numpy loop).
        if value.device.type != "cpu":
            impl = "torch"
        else:
            impl = "numpy" if _HAVE_NUMBA else "torch"
    if impl == "torch":
        return maximum_path_torch(value, mask)
    if impl == "numpy":
        return maximum_path_numpy(value, mask)
    if impl == "numpy_py":
        return maximum_path_numpy(value, mask, use_numba=False)
    raise ValueError(f"unknown MAS impl {impl!r}")


def _bench(b=32, t_x=200, t_y=900, device="cpu", reps=3) -> dict:
    """Times each available implementation; returns {impl: seconds_per_call}."""
    import time

    g = torch.Generator().manual_seed(0)
    value = torch.randn(b, t_x, t_y, generator=g).to(device) * 10 - 100
    tx = torch.randint(t_x // 2, t_x + 1, (b,), generator=g)
    ty = torch.clamp(tx * 4 + torch.randint(0, t_y, (b,), generator=g), max=t_y)
    tx[0], ty[0] = t_x, t_y
    mask = (torch.arange(t_x)[None, :, None] < tx[:, None, None]) & (torch.arange(t_y)[None, None, :] < ty[:, None, None])
    mask = mask.float().to(device)
    out = {}
    impls = ["torch", "numpy_py"] + (["numpy"] if _HAVE_NUMBA else [])
    for impl in impls:
        maximum_path(value, mask, impl)  # warmup / jit
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        for _ in range(reps):
            maximum_path(value, mask, impl)
        if device.startswith("cuda"):
            torch.cuda.synchronize()
        out["numba" if impl == "numpy" else impl] = (time.perf_counter() - t0) / reps
    return out


if __name__ == "__main__":
    import json
    import sys

    dev = sys.argv[1] if len(sys.argv) > 1 else "cpu"
    print(json.dumps({"device": dev, "B": 32, "Tx": 200, "Ty": 900, "numba": _HAVE_NUMBA,
                      "sec_per_call": _bench(device=dev)}, indent=1))
