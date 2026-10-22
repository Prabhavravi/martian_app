# Martian Rover

A small offline browser game for a live event: turn through a pre-rendered
Martian panorama and drive a 4×4 grid of rover locations.

## Run

Double-click [`index.html`](/Users/prabhavravi/Documents/martian_app/index.html)
or open it in a browser. No server, framework, bundler, npm package, or
internet connection is required. The game preloads all 16 panoramas behind the
loading screen.

For event mode, open `index.html?event=1`. On the first click it requests
fullscreen, hides the cursor, and starts a 60-second idle countdown. After the
countdown the rover resets to the start node and slowly auto-pans; any input
cancels attract mode.

## Controls

- `A` / `D` or Left / Right: turn continuously.
- `W` / `S` or Up / Down: drive one grid node forward/backward.
- The on-screen arrow buttons work with touch or a mouse.

Forward/backward movement follows the cardinal direction nearest the current
heading. Grid edges bump and remain in place. Movement transitions last about
700 ms and lock input until the handoff completes.

## Assets and adding panoramas

World data lives in [`world.js`](/Users/prabhavravi/Documents/martian_app/world.js).
The default grid is 4×4. Each placeholder slot uses
`assets/panoramas/node_{x}_{y}.png`; the audited real 4:1 panorama is mapped to
the start node `(1, 3)` in `world.js` after one-time edge blending. To add a
real panorama, put a local image in `assets/panoramas/` and change the matching
`WORLD.nodes["x:y"]` entry. Prefer a 4:1 equirectangular image; for another
aspect ratio, make an offline cover-fit crop before mapping it and never
stretch it at runtime.

## Regenerate placeholders

The generator uses only the Python standard library and preserves existing
files by default:

```bash
python3 tools/make_placeholders.py
python3 tools/make_placeholders.py --overwrite
```

The default output is deterministic 2048×512 RGB PNGs for all missing 4×4
slots. It draws Mars-colored sky, dunes, rocks, and the node coordinate label,
and blends the horizontal edges offline for wrap-safe panning.

For a real 8-bit RGB PNG whose left and right edges do not meet, blend it once:

```bash
python3 tools/make_seamless.py input.png output_seamless.png
```

## Tests

Run the pure movement test with:

```bash
node tests/logic.test.js
```

The test has no dependencies and covers cardinal movement, bounds, heading
wraparound, and a forward/backward round trip.
