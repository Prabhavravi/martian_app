# src/generate/seamless.py
"""Seamless tiling post-processing for terrain textures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


def _ensure_3d(arr: np.ndarray) -> tuple[np.ndarray, bool]:
    """Promote a 2D grayscale array to 3D, returning (array, was_2d)."""
    if arr.ndim == 2:
        return arr[:, :, np.newaxis], True
    return arr, False


def _restore_ndim(arr: np.ndarray, was_2d: bool, mode: str) -> np.ndarray:
    """Restore a 3D array to 2D if originally grayscale."""
    if was_2d:
        return arr[:, :, 0]
    return arr


def make_seamless(image: Image.Image, blend_pct: float = 0.15) -> Image.Image:
    """Make a texture tile seamless by blending opposite edges.

    Technique:
      1. Roll the image by half its width/height so outer edges meet at the center
      2. Blend the central seams (vertical and horizontal) with a feathered gradient
      3. Roll back — the blended seams are now at the outer edges, making them match

    Args:
        image: Input PIL Image (RGB or L mode).
        blend_pct: Fraction of width/height to blend at seams (0.0 to 0.5).

    Returns:
        Seamless PIL Image of same size and mode.
    """
    arr = np.asarray(image, dtype=np.float32)
    arr_3d, was_2d = _ensure_3d(arr)
    h, w = arr_3d.shape[:2]

    # Step 1: Roll so outer edges meet at center
    rolled = np.roll(arr_3d, (h // 2, w // 2), axis=(0, 1))

    # Step 2: Blend center seams
    blended = _blend_center_seams(rolled, w // 2, h // 2, blend_pct)

    # Step 3: Roll back
    result = np.roll(blended, (-h // 2, -w // 2), axis=(0, 1))

    result = _restore_ndim(result, was_2d, image.mode)
    result = np.clip(result, 0, 255).astype(np.uint8)
    return Image.fromarray(result, mode=image.mode)


def _blend_center_seams(
    arr: np.ndarray, cx: int, cy: int, blend_pct: float
) -> np.ndarray:
    """Feather-blend vertical and horizontal seams at the center of the array.

    Blends pixels adjacent to the seam toward the seam value itself, so that
    after rolling back, the outer edges match.
    """
    h, w = arr.shape[:2]
    blend_w = max(1, int(w * blend_pct))
    blend_h = max(1, int(h * blend_pct))

    result = arr.copy()
    n_channels = arr.shape[2]

    # Vertical seam at column cx: blend left-edge pixels toward rolled[cx, :]
    seam_col = result[:, cx : cx + 1, :]  # (h, 1, c) — the seam value
    x_mask = np.linspace(0.0, 1.0, blend_w).reshape(1, blend_w, 1)
    x_mask = np.broadcast_to(x_mask, (h, blend_w, n_channels))
    result[:, cx - blend_w : cx, :] = (
        result[:, cx - blend_w : cx, :] * (1.0 - x_mask) + seam_col * x_mask
    )

    # Horizontal seam at row cy: blend top-edge pixels toward rolled[cy, :]
    seam_row = result[cy : cy + 1, :, :]  # (1, w, c) — the seam value
    y_mask = np.linspace(0.0, 1.0, blend_h).reshape(blend_h, 1, 1)
    y_mask = np.broadcast_to(y_mask, (blend_h, w, n_channels))
    result[cy - blend_h : cy, :, :] = (
        result[cy - blend_h : cy, :, :] * (1.0 - y_mask) + seam_row * y_mask
    )

    return result


def pregenerate_seamless(
    input_dir: str | Path,
    output_dir: str | Path,
    blend_pct: float = 0.15,
    overwrite: bool = False,
) -> int:
    """Convert all PNGs in input_dir to seamless versions in output_dir.

    Preserves directory structure (biome subfolders are kept).
    """
    input_root = Path(input_dir)
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    count = 0
    for png_path in sorted(input_root.rglob("*.png")):
        rel = png_path.relative_to(input_root)
        out_path = output_root / rel
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if out_path.exists() and not overwrite:
            count += 1
            continue

        img = Image.open(png_path)
        seamless = make_seamless(img, blend_pct=blend_pct)
        seamless.save(out_path)
        count += 1

    return count
