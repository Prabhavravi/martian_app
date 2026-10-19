# src/world/chunk_manager.py
"""Deterministic chunk-based world generation for Martian terrain."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image

from .loader import WorldLoader


def coord_to_seed(x: int, y: int, salt: str = "martian_world") -> int:
    """Deterministic seed from world coordinates."""
    key = f"{salt}:{x}:{y}"
    return int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % (2**31)


def noise_biome(x: int, y: int, scale: float = 0.05) -> str:
    """Assign a biome to chunk coordinates using deterministic weighted random."""
    rng = random.Random(coord_to_seed(x, y, salt="biome"))
    biomes = ["mountain", "sand_plain", "dune", "crater", "rocky_outcrop"]
    weights = [0.25, 0.35, 0.15, 0.15, 0.10]
    return rng.choices(biomes, weights=weights, k=1)[0]


class ChunkManager:
    """Manages on-demand chunk generation with deterministic seeds."""

    def __init__(
        self,
        outputs_dir: str = "outputs",
        cache_dir: str = "data/world_cache",
        tile_size: int = 256,
        blend_px: int = 32,
    ) -> None:
        self.outputs_dir = Path(outputs_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.tile_size = tile_size
        self.blend_px = blend_px
        self.loader = WorldLoader(outputs_dir)
        self._memory_cache: dict[tuple[int, int], dict] = {}

    def _cache_path(self, cx: int, cy: int) -> Path:
        return self.cache_dir / f"chunk_{cx:04d}_{cy:04d}.json"

    def _chunk_filename(self, cx: int, cy: int) -> str:
        return f"chunk_{cx:04d}_{cy:04d}.png"

    def get_chunk(self, cx: int, cy: int) -> dict:
        """Get or generate a chunk at world coordinates (cx, cy)."""
        cache_key = (cx, cy)

        # Memory cache
        if cache_key in self._memory_cache:
            return self._memory_cache[cache_key]

        # Disk cache
        cache_file = self._cache_path(cx, cy)
        if cache_file.exists():
            with open(cache_file) as f:
                data = json.load(f)
            data["texture_path"] = Path(data["texture_path"])
            data["elevation_path"] = Path(data["elevation_path"])
            self._memory_cache[cache_key] = data
            return data

        # Generate new chunk
        data = self._generate_chunk(cx, cy)

        # Save to disk
        with open(cache_file, "w") as f:
            json.dump(
                {
                    "cx": data["cx"],
                    "cy": data["cy"],
                    "biome": data["biome"],
                    "seed": data["seed"],
                    "texture_path": str(data["texture_path"]),
                    "elevation_path": str(data["elevation_path"]),
                },
                f,
            )

        self._memory_cache[cache_key] = data
        return data

    def _generate_chunk(self, cx: int, cy: int) -> dict:
        """Generate a chunk using deterministic seed from coordinates."""
        seed = coord_to_seed(cx, cy)
        biome = noise_biome(cx, cy)

        rng = random.Random(seed)

        # Pick a random tile from the biome's pre-generated pool
        tiles = self.loader.get_tiles_by_biome(biome)
        if not tiles:
            tiles = self.loader.get_tiles_by_biome("sand_plain")

        tile = rng.choice(tiles)
        texture = self.loader.load_texture(tile)
        elevation = self.loader.load_elevation(tile)

        # Save chunk to cache directory
        tex_name = self._chunk_filename(cx, cy)
        tex_path = self.cache_dir / tex_name
        elev_path = self.cache_dir / tex_name.replace(".png", "_elev.png")

        texture.save(tex_path)
        elevation.save(elev_path)

        return {
            "cx": cx,
            "cy": cy,
            "biome": biome,
            "seed": seed,
            "texture_path": tex_path,
            "elevation_path": elev_path,
        }

    def get_chunk_texture(self, cx: int, cy: int) -> Image.Image:
        """Load chunk texture image."""
        data = self.get_chunk(cx, cy)
        return Image.open(data["texture_path"]).convert("RGB")

    def get_chunk_elevation(self, cx: int, cy: int) -> Image.Image:
        """Load chunk elevation image."""
        data = self.get_chunk(cx, cy)
        return Image.open(data["elevation_path"]).convert("L")
