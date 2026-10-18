"""Tests for data preprocessing."""

import tempfile
from pathlib import Path

from PIL import Image

from src.data.preprocess import BIOMES, DEFAULT_RESOLUTION, build_processed_dataset


def test_preprocess_shapes_and_normalization():
    with tempfile.TemporaryDirectory() as raw_dir, tempfile.TemporaryDirectory() as out_dir:
        # Create one tile per biome
        for biome in BIOMES:
            biome_dir = Path(raw_dir) / biome
            biome_dir.mkdir()
            img = Image.new("RGB", (512, 512), color=(128, 128, 128))
            img.save(biome_dir / f"{biome}.png")

        result = build_processed_dataset(raw_dir, out_dir, resolution=DEFAULT_RESOLUTION, val_split=0.0)

        assert len(result["train"]) == len(BIOMES)
        assert len(result["val"]) == 0

        for tile in result["train"]:
            assert tile.width == DEFAULT_RESOLUTION
            assert tile.height == DEFAULT_RESOLUTION
            assert tile.biome in BIOMES
            assert Path(tile.path).exists()
