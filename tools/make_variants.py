#!/usr/bin/env python3
"""Build deterministic, static Martian panorama scenes offline."""

from __future__ import annotations

import argparse
import json
import random
import shutil
import struct
import subprocess
import tempfile
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PRESETS = {
    "dusty_afternoon": ((1.02, 0.96, 0.86), (2, 2, 1), 0.06),
    "rust_dusk": ((1.10, 0.82, 0.68), (5, 0, -2), 0.02),
    "pale_haze": ((1.00, 1.01, 0.96), (10, 10, 8), 0.20),
    "dark_basalt": ((0.78, 0.80, 0.82), (-3, -2, -1), 0.01),
    "butte_orange": ((1.12, 0.88, 0.66), (7, 1, -3), 0.03),
}


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


def as_png(path: Path, temporary: Path) -> Path:
    if path.suffix.lower() == ".png":
        return path
    if shutil.which("sips") is None:
        raise RuntimeError("JPEG source conversion requires macOS sips or install Pillow for offline generation")
    png_path = temporary / (path.stem + ".png")
    subprocess.run(["sips", "-s", "format", "png", str(path), "--out", str(png_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return png_path


def source_id(path: Path) -> str:
    return path.stem


def discover_sources(root: Path) -> list[Path]:
    candidates = []
    for candidate in (root / "assets/panoramas/martian_panorama.png", root / "assets/panoramas/martian_panorama_seamless.png"):
        if candidate.exists():
            candidates.append(candidate)
    real_dir = root / "assets/panoramas/real"
    if real_dir.exists():
        candidates.extend(sorted(p for p in real_dir.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"}))
    return candidates


def sample(source: tuple[int, int, bytearray], x: float, y: float) -> tuple[int, int, int]:
    width, height, pixels = source
    sx = int(x) % width
    sy = max(0, min(height - 1, int(y)))
    offset = (sy * width + sx) * 3
    return pixels[offset], pixels[offset + 1], pixels[offset + 2]


def sample_part(source: tuple[int, int, bytearray], local_x: int, segment_width: int, y: int, part: dict) -> tuple[int, int, int]:
    width, _, _ = source
    crop_width = width * part["zoom"]
    normalized = (local_x + 0.5) / segment_width
    normalized = 1.0 - normalized if part["mirror"] else normalized
    source_x = part["roll"] + (normalized - 0.5) * crop_width
    return sample(source, source_x, y + part["vertical_shift"])


def grade(rgb: tuple[int, int, int], preset: str, x: int, y: int, width: int, height: int) -> tuple[int, int, int]:
    multipliers, offsets, haze = PRESETS[preset]
    values = [min(255, max(0, int(rgb[i] * multipliers[i] + offsets[i]))) for i in range(3)]
    if haze and y < height * 0.62:
        amount = haze * (1.0 - y / (height * 0.62))
        values = [int(value * (1 - amount) + (218, 211, 198)[i] * amount) for i, value in enumerate(values)]
    edge = abs(x - width / 2) / (width / 2)
    vignette = max(0.0, 1.0 - 0.10 * edge * edge)
    return tuple(int(value * vignette) for value in values)


def render_scene(sources: list[tuple[int, int, bytearray]], recipe: dict, width: int, height: int) -> bytearray:
    pixels = bytearray(width * height * 3)
    parts = recipe["parts"]
    segment_width = width // len(parts)
    feather = min(250, max(1, segment_width // 3))
    boundaries = [segment_width * i for i in range(1, len(parts))]
    for y in range(height):
        for x in range(width):
            part_index = min(len(parts) - 1, x // segment_width)
            local_x = x - part_index * segment_width
            rgb = sample_part(sources[parts[part_index]["source_index"]], local_x, segment_width, y, parts[part_index])
            for boundary_index, boundary in enumerate(boundaries):
                distance = x - boundary
                if abs(distance) < feather:
                    left_part = parts[boundary_index]
                    right_part = parts[boundary_index + 1]
                    left_rgb = sample_part(sources[left_part["source_index"]], x - boundary_index * segment_width, segment_width, y, left_part)
                    right_rgb = sample_part(sources[right_part["source_index"]], x - (boundary_index + 1) * segment_width, segment_width, y, right_part)
                    amount = (distance + feather) / (2 * feather)
                    rgb = tuple(int(left_rgb[i] * (1 - amount) + right_rgb[i] * amount) for i in range(3))
                    break
            target = (y * width + x) * 3
            pixels[target : target + 3] = bytes(grade(rgb, recipe["preset"], x, y, width, height))
    return pixels


def make_variants(source_paths: list[Path], output: Path, metadata_path: Path, count: int, seed: int) -> None:
    if not source_paths:
        raise RuntimeError("no real panoramas found; add one under assets/panoramas/real or keep martian_panorama.png")
    if shutil.which("sips") is None:
        raise RuntimeError("make_variants.py requires macOS sips or Pillow for JPEG output")
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="martian-variants-") as temp_dir:
        temporary = Path(temp_dir)
        loaded = []
        source_metadata = {}
        for path in source_paths:
            dimensions = read_rgb_png(as_png(path, temporary))
            loaded.append(dimensions)
            try:
                metadata_file = str(path.resolve().relative_to(Path.cwd().resolve()))
            except ValueError:
                metadata_file = str(path)
            source_metadata[source_id(path)] = {"file": metadata_file, "width": dimensions[0], "height": dimensions[1]}
        width, height, _ = loaded[0]
        if any((source[0], source[1]) != (width, height) for source in loaded):
            raise RuntimeError("all real panoramas must have matching dimensions")
        rng = random.Random(seed)
        variants = {}
        preset_names = list(PRESETS)
        for index in range(1, count + 1):
            preset = preset_names[(index - 1) % len(preset_names)]
            splice = len(loaded) > 1 and index % 4 == 0
            part_count = 2 + (index % 3 == 0) if splice else 1
            selected = list(range(len(loaded))) if splice and len(loaded) >= part_count else [((index - 1) % len(loaded))]
            if splice and len(selected) < part_count:
                selected = [selected[i % len(selected)] for i in range(part_count)]
            parts = []
            for part_index in range(part_count):
                parts.append({
                    "source_index": selected[part_index],
                    "roll": rng.randrange(width),
                    "zoom": round(rng.uniform(0.70, 1.00), 4),
                    "mirror": bool(index % 11 == 0 and part_index == 0),
                    "vertical_shift": rng.randint(-12, 12),
                })
            recipe = {
                "type": "splice" if splice else "single",
                "seed": seed + index,
                "preset": preset,
                "feather_px": 250 if splice else 0,
                "parts": parts,
                "haze": PRESETS[preset][2] > 0,
                "sources": list(dict.fromkeys(source_id(source_paths[part["source_index"]]) for part in parts)),
            }
            pixels = render_scene(loaded, recipe, width, height)
            png_path = temporary / f"scene_{index:03d}.png"
            jpg_path = output / f"scene_{index:03d}.jpg"
            write_rgb_png(png_path, width, height, pixels)
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92", str(png_path), "--out", str(jpg_path)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            variants[jpg_path.name] = {"sources": recipe["sources"], "recipe": recipe}
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(json.dumps({"sources": source_metadata, "variants": variants}, indent=2) + "\n", encoding="utf-8")
    print(f"created {count} static derived panoramas in {output}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", action="append", type=Path, help="real panorama path; repeat for multiple sources")
    parser.add_argument("--output", type=Path, default=Path("assets/panoramas/derived"))
    parser.add_argument("--metadata", type=Path, default=Path("assets/panoramas/variants.json"))
    parser.add_argument("--count", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20261022)
    args = parser.parse_args()
    root = Path.cwd()
    source_paths = [path if path.is_absolute() else root / path for path in args.source] if args.source else discover_sources(root)
    make_variants(source_paths, args.output, args.metadata, args.count, args.seed)


if __name__ == "__main__":
    main()
