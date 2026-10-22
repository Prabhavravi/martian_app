#!/usr/bin/env python3
"""Create small, deterministic 2048x512 Martian panorama placeholders.

This uses only the Python standard library so it can run offline on a clean
machine. Real files already present in the output directory are preserved.
"""

from __future__ import annotations

import argparse
import math
import random
import struct
import zlib
from pathlib import Path


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def write_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    raw = bytearray()
    stride = width * 3
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride : (y + 1) * stride])
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b""))


FONT = {
    "0": ("111", "101", "101", "101", "111"),
    "1": ("010", "110", "010", "010", "111"),
    "2": ("110", "001", "010", "100", "111"),
    "3": ("110", "001", "010", "001", "110"),
    "4": ("101", "101", "111", "001", "001"),
    "5": ("111", "100", "110", "001", "110"),
    "6": ("011", "100", "111", "101", "111"),
    "7": ("111", "001", "010", "010", "010"),
    "8": ("111", "101", "111", "101", "111"),
    "9": ("111", "101", "111", "001", "110"),
    "_": ("000", "000", "000", "000", "111"),
    "x": ("000", "101", "010", "101", "000"),
}


def draw_label(pixels: bytearray, width: int, height: int, text: str) -> None:
    scale = 7
    start_x = width // 2 - (len(text) * 4 * scale) // 2
    start_y = height // 2 - 3 * scale
    for i, char in enumerate(text):
        glyph = FONT.get(char, FONT["_"])
        x0 = start_x + i * 4 * scale
        for gy, row in enumerate(glyph):
            for gx, bit in enumerate(row):
                if bit == "1":
                    for oy in range(scale):
                        for ox in range(scale):
                            x, y = x0 + gx * scale + ox, start_y + gy * scale + oy
                            if 0 <= x < width and 0 <= y < height:
                                p = (y * width + x) * 3
                                pixels[p : p + 3] = bytes((248, 214, 155))


def make_placeholder(path: Path, x: int, y: int, width: int, height: int) -> None:
    rng = random.Random(20261022 + x * 101 + y * 1009)
    pixels = bytearray(width * height * 3)
    phase = rng.random() * math.tau
    dune_phase = rng.random() * math.tau
    for py in range(height):
        horizon = height * 0.53
        for px in range(width):
            t = py / height
            if py < horizon:
                glow = py / horizon
                r = int(67 + 92 * (1 - glow) + 30 * glow)
                g = int(24 + 34 * (1 - glow) + 16 * glow)
                b = int(28 + 20 * (1 - glow) + 9 * glow)
                if rng.random() < 0.002:
                    r, g, b = 214, 119, 76
            else:
                grain = rng.randint(-7, 7)
                wave = math.sin(px / 120 + dune_phase) * 12 + math.sin(px / 310 + phase) * 9
                depth = (py - horizon) / (height - horizon)
                r = int(133 + 44 * depth + wave * 0.35 + grain)
                g = int(55 + 22 * depth + wave * 0.15 + grain * 0.45)
                b = int(31 + 12 * depth + grain * 0.25)
            p = (py * width + px) * 3
            pixels[p : p + 3] = bytes((max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))))

    # Low, dark rocks and a few distant mesas make the fallback read as terrain.
    for _ in range(20):
        cx = rng.randrange(width)
        base = int(height * (0.60 + rng.random() * 0.32))
        radius = rng.randrange(8, 34)
        for py in range(max(0, base - radius), min(height, base + 8)):
            half = int(math.sqrt(max(0, radius * radius - (py - (base - radius // 2)) ** 2)))
            for px in range(max(0, cx - half), min(width, cx + half + 1)):
                p = (py * width + px) * 3
                shade = rng.randrange(0, 18)
                pixels[p : p + 3] = bytes((66 + shade, 30 + shade // 2, 22))
    draw_label(pixels, width, height, f"{x}x{y}")
    # Blend the right edge toward the left edge once, offline. Runtime panning
    # can then wrap by copying pixels without a seam or a special case.
    blend = min(96, width // 4)
    for offset in range(blend):
        amount = (offset + 1) / blend
        right_x = width - blend + offset
        left_x = offset
        for py in range(height):
            right = (py * width + right_x) * 3
            left = (py * width + left_x) * 3
            for channel in range(3):
                pixels[right + channel] = int(pixels[right + channel] * (1 - amount) + pixels[left + channel] * amount)
    for py in range(height):
        right = (py * width + width - 1) * 3
        left = py * width * 3
        pixels[right : right + 3] = pixels[left : left + 3]
    write_png(path, width, height, pixels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="assets/panoramas")
    parser.add_argument("--width", type=int, default=2048)
    parser.add_argument("--height", type=int, default=512)
    parser.add_argument("--grid", type=int, nargs=2, default=(4, 4), metavar=("WIDTH", "HEIGHT"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    created = 0
    for y in range(args.grid[1]):
        for x in range(args.grid[0]):
            path = output / f"node_{x}_{y}.png"
            if args.overwrite or not path.exists():
                make_placeholder(path, x, y, args.width, args.height)
                created += 1
    print(f"created {created} placeholder panoramas in {output}")


if __name__ == "__main__":
    main()
