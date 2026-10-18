# scripts/generate_sd.py
import importlib

try:
    torch = importlib.import_module("torch")
except ModuleNotFoundError as exc:
    raise RuntimeError("PyTorch is required; install it in the active Python environment.") from exc

try:
    StableDiffusionPipeline = importlib.import_module("diffusers").StableDiffusionPipeline
except ModuleNotFoundError as exc:
    raise RuntimeError(
        "The diffusers package is required; install it with `pip install diffusers`."
    ) from exc
try:
    Image = importlib.import_module("PIL.Image")
except ModuleNotFoundError as exc:
    raise RuntimeError("Pillow is required; install it with `pip install Pillow`.") from exc
import os
from pathlib import Path

DEVICE = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")

pipe = StableDiffusionPipeline.from_pretrained(
    "runwayml/stable-diffusion-v1-5",
    torch_dtype=torch.float16 if DEVICE != "cpu" else torch.float32,
).to(DEVICE)

BIOMES = {
    "mountain": "martian mountain terrain, reddish rocky mountains, sci-fi landscape, high detail",
    "sand_plain": "martian sand plain, sandy desert texture, reddish sand, barren",
    "dune": "martian sand dunes, ripple patterns, reddish sand, desert",
    "crater": "martian crater, impact crater, rocky terrain, reddish soil",
    "rocky_outcrop": "martian rocky outcrop, exposed rock, reddish stone, desert",
}

output_dir = Path("outputs_sd")
(output_dir / "textures").mkdir(parents=True, exist_ok=True)
(output_dir / "elevation").mkdir(parents=True, exist_ok=True)

for biome, prompt in BIOMES.items():
    for i in range(10):  # 10 tiles per biome
        image = pipe(prompt, num_inference_steps=20, guidance_scale=7.5).images[0]
        image = image.resize((256, 256))
        image.save(output_dir / "textures" / f"{biome}_{i:03d}.png")
        
        # Elevation from brightness
        arr = __import__("numpy").asarray(image.convert("L"), dtype=__import__("numpy").uint8)
        Image.fromarray(arr, mode="L").save(output_dir / "elevation" / f"{biome}_{i:03d}.png")

print("Done — outputs in outputs_sd/")
