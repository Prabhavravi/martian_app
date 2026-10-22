from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def make_horiz_seamless(img: Image.Image, blend_px: int = 64) -> Image.Image:
    """Blend the right edge of ``img`` to match its left edge so it tiles horizontally."""
    arr = np.asarray(img.convert("RGB"), dtype=np.float64)
    h, w, _ = arr.shape
    b = max(1, min(blend_px, w // 2))
    left_edge = arr[:, 0:1, :]                      # (h,1,3)
    mask = np.linspace(0.0, 1.0, b).reshape(1, b, 1)
    mask = np.broadcast_to(mask, (h, b, 3))
    arr[:, w - b : w, :] = (
        arr[:, w - b : w, :] * (1.0 - mask) + left_edge * mask
    )
    arr[:, w - 1 : w, :] = left_edge                # force exact match at the seam
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGB")


def band_stretch(img: Image.Image, top_frac: float, bot_frac: float, out_h: int) -> Image.Image:
    """Crop a horizontal band and stretch it vertically to ``out_h``."""
    w, h = img.size
    y0 = int(top_frac * h)
    y1 = max(y0 + 1, int(bot_frac * h))
    band = img.crop((0, y0, w, y1))
    return band.resize((w, out_h), Image.LANCZOS)


def repeat_horiz(img: Image.Image, count: int) -> Image.Image:
    """Tile ``img`` horizontally ``count`` times (assumes horizontally seamless)."""
    w, h = img.size
    canvas = Image.new("RGB", (w * count, h))
    for i in range(count):
        canvas.paste(img, (i * w, 0))
    return canvas


def slice_tiles(strip: Image.Image, tile_w: int) -> list[Image.Image]:
    """Cut a horizontally seamless strip into equal ``tile_w``-wide tiles."""
    w, h = strip.size
    assert w % tile_w == 0, f"strip width {w} not divisible by tile_w {tile_w}"
    return [strip.crop((i * tile_w, 0, (i + 1) * tile_w, h)) for i in range(w // tile_w)]
