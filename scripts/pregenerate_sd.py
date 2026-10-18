# scripts/pregenerate_sd.py
"""Convert Stable Diffusion outputs into the manifest format WorldLoader expects.

Reads texture + elevation PNGs from an SD output directory and emits
outputs/manifest.json with the correct schema.

Supported input layouts:
    <sd_dir>/textures/<biome>/<tile>.png      (nested by biome)
    <sd_dir>/textures/<tile>.png              (flat - assign biome from filename prefix)
    <sd_dir>/elevation/<biome>/<tile>.png     (nested by biome)
    <sd_dir>/elevation/<tile>.png             (flat)

Usage:
    python scripts/pregenerate_sd.py [sd_outputs_dir] [output_dir]

Defaults:
    sd_outputs_dir = outputs_sd
    output_dir     = outputs
"""

from __future__ import annotations

import json
import re
from pathlib import Path
import sys

BIOMES = ["mountain", "sand_plain", "dune", "crater", "rocky_outcrop"]


def _biome_from_name(filename: str) -> str | None:
    """Try to infer biome from filename prefix."""
    name = filename.lower()
    for biome in BIOMES:
        if name.startswith(biome):
            return biome
    return None


def pregenerate_sd(sd_dir: str | Path, output_dir: str | Path) -> Path:
    sd_root = Path(sd_dir)
    out_root = Path(output_dir)
    textures_out = out_root / "textures"
    elevation_out = out_root / "elevation"
    textures_out.mkdir(parents=True, exist_ok=True)
    elevation_out.mkdir(parents=True, exist_ok=True)

    tiles = []
    tile_id = 0

    tex_root = sd_root / "textures"
    elev_root = sd_root / "elevation"

    # Collect all texture PNGs (nested by biome or flat)
    texture_files = []
    if tex_root.exists():
        texture_files = sorted(tex_root.rglob("*.png"))

    if not texture_files:
        print(f"[warn] No texture PNGs found under {tex_root}")
        # Write empty manifest anyway
        manifest = {"version": 1, "tiles": []}
        manifest_path = out_root / "manifest.json"
        with open(manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)
        print(f"\n[done] 0 tiles -> {manifest_path}")
        return manifest_path

    import shutil
    from PIL import Image
    import numpy as np

    for tex_path in texture_files:
        # Determine biome: from parent dir name or filename prefix
        parent_name = tex_path.parent.name.lower()
        if parent_name in BIOMES:
            biome = parent_name
        else:
            biome = _biome_from_name(tex_path.stem)
            if biome is None:
                print(f"[skip] {tex_path}: cannot determine biome from name")
                continue

        tile_id += 1
        tex_name = f"tile_{tile_id:04d}.png"
        elev_name = f"tile_{tile_id:04d}.png"

        # Copy texture
        shutil.copy2(tex_path, textures_out / tex_name)

        # Copy or derive elevation
        elev_path = elev_root / parent_name / tex_path.name if (elev_root / parent_name).exists() else None
        if elev_path is None:
            # Try flat elevation
            elev_path = elev_root / tex_path.name if elev_root.exists() else None
        if elev_path is None or not elev_path.exists():
            # Derive elevation from texture brightness
            img = Image.open(tex_path).convert("RGB")
            arr = np.asarray(img, dtype=np.float32)
            elevation = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
            Image.fromarray(elevation.astype(np.uint8), mode="L").save(
                elevation_out / elev_name
            )
        else:
            shutil.copy2(elev_path, elevation_out / elev_name)

        tiles.append(
            {
                "id": f"tile_{tile_id:04d}",
                "biome": biome,
                "texture": f"textures/{tex_name}",
                "elevation": f"elevation/{elev_name}",
                "width": 256,
                "height": 256,
                "seed": None,
            }
        )
        print(f"[ok] {biome}: {tex_path.name} -> tile_{tile_id:04d}.png")

    manifest = {"version": 1, "tiles": tiles}
    manifest_path = out_root / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\n[done] {tile_id} tiles -> {manifest_path}")
    return manifest_path


if __name__ == "__main__":
    sd_dir = sys.argv[1] if len(sys.argv) > 1 else "outputs_sd"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "outputs"
    pregenerate_sd(sd_dir, output_dir)
