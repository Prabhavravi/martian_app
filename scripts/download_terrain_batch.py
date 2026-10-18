# scripts/download_terrain_batch.py
"""Batch-download terrain photos from a URL list file into data/raw/<biome>/.

Usage:
    python scripts/download_terrain_batch.py <biome> <urls_file.txt>

The URLs file should contain one direct image URL per line. Blank lines and
lines starting with # are ignored.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.request import urlretrieve
from urllib.error import URLError, HTTPError

BIOMES = ["mountain", "sand_plain", "dune", "crater", "rocky_outcrop"]


def read_urls(path: str | Path) -> list[str]:
    """Read non-blank, non-comment URLs from a text file."""
    urls: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            urls.append(line)
    return urls


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
        print("Usage: python scripts/download_terrain_batch.py <biome> <urls_file.txt>")
        print(f"Biomes: {', '.join(BIOMES)}")
        sys.exit(1)

    biome = sys.argv[1]
    if biome not in BIOMES:
        print(f"Unknown biome '{biome}'. Choose from: {', '.join(BIOMES)}")
        sys.exit(1)

    urls_file = Path(sys.argv[2])
    if not urls_file.exists():
        print(f"URLs file not found: {urls_file}")
        sys.exit(1)

    urls = read_urls(urls_file)
    if not urls:
        print(f"No URLs found in {urls_file}")
        sys.exit(1)

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
