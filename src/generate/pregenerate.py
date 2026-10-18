"""Offline pre-generation pipeline: sample conditioned texture tiles + elevation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np
import torch
from PIL import Image
from tqdm import tqdm

from src.models.cgan import ConditionalGenerator

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

BIOMES = ["mountain", "sand_plain", "dune", "crater", "rocky_outcrop"]


def load_generator(
    checkpoint_path: str | Path,
    latent_dim: int = 100,
    num_biomes: int = 5,
    img_size: int = 256,
) -> ConditionalGenerator:
    """Load a fine-tuned generator from a checkpoint file."""
    checkpoint = torch.load(checkpoint_path, map_location=DEVICE)
    state_dict = checkpoint.get("generator", checkpoint)

    generator = ConditionalGenerator(
        latent_dim=latent_dim, num_biomes=num_biomes, img_channels=3, img_size=img_size
    ).to(DEVICE)
    generator.load_state_dict(state_dict)
    generator.eval()
    return generator


def derive_elevation(texture_path: str | Path, output_path: str | Path) -> None:
    """Derive a grayscale elevation map from a texture tile by brightness.

    Elevation = 0.299*R + 0.587*G + 0.114*B (luminance), saved as PNG.
    Darker areas = lower elevation, brighter = higher elevation.
    """
    img = Image.open(texture_path).convert("RGB")
    arr = np.asarray(img, dtype=np.float32)
    elevation = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    elevation = elevation.astype(np.uint8)
    Image.fromarray(elevation, mode="L").save(output_path)


def pregenerate(
    checkpoint_path: str | Path,
    output_dir: str | Path,
    num_per_biome: int = 10,
    latent_dim: int = 100,
    img_size: int = 256,
    seed: int | None = None,
) -> Path:
    """Generate texture tiles + elevation maps per biome and emit manifest.json.

    Args:
        checkpoint_path: fine-tuned generator checkpoint (.pt).
        output_dir: root output directory (contains textures/ and elevation/).
        num_per_biome: number of tiles to generate per biome.
        latent_dim: generator latent dimension.
        img_size: tile resolution (power of two).
        seed: optional RNG seed for deterministic output.

    Returns the path to the written manifest.json.
    """
    if seed is not None:
        torch.manual_seed(seed)
        np.random.seed(seed)

    output_root = Path(output_dir)
    textures_dir = output_root / "textures"
    elevation_dir = output_root / "elevation"
    textures_dir.mkdir(parents=True, exist_ok=True)
    elevation_dir.mkdir(parents=True, exist_ok=True)

    generator = load_generator(
        checkpoint_path,
        latent_dim=latent_dim,
        num_biomes=len(BIOMES),
        img_size=img_size,
    )

    tiles: List[dict] = []
    tile_id = 0

    for biome_idx, biome in enumerate(tqdm(BIOMES, desc="biomes")):
        labels = torch.full((num_per_biome,), biome_idx, device=DEVICE, dtype=torch.long)
        z = torch.randn(num_per_biome, latent_dim, device=DEVICE)

        with torch.no_grad():
            imgs = generator(z, labels)  # [-1, 1]
            imgs = (imgs + 1.0) / 2.0  # [0, 1]
            imgs = imgs.clamp(0, 1)

        for i in range(num_per_biome):
            tile_id += 1
            img_tensor = imgs[i].cpu().clamp(0, 1) * 255.0
            img_array = img_tensor.permute(1, 2, 0).numpy().astype(np.uint8)
            img = Image.fromarray(img_array, mode="RGB")

            texture_name = f"tile_{tile_id:04d}.png"
            texture_rel = f"textures/{texture_name}"
            elevation_rel = f"elevation/tile_{tile_id:04d}.png"

            texture_path = textures_dir / texture_name
            elevation_path = elevation_dir / f"tile_{tile_id:04d}.png"

            img.save(texture_path)
            derive_elevation(texture_path, elevation_path)

            tiles.append(
                {
                    "id": f"tile_{tile_id:04d}",
                    "biome": biome,
                    "texture": texture_rel,
                    "elevation": elevation_rel,
                    "width": img_size,
                    "height": img_size,
                    "seed": seed,
                }
            )

    manifest = {"version": 1, "tiles": tiles}
    manifest_path = output_root / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"[pregenerate] generated {tile_id} tiles -> {manifest_path}")
    return manifest_path
