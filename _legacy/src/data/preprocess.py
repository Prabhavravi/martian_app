"""Data preprocessing for Martian landscape terrain tiles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image

BIOMES = ["mountain", "sand_plain", "dune", "crater", "rocky_outcrop"]
DEFAULT_RESOLUTION = 256


@dataclass
class ProcessedTile:
    path: str
    biome: str
    biome_index: int
    width: int
    height: int


def load_raw_dataset(raw_dir: str | Path) -> List[Tuple[Path, str]]:
    """Recursively load raw terrain images grouped by biome subdirectory.

    Returns a list of (image_path, biome_label) tuples.
    """
    raw_root = Path(raw_dir)
    samples: List[Tuple[Path, str]] = []
    for biome_dir in sorted(raw_root.iterdir()):
        if not biome_dir.is_dir():
            continue
        biome = biome_dir.name
        for img_path in sorted(biome_dir.iterdir()):
            if img_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                samples.append((img_path, biome))
    return samples


def preprocess_tile(
    image_path: Path,
    output_dir: str | Path,
    resolution: int = DEFAULT_RESOLUTION,
) -> ProcessedTile:
    """Resize, normalize, and save a single tile to the processed directory.

    Returns a ProcessedTile dataclass describing the saved file.
    """
    output_root = Path(output_dir)
    img = Image.open(image_path).convert("RGB")
    img = img.resize((resolution, resolution), Image.Resampling.BILINEAR)

    arr = np.asarray(img, dtype=np.float32) / 255.0
    arr = (arr * 2.0) - 1.0  # normalize to [-1, 1]

    img_out = Image.fromarray(((arr + 1.0) / 2.0 * 255.0).astype(np.uint8))
    rel_path = image_path.relative_to(Path(image_path).anchor)
    out_path = output_root / rel_path
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img_out.save(out_path)

    biome = image_path.parent.name
    biome_index = BIOMES.index(biome) if biome in BIOMES else -1

    return ProcessedTile(
        path=str(out_path),
        biome=biome,
        biome_index=biome_index,
        width=resolution,
        height=resolution,
    )


def build_processed_dataset(
    raw_dir: str | Path,
    output_dir: str | Path,
    resolution: int = DEFAULT_RESOLUTION,
    val_split: float = 0.2,
    seed: int = 42,
) -> Dict[str, List[ProcessedTile]]:
    """Preprocess all raw tiles and split into train/val sets.

    Returns a dict with keys "train" and "val", each a list of ProcessedTile.
    """
    samples = load_raw_dataset(raw_dir)
    if not samples:
        raise ValueError(f"No raw images found under {raw_dir}")

    train_samples, val_samples = _split_train_val(samples, val_split, seed)

    train_tiles = [preprocess_tile(p, output_dir, resolution) for p, _ in train_samples]
    val_tiles = [preprocess_tile(p, output_dir, resolution) for p, _ in val_samples]

    return {"train": train_tiles, "val": val_tiles}


def _split_train_val(
    samples: List[Tuple[Path, str]],
    val_split: float,
    seed: int,
) -> Tuple[List[Tuple[Path, str]], List[Tuple[Path, str]]]:
    """Deterministic train/val split without external dependencies."""
    rng = np.random.RandomState(seed)
    indices = np.arange(len(samples))
    rng.shuffle(indices)
    n_val = int(len(samples) * val_split)
    val_idx = indices[:n_val]
    train_idx = indices[n_val:]
    train_samples = [samples[i] for i in train_idx]
    val_samples = [samples[i] for i in val_idx]
    return train_samples, val_samples
