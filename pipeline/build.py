from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

from .generate_layer import band_stretch, make_horiz_seamless, repeat_horiz, slice_tiles
from .contact_sheet import contact_sheet

SOURCE = Path("martian_panorama.png")
LAYERS = [
    {
        "name": "sky",
        "speed": 0.15,
        "top_frac": 0.00,
        "bot_frac": 0.40,
        "prompt": "Martian sky band from pre-rendered panorama",
        "settings": {"kind": "band", "source": "martian_panorama.png"},
    },
    {
        "name": "far",
        "speed": 0.40,
        "top_frac": 0.25,
        "bot_frac": 0.60,
        "prompt": "Distant Martian terrain band from pre-rendered panorama",
        "settings": {"kind": "band", "source": "martian_panorama.png"},
    },
    {
        "name": "mid",
        "speed": 0.70,
        "top_frac": 0.45,
        "bot_frac": 0.80,
        "prompt": "Mid-distance Martian terrain band from pre-rendered panorama",
        "settings": {"kind": "band", "source": "martian_panorama.png"},
    },
    {
        "name": "base",
        "speed": 1.00,
        "top_frac": 0.00,
        "bot_frac": 1.00,
        "prompt": "Full Martian landscape band from pre-rendered panorama",
        "settings": {"kind": "band", "source": "martian_panorama.png"},
    },
]


def build(
    out_dir: str = "assets/real",
    tile_w: int = 2048,
    tile_h: int = 720,
    count: int = 8,
    viewport_w: int = 1280,
    viewport_h: int = 720,
    scroll_speed_px_per_sec: float = 300.0,
    end_behavior: str = "LOOP",
    seed: int = 20261020,
) -> Path:
    out = Path(out_dir)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    base = Image.open(SOURCE).convert("RGB")
    base = make_horiz_seamless(base, blend_px=64)
    base = base.resize((tile_w, tile_h), Image.LANCZOS)  # offline upscale to fill viewport

    manifest_layers = []
    for i, layer in enumerate(LAYERS):
        layer_img = band_stretch(base, layer["top_frac"], layer["bot_frac"], tile_h)
        strip = repeat_horiz(layer_img, count)
        tiles = slice_tiles(strip, tile_w)
        layer_dir = out / "tiles" / layer["name"]
        layer_dir.mkdir(parents=True, exist_ok=True)
        entries = []
        for j, tile in enumerate(tiles):
            fname = f"{layer['name']}_{j:04d}.png"
            tile.save(layer_dir / fname)
            entries.append(
                {
                    "id": f"{layer['name']}_{j:04d}",
                    "index": j,
                    "texture": f"tiles/{layer['name']}/{fname}",
                    "width": tile_w,
                    "height": tile_h,
                    "seed": int(seed + i * 100003 + j),
                    "prompt": layer["prompt"],
                    "settings": layer["settings"],
                }
            )
        manifest_layers.append(
            {
                "name": layer["name"],
                "speed": layer["speed"],
                "tile_w": tile_w,
                "tile_h": tile_h,
                "tile_count": count,
                "tiles": entries,
            }
        )
        contact_sheet(out, layer, tile_w, tile_h, count)

    manifest = {
        "version": 1,
        "tile_size": [tile_w, tile_h],
        "world_length_px": count * tile_w,
        "end_behavior": end_behavior,
        "viewport": {"w": viewport_w, "h": viewport_h},
        "scroll_speed_px_per_sec": scroll_speed_px_per_sec,
        "layers": manifest_layers,
    }
    manifest_path = out / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"wrote {manifest_path}")
    print(f"tiles: {count} per layer x {len(LAYERS)} layers = {count * len(LAYERS)} tiles")
    print(f"world length: {count * tile_w} px, tile size: {tile_w}x{tile_h}")
    return manifest_path


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="assets/real")
    parser.add_argument("--tile-w", type=int, default=2048)
    parser.add_argument("--tile-h", type=int, default=720)
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20261020)
    args = parser.parse_args()
    build(
        out_dir=args.out,
        tile_w=args.tile_w,
        tile_h=args.tile_h,
        count=args.count,
        seed=args.seed,
    )
