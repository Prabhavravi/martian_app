from __future__ import annotations

from PIL import Image, ImageDraw, ImageFont

import pygame

from .world import visible_tiles


class Renderer:
    def __init__(self, screen, manifest, assets_root, cache) -> None:
        self.screen = screen
        self.manifest = manifest
        self.cache = cache
        self.font = ImageFont.load_default()
        self.debug = False
        self.fps = 0.0

    def render(self, effective) -> int:
        vp_w, vp_h = self.screen.get_size()
        self.screen.fill((20, 24, 30))
        needed = set()
        drawn = 0
        for layer in self.manifest.layers:
            by_index = {entry.index: entry for entry in layer.tiles}
            for screen_x, tex in visible_tiles(
                effective,
                layer.speed,
                layer.tile_w,
                vp_w,
                layer.tile_w,
                layer.tile_count,
                self.manifest.end_behavior,
            ):
                entry = by_index[tex]
                surface = self.cache.get(layer, entry)
                y = (vp_h - entry.height) // 2
                self.screen.blit(surface, (screen_x, y))
                needed.add((layer.name, entry.index))
                drawn += 1
        self.cache.prune(needed)
        if self.debug:
            self._draw_debug(effective, drawn)
        return drawn

    def _text_surface(self, text, size=20):
        img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        img = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((2 - bbox[0], 2 - bbox[1]), text, font=font, fill=(255, 255, 255, 255))
        return pygame.image.fromstring(img.tobytes(), img.size, "RGBA").convert_alpha()

    def _draw_debug(self, effective, drawn) -> None:
        lines = [
            f"{self.manifest.end_behavior[:3]} eff={effective:9.1f}",
            f"tiles={drawn} cached={len(self.cache)}",
            f"fps={self.fps:5.1f}",
        ]
        surf = self._text_surface("  |  ".join(lines), size=18)
        self.screen.blit(surf, (10, 10))
