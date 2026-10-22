from __future__ import annotations

from PIL import Image

import pygame


class TileCache:
    def __init__(self, assets_root) -> None:
        self.assets_root = assets_root
        self._surfaces = {}

    def get(self, layer, entry):
        key = (layer.name, entry.index)
        surface = self._surfaces.get(key)
        if surface is None:
            path = self.assets_root / entry.texture
            image = Image.open(path).convert("RGB")
            surface = pygame.image.fromstring(image.tobytes(), image.size, "RGB").convert()
            self._surfaces[key] = surface
        return surface

    def prune(self, keep) -> int:
        evicted = 0
        for key in list(self._surfaces.keys()):
            if key not in keep:
                del self._surfaces[key]
                evicted += 1
        return evicted

    def __len__(self) -> int:
        return len(self._surfaces)
