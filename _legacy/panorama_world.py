# src/world/panorama_world.py
"""Panoramic world: slice one cohesive image into chunks, pan left/right seamlessly."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image


class PanoramaWorld:
    """Loads one panoramic image and provides chunks for left/right panning."""

    def __init__(self, image_path: str | Path, chunk_width: int = 512, overlap: int = 64) -> None:
        self.image_path = Path(image_path)
        self.image = Image.open(self.image_path).convert("RGB")
        self.width, self.height = self.image.size
        self.chunk_width = chunk_width
        self.overlap = overlap

        # Calculate how many chunks fit across the panorama
        self.num_chunks = max(1, (self.width - overlap) // (chunk_width - overlap))
        self._chunk_cache: dict[int, Image.Image] = {}

        print(f"Loaded panorama: {self.width}x{self.height}")
        print(f"Chunk width: {chunk_width}, overlap: {overlap}")
        print(f"Total chunks across: {self.num_chunks}")

    def get_chunk(self, cx: int) -> Image.Image:
        """Get a chunk at horizontal index cx. Wraps around if out of bounds."""
        if cx in self._chunk_cache:
            return self._chunk_cache[cx]

        # Wrap around for infinite scrolling
        wrapped_cx = cx % self.num_chunks

        # Calculate x position in the panorama
        step = self.chunk_width - self.overlap
        x = wrapped_cx * step
        x = min(x, self.width - self.chunk_width)

        chunk = self.image.crop((x, 0, x + self.chunk_width, self.height))
        self._chunk_cache[wrapped_cx] = chunk
        return chunk

    def pan_left(self, current_cx: int) -> int:
        """Move camera left by one chunk. Returns new chunk index."""
        return current_cx - 1

    def pan_right(self, current_cx: int) -> int:
        """Move camera right by one chunk. Returns new chunk index."""
        return current_cx + 1

    def render_viewport(
        self,
        center_cx: int,
        num_chunks: int = 3,
        output_path: str = "viewport.png",
    ) -> Image.Image:
        """Render a viewport centered on chunk center_cx, showing num_chunks across.

        Adjacent chunks are crossfaded at their overlap regions for seamless transitions.
        """
        half = num_chunks // 2
        canvas_w = num_chunks * self.chunk_width
        canvas = np.zeros((self.height, canvas_w, 3), dtype=np.float32)

        for i in range(-half, half + 1):
            cx = center_cx + i
            chunk = self.get_chunk(cx)
            chunk_arr = np.asarray(chunk, dtype=np.float32)

            x0 = (i + half) * self.chunk_width
            canvas[:, x0 : x0 + self.chunk_width, :] = chunk_arr

        # Crossfade overlaps between adjacent chunks
        canvas = self._crossfade_overlaps(canvas, num_chunks)

        result = Image.fromarray(np.clip(canvas, 0, 255).astype(np.uint8))
        result.save(output_path)
        print(f"Saved viewport centered at chunk {center_cx}: {output_path}")
        return result

    def _crossfade_overlaps(self, canvas: np.ndarray, num_chunks: int) -> np.ndarray:
        """Crossfade the overlap regions between adjacent chunks."""
        result = canvas.copy()
        h, w = canvas.shape[0], canvas.shape[1]

        step = self.chunk_width - self.overlap
        ov = self.overlap

        for i in range(1, num_chunks):
            seam_x = i * step  # seam between chunk i-1 and chunk i
            lo = seam_x - ov // 2
            hi = seam_x + ov // 2
            blend_w = hi - lo

            if blend_w <= 0:
                continue

            # Left chunk's right edge, right chunk's left edge
            left_edge = canvas[:, seam_x - 1 : seam_x, :]      # (h, 1, 3)
            right_edge = canvas[:, seam_x : seam_x + 1, :]      # (h, 1, 3)

            # Left side of seam
            left_side = canvas[:, lo:seam_x, :]                 # (h, ov//2, 3)
            l_mask = np.linspace(0.0, 1.0, ov // 2).reshape(1, ov // 2, 1)
            l_mask = np.broadcast_to(l_mask, (h, ov // 2, 3))
            left_blended = left_side * (1.0 - l_mask) + right_edge * l_mask

            # Right side of seam
            right_side = canvas[:, seam_x : seam_x + ov // 2, :]  # (h, ov//2, 3)
            right_blended = left_edge * (1.0 - l_mask) + right_side * l_mask

            result[:, lo:seam_x, :] = left_blended
            result[:, seam_x : seam_x + ov // 2, :] = right_blended

        return result


if __name__ == "__main__":
    # Example usage
    world = PanoramaWorld("martian_panorama.png", chunk_width=512, overlap=64)

    # Initial view centered at chunk 0
    world.render_viewport(0, num_chunks=3, output_path="viewport_center.png")

    # User moves right
    cx = world.pan_right(0)
    world.render_viewport(cx, num_chunks=3, output_path="viewport_right.png")

    # User moves right again
    cx = world.pan_right(cx)
    world.render_viewport(cx, num_chunks=3, output_path="viewport_right2.png")

    # User moves left (back toward center)
    cx = world.pan_left(cx)
    world.render_viewport(cx, num_chunks=3, output_path="viewport_back_center.png")

    print("Done. Viewports: viewport_center.png, viewport_right.png, viewport_right2.png, viewport_back_center.png")
