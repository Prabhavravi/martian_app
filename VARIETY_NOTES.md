# Landscape variety measurements

## Step 1: baseline, before changes

- The grid is 4×4: 16 nodes, with 16 distinct mapped file paths.
- There is 1 original real source panorama: `assets/panoramas/martian_panorama.png` (2048×512). The active start image `assets/panoramas/martian_panorama_seamless.png` is its static seam-blended copy, also 2048×512. `martian_strip.png` is 1280×256 and is not a node panorama.
- Every current derived node uses a distinct `node_x_y.jpg` filename, but all 15 derived files were generated from the same single source image by `tools/make_variants.py`. The generator uses `index = y * width_nodes + x`, a roll of `(width * (index + 1) // 17) % width`, mirror on odd indexes, and one of five small brightness factors. There is no node metadata recording different source IDs, and there is no modulo bug in the node index: the repetition is caused by the one-source budget, not by world-coordinate assignment.
- The current world mapping is generated implicitly by the loop in `world.js`: every node initially maps to `assets/panoramas/node_x_y.jpg`, then `(1,3)` is overwritten with `martian_panorama_seamless.png`. Thus the grid has 16 distinct files but only 1 source ID/scene family.

### Straight paths from the start `(1,3)`

Source sequence means source panorama identity, not filename. All current derived files have the same source identity as the start panorama, so the first repeated source is immediate in every direction.

| Heading | Node sequence | Source sequence | First repeated source distance |
|---|---|---|---:|
| 0° / north | (1,3) → (1,2) → (1,1) → (1,0) | base → base → base → base | 1 node |
| 90° / east | (1,3) → (2,3) → (3,3) | base → base → base | 1 node |
| 180° / south | (1,3) | base | no move; edge immediately |
| 270° / west | (1,3) → (0,3) | base → base | 1 node |

`contact_sheet.jpg` was generated from these 16 mapped files at 1680×528; its labels show the grid coordinates and the current `base`/`derived` source family. The current variety failure is an asset/source-budget problem, not a movement or transition problem.

## Step 2: offline scene generation

`tools/make_variants.py` now produces 32 deterministic 2048×512 JPEG scenes in `assets/panoramas/derived/` using five colour grades (`dusty_afternoon`, `rust_dusk`, `pale_haze`, `dark_basalt`, `butte_orange`), crop/zoom, horizontal roll, sparse mirroring, vertical shifts, haze, vignette, and 250-pixel feathered splices. The current project has two real panorama files available as inputs (`martian_panorama.png` and its static seamless copy), representing one underlying captured scene; 8 of the 32 generated recipes are two-source splices. `assets/panoramas/variants.json` records each variant's `sources` and complete recipe.

The generator also discovers future images placed in `assets/panoramas/real/`, including `gen_*.jpg`, without requiring source-code edits. With only one underlying captured scene, source separation remains limited until Colab supplies additional genuinely different panoramas; the derived recipes provide visual variation but do not pretend to create new source provenance.

