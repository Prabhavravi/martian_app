"""Paste this whole file into the existing Colab to add real panorama sources.

Usage: edit N, STEPS, and OUTPUT_DIR below, run the cell, and copy the resulting
gen_*.jpg files into assets/panoramas/real/. Existing files are skipped, so the
cell can be rerun after an interruption. This script runs only in Colab and is
never imported by the browser game.
"""

from __future__ import annotations

import inspect
import random
from pathlib import Path

import torch
from diffusers import DDIMScheduler, StableDiffusionPanoramaPipeline


# Quality/time tradeoff: 24 images at 28 steps is a useful first batch.
N = 24
STEPS = 28
BASE_SEED = 20261022
MODEL_ID = "runwayml/stable-diffusion-v1-5"

DRIVE_ROOT = Path("/content/drive/MyDrive")
if DRIVE_ROOT.exists():
    OUTPUT_DIR = DRIVE_ROOT / "martian_rover" / "assets" / "panoramas" / "real"
else:
    OUTPUT_DIR = Path("/content/martian_rover_real")

TERRAIN_PROMPTS = [
    "wide Martian dune field with wind-carved ripples",
    "wide Martian rocky ridge and scattered angular rocks",
    "wide Martian crater rim with layered eroded walls",
    "wide Martian canyon wall with distant mesas",
    "wide Martian boulder plain with low ridges",
    "wide flat Martian basalt plain with dark volcanic rocks",
    "wide Martian sand ripples flowing toward a low horizon",
    "wide Martian mesa landscape with isolated buttes",
    "wide Martian dry riverbed winding through red terrain",
    "wide Martian dust-hazy horizon with faint distant hills",
    "wide Martian scree slope beneath a rocky escarpment",
    "wide Martian low hills and wind-scoured gravel plain",
]
STYLE = "photorealistic static equirectangular panorama, rover eye height, natural Martian scale, muted rust red and ochre palette, clear terrain detail, no camera motion"
NEGATIVE = "no people, buildings, vehicles, text, watermark, vegetation, water, Earth-like clouds"


def enable_circular_padding(pipe):
    """Use circular padding when the installed diffusers build exposes it."""
    if hasattr(pipe, "enable_circular_padding"):
        pipe.enable_circular_padding()
        return "pipeline.enable_circular_padding()"
    if hasattr(pipe.unet, "set_circular_padding"):
        pipe.unet.set_circular_padding(True)
        return "unet.set_circular_padding(True)"
    if hasattr(pipe.unet.config, "circular_padding"):
        pipe.unet.config.circular_padding = True
        return "unet.config.circular_padding=True"
    return "not available in this diffusers build"


def generate():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Writing resumable batch to {OUTPUT_DIR}; N={N}, steps={STEPS}, model={MODEL_ID}")
    pipe = StableDiffusionPanoramaPipeline.from_pretrained(MODEL_ID, torch_dtype=torch.float16)
    pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
    pipe = pipe.to("cuda")
    print("Circular padding:", enable_circular_padding(pipe))
    try:
        pipe.enable_attention_slicing()
    except AttributeError:
        pass

    rng = random.Random(BASE_SEED)
    seeds = [rng.randrange(1, 2**31 - 1) for _ in range(N)]
    call_parameters = inspect.signature(pipe.__call__).parameters
    for index in range(1, N + 1):
        output_path = OUTPUT_DIR / f"gen_{index:03d}.jpg"
        if output_path.exists():
            print(f"skip {output_path.name}")
            continue
        prompt = f"{TERRAIN_PROMPTS[(index - 1) % len(TERRAIN_PROMPTS)]}, {STYLE}"
        kwargs = {
            "prompt": prompt,
            "negative_prompt": NEGATIVE,
            "height": 512,
            "width": 2048,
            "num_inference_steps": STEPS,
            "generator": torch.Generator(device="cuda").manual_seed(seeds[index - 1]),
        }
        if "circular_padding" in call_parameters:
            kwargs["circular_padding"] = True
        with torch.inference_mode():
            image = pipe(**kwargs).images[0]
        image.save(output_path, format="JPEG", quality=95, optimize=True)
        print(f"saved {output_path.name} seed={seeds[index - 1]} prompt={TERRAIN_PROMPTS[(index - 1) % len(TERRAIN_PROMPTS)]}")


if __name__ == "__main__":
    generate()
