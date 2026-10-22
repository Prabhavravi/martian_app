#!/usr/bin/env python3
"""Create static JPEG panorama variants from one real RGB PNG, offline."""

from __future__ import annotations

import argparse
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def paeth(a: int, b: int, c: int) -> int:
    estimate = a + b - c
    pa, pb, pc = abs(estimate - a), abs(estimate - b), abs(estimate - c)
    return a if pa <= pb and pa <= pc else (b if pb <= pc else c)


def read_rgb_png(path: Path) -> tuple[int, int, bytearray]:
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"not a PNG: {path}")
    pos = len(PNG_SIGNATURE)
    idat = bytearray()
    width = height = bit_depth = color_type = None
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        kind = data[pos + 4 : pos + 8]
        payload = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", payload)
        elif kind == b"IDAT":
            idat.extend(payload)
        elif kind == b"IEND":
            break
    if (bit_depth, color_type) != (8, 2):
        raise ValueError("make_variants.py supports only 8-bit RGB PNGs")
    raw = zlib.decompress(bytes(idat))
    stride = width * 3
    pixels = bytearray(width * height * 3)
    previous = bytearray(stride)
    offset = 0
    for y in range(height):
        filter_type = raw[offset]
        offset += 1
        scan = bytearray(raw[offset : offset + stride])
        offset += stride
        for x in range(stride):
            left = scan[x - 3] if x >= 3 else 0
            up = previous[x]
            up_left = previous[x - 3] if x >= 3 else 0
            if filter_type == 1:
                scan[x] = (scan[x] + left) & 255
            elif filter_type == 2:
                scan[x] = (scan[x] + up) & 255
            elif filter_type == 3:
                scan[x] = (scan[x] + ((left + up) // 2)) & 255
            elif filter_type == 4:
                scan[x] = (scan[x] + paeth(left, up, up_left)) & 255
            elif filter_type != 0:
                raise ValueError(f"unsupported PNG filter {filter_type}")
        pixels[y * stride : (y + 1) * stride] = scan
        previous = scan
    return width, height, pixels


def write_rgb_png(path: Path, width: int, height: int, pixels: bytearray) -> None:
    stride = width * 3
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw.extend(pixels[y * stride : (y + 1) * stride])
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    path.write_bytes(PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def make_variant(source_pixels: bytearray, width: int, height: int, index: int) -> bytearray:
    pixels = bytearray(len(source_pixels))
    roll = (width * (index + 1) // 17) % width
    mirror = index % 2 == 1
    brightness = 0.94 + (index % 5) * 0.03
    for y in range(height):
        for x in range(width):
            source_x = (x + roll) % width
            if mirror:
                source_x = width - 1 - source_x
            source = (y * width + source_x) * 3
            target = (y * width + x) * 3
            pixels[target] = min(255, int(source_pixels[source] * brightness))
            pixels[target + 1] = min(255, int(source_pixels[source + 1] * brightness))
            pixels[target + 2] = min(255, int(source_pixels[source + 2] * brightness))
    return pixels


def make_variants(source: Path, output: Path, width_nodes: int, height_nodes: int, start_x: int, start_y: int) -> None:
    if shutil.which("sips") is None:
        raise RuntimeError("make_variants.py requires macOS sips to encode JPEGs; no Python dependency is needed")
    width, height, source_pixels = read_rgb_png(source)
    output.mkdir(parents=True, exist_ok=True)
    made = 0
    with tempfile.TemporaryDirectory(prefix="martian-variants-") as temp_dir:
        temp = Path(temp_dir)
        for y in range(height_nodes):
            for x in range(width_nodes):
                if (x, y) == (start_x, start_y):
                    continue
                png_path = temp / f"node_{x}_{y}.png"
                jpg_path = output / f"node_{x}_{y}.jpg"
                write_rgb_png(png_path, width, height, make_variant(source_pixels, width, height, y * width_nodes + x))
                subprocess.run(
                    ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", str(png_path), "--out", str(jpg_path)],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
                made += 1
    print(f"created {made} static derived panoramas in {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("assets/panoramas/martian_panorama_seamless.png"))
    parser.add_argument("--output", type=Path, default=Path("assets/panoramas"))
    parser.add_argument("--width", type=int, default=4)
    parser.add_argument("--height", type=int, default=4)
    parser.add_argument("--start-x", type=int, default=1)
    parser.add_argument("--start-y", type=int, default=3)
    args = parser.parse_args()
    make_variants(args.source, args.output, args.width, args.height, args.start_x, args.start_y)


if __name__ == "__main__":
    main()
