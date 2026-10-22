# src/world/world_renderer.py
"""Render seamless world chunks for exploration."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .chunk_manager import ChunkManager


class WorldRenderer:
    """Renders a scrolling world from chunks with seamless edges."""

    def __init__(
        self,
        chunk_manager: ChunkManager,
        tile_size: int = 256,
        blend_px: int = 32,
    ) -> None:
        self.chunk_manager = chunk_manager
        self.tile_size = tile_size
        self.blend_px = blend_px

    def render_viewport(
        self,
        center_cx: int,
        center_cy: int,
        viewport_chunks: int = 3,
        output_path: str = "viewport.png",
    ) -> Image.Image:
        """Render a square viewport of chunks centered on (center_cx, center_cy).

        Args:
            center_cx: Center chunk X coordinate.
            center_cy: Center chunk Y coordinate.
            viewport_chunks: Number of chunks per side (odd number recommended).
            output_path: Where to save the result.
        """
        half = viewport_chunks // 2
        canvas_size = viewport_chunks * self.tile_size
        canvas = np.zeros((canvas_size, canvas_size, 3), dtype=np.float32)

        for dy in range(-half, half + 1):
            for dx in range(-half, half + 1):
                cx = center_cx + dx
                cy = center_cy + dy

                chunk = self.chunk_manager.get_chunk(cx, cy)
                texture = self.chunk_manager.get_chunk_texture(cx, cy)
                texture_arr = np.asarray(texture, dtype=np.float32)

                x0 = (dx + half) * self.tile_size
                y0 = (dy + half) * self.tile_size
                canvas[y0 : y0 + self.tile_size, x0 : x0 + self.tile_size] = texture_arr

        # Crossfade seams between adjacent chunks
        canvas = self._crossfade_seams(canvas, viewport_chunks)

        result = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
        result.save(output_path)
        return result

    def _crossfade_seams(self, canvas: np.ndarray, chunks: int) -> np.ndarray:
        """Crossfade vertical and horizontal seams between chunks.

        For each seam between two chunks, blend over ``blend_px`` pixels on each
        side of the seam line:
          - Left side of seam: fade from left tile content → right tile's edge pixel
          - Right side of seam: fade from left tile's edge pixel → right tile content
        """
        ts = self.tile_size
        bp = self.blend_px
        if bp <= 0:
            return canvas

        result = canvas.copy()
        h, w = canvas.shape[0], canvas.shape[1]

        # Vertical seams (between columns)
        for cx in range(1, chunks):
            x = cx * ts
            bw = min(bp, x, w - x)
            if bw <= 0:
                continue

            # Left tile's rightmost column (at x-1), right tile's leftmost column (at x)
            left_edge = result[:, x - 1 : x, :]      # (h, 1, 3)
            right_edge = result[:, x : x + 1, :]      # (h, 1, 3)

            # Left side: [x-bw, x) — fade from left tile content to right tile's edge
            left_cols = result[:, x - bw : x, :]     # (h, bw, 3)
            w_mask = np.linspace(0.0, 1.0, bw).reshape(1, bw, 1)
            w_mask = np.broadcast_to(w_mask, (h, bw, 3))
            left_blended = left_cols * (1.0 - w_mask) + right_edge * w_mask

            # Right side: [x, x+bw) — fade from left tile's edge to right tile content
            right_cols = result[:, x : x + bw, :]    # (h, bw, 3)
            right_blended = left_edge * (1.0 - w_mask) + right_cols * w_mask

            result[:, x - bw : x, :] = left_blended
            result[:, x : x + bw, :] = right_blended

        # Horizontal seams (between rows)
        for cy in range(1, chunks):
            y = cy * ts
            bw = min(bp, y, h - y)
            if bw <= 0:
                continue

            # Top tile's bottom row (at y-1), bottom tile's top row (at y)
            top_edge = result[y - 1 : y, :, :]        # (1, w, 3)
            bottom_edge = result[y : y + 1, :, :]      # (1, w, 3)

            # Top side: [y-bw, y) — fade from top tile content to bottom tile's edge
            top_rows = result[y - bw : y, :, :]       # (bw, w, 3)
            h_mask = np.linspace(0.0, 1.0, bw).reshape(bw, 1, 1)
            h_mask = np.broadcast_to(h_mask, (bw, w, 3))
            top_blended = top_rows * (1.0 - h_mask) + bottom_edge * h_mask

            # Bottom side: [y, y+bw) — fade from top tile's edge to bottom tile content
            bottom_rows = result[y : y + bw, :, :]    # (bw, w, 3)
            bottom_blended = top_edge * (1.0 - h_mask) + bottom_rows * h_mask

            result[y - bw : y, :, :] = top_blended
            result[y : y + bw, :, :] = bottom_blended

        return result


if __name__ == "__main__":
    cm = ChunkManager("outputs", "data/world_cache")
    wr = WorldRenderer(cm)

    # Render a 5x5 viewport centered at chunk (0, 0)
    wr.render_viewport(0, 0, viewport_chunks=5, output_path="viewport_00.png")

    # Render a viewport centered at chunk (3, -2) — player moved right and up
    wr.render_viewport(3, -2, viewport_chunks=5, output_path="viewport_3_-2.png")

    print("Viewports rendered.")
