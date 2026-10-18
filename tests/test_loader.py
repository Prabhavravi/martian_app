"""Tests for runtime loader."""

import tempfile
from pathlib import Path

from PIL import Image

from src.world.loader import WorldLoader


def test_loader_biome_api():
    with tempfile.TemporaryDirectory() as out_dir:
        textures_dir = Path(out_dir) / "textures"
        elevation_dir = Path(out_dir) / "elevation"
        textures_dir.mkdir()
        elevation_dir.mkdir()

        Image.new("RGB", (256, 256), color=(200, 100, 50)).save(textures_dir / "tile_0001.png")
        Image.new("L", (256, 256), color=150).save(elevation_dir / "tile_0001.png")
        Image.new("RGB", (256, 256), color=(80, 160, 90)).save(textures_dir / "tile_0002.png")
        Image.new("L", (256, 256), color=120).save(elevation_dir / "tile_0002.png")

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
                    "seed": 1,
                },
                {
                    "id": "tile_0002",
                    "biome": "mountain",
                    "texture": "textures/tile_0002.png",
                    "elevation": "elevation/tile_0002.png",
                    "width": 256,
                    "height": 256,
                    "seed": 2,
                },
            ],
        }
        with open(Path(out_dir) / "manifest.json", "w") as f:
            import json

            json.dump(manifest, f)

        loader = WorldLoader(out_dir)
        sand_tiles = loader.get_tiles_by_biome("sand_plain")
        mountain_tiles = loader.get_tiles_by_biome("mountain")

        assert len(sand_tiles) == 1
        assert sand_tiles[0]["id"] == "tile_0001"
        assert len(mountain_tiles) == 1
        assert mountain_tiles[0]["id"] == "tile_0002"

        tex = loader.load_texture(sand_tiles[0])
        elev = loader.load_elevation(sand_tiles[0])
        assert tex.mode == "RGB"
        assert elev.mode == "L"
        assert tex.size == elev.size
