# M0 audit

## Repository and safety

This directory was already a Git repository. Its pre-rebuild state was recorded
in commit `386572d` (`M0: snapshot pre-rebuild state`) before any files were
quarantined. No images or generators were deleted.

The previous Python/Pygame implementation and its tests are preserved under
`_legacy/` so the browser rebuild does not depend on them.

## Inventory

| Path | What it is | Status | Decision |
| --- | --- | --- | --- |
| `README.md` | Previous Python/Pygame run instructions | Not suitable for the browser brief | Replace for the new runtime; original content is preserved by the M0 snapshot commit |
| `assets/` | Generated square/layered terrain assets and manifests | Files are readable assets, but manifests target the old Pygame renderer | Keep as salvage/reference; browser build uses the panorama source and new assets |
| `assets/real/` | Panorama-derived 2048×720 layer tiles, contact sheets, and manifest | Usable images, wrong runtime format for the new node grid | Keep as reference; do not delete |
| `data/` | Raw dataset, processed dataset, and cached square terrain chunks | Source data and old generated cache; not needed at runtime | Keep; not loaded by the browser |
| `outputs/` | Old generated square terrain/elevation output and manifest | Works for the old Python pipeline only | Keep; not loaded by the browser |
| `_legacy/` | Quarantined previous source, tests, and pipeline | Preserved verbatim from the working tree | Keep for recovery and reference |
| `*.png` at repo root | Existing landscape, panorama, viewport, and debug images | Readable static assets | Keep; the 4:1 panorama is copied into the new asset location without altering the original |
| `.gitignore`, `.gitattributes` | Repository metadata | Valid | Keep |
| `.pytest_cache`, `.ruff_cache`, `.DS_Store` | Local tool/editor caches | Not runtime inputs | Keep untouched; exclude from the new runtime |

## Panorama images

Original panorama-like images found at the repository root:

| Path | Dimensions | Notes |
| --- | --- | --- |
| `martian_panorama.png` | 2048×512 | The only true 4:1 source panorama; salvage for node 1,1 |
| `martian_strip.png` | 1280×256 | A 5:1 strip/debug render, not the requested 4:1 source |

Other related images:

- `assets/real/tiles/{sky,far,mid,base}/ *_0000.png` through `*_0007.png` are 32 panorama-derived 2048×720 RGB tiles made from `martian_panorama.png`; they are old renderer artifacts, not independent node panoramas.
- `martian_landscape_1024.png` and `center_region.png` are square crops, not panoramas.
- The many `data/`, `outputs/`, and `assets/tiles/` images are square terrain tiles.

## Generator audit

No Colab notebook or script using `diffusers.StableDiffusionPanoramaPipeline`,
Stable Diffusion 1.5, or a 512×2048 output configuration exists in this
checkout. The closest files are:

- `_legacy/pipeline/build.py`: offline post-processing that reads the already
  existing `martian_panorama.png`, makes a horizontal seam, stretches bands,
  and writes old Pygame layer tiles. It is not a panorama generator and is
  preserved unmodified.
- `_legacy/src/generate/pregenerate.py`: a PyTorch conditional square-tile
  generator, not a panorama generator.

## Why the old movement was broken for this brief

The old runtime was a Python/Pygame renderer driven by a one-dimensional pixel
camera and a separate clamped depth coordinate. Left/right changed a scroll
position and up/down changed depth; there was no `{x, y, heading}` state, no
bounded 4×4 node grid, no panorama FOV window, no browser/file:// entry point,
and it required Python dependencies. That model cannot satisfy the requested
neighbour-node movement or zero-network double-click launch.

## M0 disposition

All old source code was moved to `_legacy/`; images, datasets, generated assets,
and the old pipeline files were preserved. The rebuild may add a small plain
HTML/CSS/JavaScript runtime at the repository root and offline scripts under
`tools/`.
