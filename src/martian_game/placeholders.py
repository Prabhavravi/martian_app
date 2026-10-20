from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _gradient_color(base, x, w):
    return tuple(min(255, int(c + (255 - c) * x / w)) for c in base)


def generate_placeholders(out_dir, tile_w, tile_h, count, layers):
    out_dir = Path(out_dir)
    font = ImageFont.load_default()
    for layer in layers:
        layer_dir = out_dir / "tiles" / layer["name"]
        layer_dir.mkdir(parents=True, exist_ok=True)
        for i in range(count):
            base = (
                (i * 37) % 200 + 20,
                (i * 101) % 180 + 40,
                (i * 173) % 160 + 60,
            )
            img = Image.new("RGB", (tile_w, tile_h))
            draw = ImageDraw.Draw(img)
            for x in range(tile_w):
                color = _gradient_color(base, x, tile_w)
                draw.line([(x, 0), (x, tile_h - 1)], fill=color)
            label = f"{layer['name'][:3].upper()}{i:03d}"
            bbox = draw.textbbox((0, 0), label, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            draw.text(
                ((tile_w - tw) / 2 - bbox[0], (tile_h - th) / 2 - bbox[1]),
                label,
                font=font,
                fill=(255, 255, 255),
            )
            img.save(layer_dir / f"{layer['name']}_{i:04d}.png")
