#!/usr/bin/env python3
"""Rebuild all offline scenes, static node data, contact sheet, and tests."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def real_sources(root: Path) -> list[Path]:
    paths = [root / "assets/panoramas/martian_panorama.png", root / "assets/panoramas/martian_panorama_seamless.png"]
    real_dir = root / "assets/panoramas/real"
    if real_dir.exists():
        paths.extend(sorted(path for path in real_dir.iterdir() if path.suffix.lower() in {".png", ".jpg", ".jpeg"}))
    unique = []
    seen = set()
    for path in paths:
        if path.exists() and path.resolve() not in seen:
            unique.append(path)
            seen.add(path.resolve())
    return unique


def run(root: Path, command: list[str]) -> None:
    print("$", " ".join(command))
    subprocess.run(command, cwd=root, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=32)
    parser.add_argument("--seed", type=int, default=20261022)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sources = real_sources(root)
    if not sources:
        raise SystemExit("No real panoramas found")
    variant_command = [sys.executable, "tools/make_variants.py", "--count", str(args.count), "--seed", str(args.seed)]
    for source in sources:
        variant_command.extend(["--source", str(source)])
    run(root, variant_command)
    run(root, [sys.executable, "tools/assign_nodes.py"])
    run(root, [sys.executable, "tools/make_contact_sheet.py"])
    run(root, ["node", "tests/assets.test.js"])
    run(root, ["node", "tests/logic.test.js"])
    run(root, ["node", "tests/variety.test.js"])
    print(f"World rebuilt from {len(sources)} real panorama files")


if __name__ == "__main__":
    main()
