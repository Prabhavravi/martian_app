#!/usr/bin/env python3
"""Blend the horizontal edges of an 8-bit RGB PNG once, offline."""

from __future__ import annotations

import argparse
import struct
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
        raise ValueError("make_seamless.py supports only 8-bit RGB PNGs")
    raw = zlib.decompress(bytes(idat))
    bpp, stride = 3, width * 3
    pixels = bytearray(width * height * bpp)
    previous = bytearray(stride)
    offset = 0
    for y in range(height):
        filter_type = raw[offset]
        offset += 1
        scan = bytearray(raw[offset : offset + stride])
        offset += stride
        for x in range(stride):
            left = scan[x - bpp] if x >= bpp else 0
            up = previous[x]
            up_left = previous[x - bpp] if x >= bpp else 0
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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b""))


def make_seamless(source: Path, output: Path, blend_px: int = 96) -> None:
    width, height, pixels = read_rgb_png(source)
    blend = min(max(1, blend_px), width // 2)
    for offset in range(blend):
        amount = (offset + 1) / blend
        right_x, left_x = width - blend + offset, offset
        for y in range(height):
            right = (y * width + right_x) * 3
            left = (y * width + left_x) * 3
            for channel in range(3):
                pixels[right + channel] = int(pixels[right + channel] * (1 - amount) + pixels[left + channel] * amount)
    for y in range(height):
        right = (y * width + width - 1) * 3
        left = y * width * 3
        pixels[right : right + 3] = pixels[left : left + 3]
    write_rgb_png(output, width, height, pixels)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--blend-px", type=int, default=96)
    args = parser.parse_args()
    make_seamless(args.source, args.output, args.blend_px)
    print(f"wrote seamless panorama {args.output}")


if __name__ == "__main__":
    main()
