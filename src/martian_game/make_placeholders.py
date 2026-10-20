from __future__ import annotations

import json
from pathlib import Path

from .placeholders import generate_placeholders

OUT = Path("assets")
TILE_W = 512
TILE_H = 512
COUNT = 40
LAYERS = [
    {"name": "sky", "speed": 0.15},
    {"name": "far", "speed": 0.4},
    {"name": "mid", "speed": 0.7},
    {"name": "base", "speed": 1.0},
]


def build_manifest() -> dict:
    layers = []
    for i, layer in enumerate(LAYERS):
        tiles = []
        for j in range(COUNT):
            tiles.append(
                {
                    "id": f"{layer['name']}_{j:04d}",
                    "index": j,
                    "texture": f"tiles/{layer['name']}/{layer['name']}_{j:04d}.png",
                    "width": TILE_W,
                    "height": TILE_H,
                    "seed": 1000 + i * 100 + j,
                    "prompt": f"placeholder {layer['name']} tile {j}",
                    "settings": {"kind": "placeholder"},
                }
            )
        layers.append(
            {
                "name": layer["name"],
                "speed": layer["speed"],
                "tile_w": TILE_W,
                "tile_h": TILE_H,
                "tile_count": COUNT,
                "tiles": tiles,
            }
        )
    return {
        "version": 1,
        "tile_size": [TILE_W, TILE_H],
        "world_length_px": COUNT * TILE_W,
        "end_behavior": "LOOP",
        "viewport": {"w": 1280, "h": 720},
        "scroll_speed_px_per_sec": 300.0,
        "layers": layers,
    }


def main() -> None:
    generate_placeholders(OUT, TILE_W, TILE_H, COUNT, LAYERS)
    (OUT / "manifest.json").write_text(json.dumps(build_manifest(), indent=2))
    print("placeholders written to assets/")


if __name__ == "__main__":
    main()
