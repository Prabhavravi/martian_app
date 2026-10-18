# scripts/download_terrain.py
"""Download terrain photos into data/raw/<biome>/ folders.

Usage:
    python scripts/download_terrain.py <biome> <url1> [url2] ...

Biomes: mountain, sand_plain, dune, crater, rocky_outcrop
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError, HTTPError

BIOMES = ["mountain", "sand_plain", "dune", "crater", "rocky_outcrop"]


def download(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        urlretrieve(url, dest)
        print(f"[ok]   {dest.name} <- {url}")
        return True
    except (HTTPError, URLError, Exception) as exc:  # noqa: BLE001
        print(f"[fail] {url}: {exc}")
        return False


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python scripts/download_terrain.py <biome> <url1> [url2] ...")
        print(f"Biomes: {', '.join(BIOMES)}")
        sys.exit(1)

    biome = sys.argv[1]
    if biome not in BIOMES:
        print(f"Unknown biome '{biome}'. Choose from: {', '.join(BIOMES)}")
        sys.exit(1)

    urls = sys.argv[2:]
    raw_root = Path("data/raw") / biome
    count = 0
    for i, url in enumerate(urls, 1):
        ext = os.path.splitext(url)[1].lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            ext = ".jpg"
        dest = raw_root / f"{biome}_{i:03d}{ext}"
        if download(url, dest):
            count += 1
    print(f"\nDownloaded {count}/{len(urls)} images to {raw_root}")


if __name__ == "__main__":
    main()
