# Martian Rover

This project generates and displays a layered Martian landscape in a Pygame
rover-style explorer. The active runtime uses the pre-generated assets in
`assets/real/manifest.json` and keeps horizontal panorama movement seamless.

## Run the rover

From the repository root:

```bash
python -m src.martian_game
```

The default game loads the generated Martian landscape from:

```
assets/real/manifest.json
```

with texture tiles under `assets/real/tiles/`. Placeholder assets in `assets/`
are retained only for development and testing — they are not used by default.

To select a different manifest:

```bash
python -m src.martian_game --manifest PATH
```

## Controls

- Left arrow or `A`: move left
- Right arrow or `D`: move right
- Up arrow or `W`: move forward toward the horizon
- Down arrow or `S`: move backward toward the foreground
- Space: toggle the debug overlay
- Escape: quit

### Movement model

Horizontal movement is driven by a camera that scrolls at a constant speed
(300 px/sec by default, configurable via `scroll_speed_px_per_sec`). When the
world reaches its end it **loops** back to the beginning, so the panorama is
seamless and infinite.

Front/back movement controls a depth coordinate that is **clamped** to the
configured `[depth.min, depth.max]` range (default 0.0–1.0, starting at 0.5).
It cannot exit this range.

### Depth illusion (zoom / vertical offset)

The depth coordinate is normalized to `t` in `[0, 1]` and used to interpolate
two transforms on the terrain layers (`far`, `mid`, `base`):

- **Zoom** interpolates from `zoom_far` (0.92) at the far/min end to
  `zoom_near` (1.18) at the near/max end. Terrain tiles grow larger as you
  move backward and shrink as you move forward.
- **Vertical offset** interpolates from `offset_far_px` (-24) to
  `offset_near_px` (+48). Moving forward shifts terrain upward toward the
  horizon; moving backward shifts it downward into the foreground.

All terrain tiles are scaled around a **horizon line** at
`viewport_height * horizon_ratio` (default 0.45). The sky layer is kept fixed
and is unaffected by depth changes. Scaled surfaces are cached with quantized
zoom buckets to bound memory usage.

### Rendering modes

A manifest may declare a top-level `render_mode` (defaults to `layered` when
absent, for backwards compatibility with older/placeholder manifests):

- `layered` — the classic mode above. Each layer (`sky`, `far`, `mid`, `base`)
  is drawn as its own tile band and the terrain layers are depth-scaled around
  the horizon. Used by the placeholder/development assets in `assets/`.
- `single_panorama` — treats the `base` layer as a complete, opaque full-frame
  panorama (sky and terrain baked together) and draws only it. The effective
  zoom is clamped to at least `viewport_height / source_height` and the image is
  bottom-anchored, so the panorama always covers the full viewport height.
- `single_panorama_perspective` — used by the real pre-generated panorama in
  `assets/real/manifest.json` (the default).

The real layer images (`sky`, `far`, `mid`, `base`) are **opaque 2048×720
RGB panoramas**, not transparent compositing layers — each one is a complete,
full-frame slice of the Martian scene. Drawing them all on top of one another
(the layered approach) leaves vertical gaps once the terrain layers are
depth-scaled, so the fixed sky/background leaks in below the terrain when the
rover moves backward, and the sky scales together with the ground making
movement look unrealistic.

In `single_panorama_perspective` mode the `base` layer is split into a fixed
**sky band** (the top ~45% of the image) and a **ground band** (the remainder).
The sky stays stable while the rover moves horizontally. The ground is rendered
with a pseudo-3D **Mode 7-style scanline projection** rendered to a
low-resolution offscreen surface and scaled to the viewport:

- Rows near the horizon represent distant ground (narrow, slow-moving).
- Rows near the bottom represent nearby ground (wide, fast-moving).
- **Forward** movement (`W`/`Up`) increases the near ground scale so detail
  rushes toward the rover; **backward** movement (`S`/`Down`) decreases it so
  ground recedes toward the horizon.
- The sky never scales with the ground.
- Horizontal movement (`A`/`D`, `Left`/`Right`) scrolls the panorama texture
  with seamless wrapping.

The perspective ground surface is clamped so it always reaches the bottom of
the viewport, so no dark fallback background is ever revealed. Vertical zoom is
clamped to keep the ground anchored to the horizon.

### Camera motion

Movement uses acceleration and deceleration rather than instant full speed, and
adds subtle rover-style camera motion:

- **Vertical bob** while moving (a small sine offset tied to forward/backward
  speed).
- **Roll/sway** proportional to horizontal velocity, giving a gentle lean into
  turns.

These effects are deliberately subtle and never obscure the landscape.

## Tests

Run the test suite with:

```bash
pytest -q
```
