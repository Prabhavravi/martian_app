# src/world/panorama_world.py
"""Panoramic world: slice one cohesive image into non-overlapping chunks, pan left/right seamlessly.

Since all chunks come from the SAME panoramic image, placing them side by side
with NO blending produces perfectly seamless transitions — no seams, no black borders.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image


class PanoramaWorld:
    """Loads one panoramic image and provides non-overlapping chunks for left/right panning."""

    def __init__(
        self,
        image_path: str | Path,
        chunk_width: int = 512,
    ) -> None:
        self.image_path = Path(image_path)
        self.image = Image.open(self.image_path).convert("RGB")
        self.width, self.height = self.image.size
        self.chunk_width = chunk_width

        # Calculate how many non-overlapping chunks fit across the panorama
        self.num_chunks = max(1, self.width // self.chunk_width)
        self._chunk_cache: dict[int, Image.Image] = {}

        print(f"Loaded panorama: {self.width}x{self.height}")
        print(f"Chunk width: {chunk_width}")
        print(f"Total chunks across: {self.num_chunks} (perfectly seamless)")

    def get_chunk(self, cx: int) -> Image.Image:
        """Get a chunk at horizontal index cx. Wraps around for infinite scrolling."""
        if cx in self._chunk_cache:
            return self._chunk_cache[cx]

        # Wrap around for infinite scrolling
        wrapped_cx = cx % self.num_chunks

        # Calculate x position — non-overlapping, adjacent chunks
        x = wrapped_cx * self.chunk_width
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

        Chunks are placed side by side with NO blending — perfectly seamless
        because they're adjacent pixels from the same panoramic image.
        """
        half = num_chunks // 2
        canvas_w = num_chunks * self.chunk_width
        canvas = Image.new("RGB", (canvas_w, self.height))

        for i in range(-half, half + 1):
            cx = center_cx + i
            chunk = self.get_chunk(cx)
            x0 = (i + half) * self.chunk_width
            canvas.paste(chunk, (x0, 0))

        canvas.save(output_path)
        print(f"Saved viewport centered at chunk {center_cx}: {output_path}")
        return canvas


if __name__ == "__main__":
    # Example usage
    world = PanoramaWorld("martian_panorama.png", chunk_width=512)

    # Start at center chunk 0
    world.render_viewport(0, num_chunks=3, output_path="viewport_center.png")

    # User moves right
    cx = world.pan_right(0)
    world.render_viewport(cx, num_chunks=3, output_path="viewport_right.png")

    # User moves right again
    cx = world.pan_right(cx)
    world.render_viewport(cx, num_chunks=3, output_path="viewport_right2.png")

    # User moves left back
    cx = world.pan_left(cx)
    world.render_viewport(cx, num_chunks=3, output_path="viewport_back_center.png")

    print("Done. Viewports: viewport_center.png, viewport_right.png, viewport_right2.png, viewport_back_center.png")
