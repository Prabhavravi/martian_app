"""Runtime loader for pre-generated Martian landscape tiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image

MANIFEST_FILENAME = "manifest.json"


class WorldLoader:
    """Loads the pre-generated manifest and resolves texture/elevation paths."""

    def __init__(self, outputs_dir: str | Path) -> None:
        self.outputs_dir = Path(outputs_dir)
        manifest_path = self.outputs_dir / MANIFEST_FILENAME
        if not manifest_path.exists():
            raise FileNotFoundError(f"manifest.json not found at {manifest_path}")
        with open(manifest_path) as f:
            self.manifest = json.load(f)

        self.tiles: List[dict] = self.manifest.get("tiles", [])
        self._by_id: Dict[str, dict] = {t["id"]: t for t in self.tiles}
        self._by_biome: Dict[str, List[dict]] = {}
        for t in self.tiles:
            self._by_biome.setdefault(t["biome"], []).append(t)

    @property
    def version(self) -> int:
        return self.manifest.get("version", 0)

    @property
    def biome_list(self) -> List[str]:
        return list(self._by_biome.keys())

    def tile_count(self) -> int:
        return len(self.tiles)

    def get_tile(self, tile_id: str) -> Optional[dict]:
        return self._by_id.get(tile_id)

    def get_tiles_by_biome(self, biome: str) -> List[dict]:
        return self._by_biome.get(biome, [])

    def resolve(self, tile: dict) -> dict:
        """Resolve relative texture/elevation paths to absolute Paths."""
        return {
            "id": tile["id"],
            "biome": tile["biome"],
            "texture_path": self.outputs_dir / tile["texture"],
            "elevation_path": self.outputs_dir / tile["elevation"],
            "width": tile["width"],
            "height": tile["height"],
            "seed": tile.get("seed"),
        }

    def load_texture(self, tile: dict) -> Image.Image:
        resolved = self.resolve(tile)
        return Image.open(resolved["texture_path"]).convert("RGB")

    def load_elevation(self, tile: dict) -> Image.Image:
        resolved = self.resolve(tile)
        return Image.open(resolved["elevation_path"]).convert("L")


class WorldRenderer:
    """Engine-agnostic stub interface for blitting tiles + elevation into a world grid.

    Implementations should subclass and override `place_tile` to integrate with a
    specific game engine / rendering backend.
    """

    def __init__(self, loader: WorldLoader) -> None:
        self.loader = loader

    def place_tile(self, tile: dict, x: int, y: int) -> None:
        """Place a terrain tile at grid coordinate (x, y). Override in subclass."""
        raise NotImplementedError

    def render_random_biome(self, biome: str, x: int, y: int) -> None:
        """Pick a random tile from the given biome and place it at (x, y)."""
        tiles = self.loader.get_tiles_by_biome(biome)
        if not tiles:
            raise ValueError(f"No tiles available for biome: {biome}")
        import random

        tile = random.choice(tiles)
        self.place_tile(tile, x, y)
