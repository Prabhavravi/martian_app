"""Tests for manifest schema and file existence."""

import json
import tempfile
from pathlib import Path

from src.world.loader import WorldLoader


def test_manifest_schema_and_files_exist():
    with tempfile.TemporaryDirectory() as out_dir:
        textures_dir = Path(out_dir) / "textures"
        elevation_dir = Path(out_dir) / "elevation"
        textures_dir.mkdir()
        elevation_dir.mkdir()

        # Create dummy texture + elevation files
        from PIL import Image

        Image.new("RGB", (256, 256), color=(200, 100, 50)).save(textures_dir / "tile_0001.png")
        Image.new("L", (256, 256), color=150).save(elevation_dir / "tile_0001.png")

        manifest = {
            "version": 1,
            "tiles": [
                {
                    "id": "tile_0001",
                    "biome": "sand_plain",
                    "texture": "textures/tile_0001.png",
                    "elevation": "elevation/tile_0001.png",
                    "width": 256,
                    "height": 256,
                    "seed": 42,
                }
            ],
        }
        with open(Path(out_dir) / "manifest.json", "w") as f:
            json.dump(manifest, f)

        loader = WorldLoader(out_dir)
        assert loader.version == 1
        assert loader.tile_count() == 1
        assert "sand_plain" in loader.biome_list

        tile = loader.get_tile("tile_0001")
        assert tile is not None
        resolved = loader.resolve(tile)
        assert resolved["texture_path"].exists()
        assert resolved["elevation_path"].exists()
