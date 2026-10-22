# Martian Rover design

## Runtime

The game is a static, dependency-free browser app. `index.html` loads classic
scripts in order, so it works from `file://` with no server and no network:

1. `world.js` — grid configuration, node image manifest, and pure state/movement functions.
2. `game.js` — canvas renderer, image preloading, transitions, input, HUD, and event mode.
3. `styles.css` — full-window rover-camera framing and restrained HUD styling.

Offline asset helpers live under `tools/`; they are never loaded by the game.
The logic test is `tests/logic.test.js` and runs with `node` only.

## World and state

The world is a 4×4 grid (`WORLD.width` and `WORLD.height` in `world.js`). Each
node resolves to `assets/panoramas/node_{x}_{y}.jpg` or `.png`; a node can
instead point at a real panorama. The initial state is `{x: 1, y: 1,
heading: 0}`. Heading is degrees, normalized to `[0, 360)`, with 0° north,
90° east, 180° south, and 270° west.

Movement snaps the current heading to the nearest cardinal direction. Forward
moves one node in that direction; backward moves in the opposite direction.
Grid edges block movement and trigger a short bump. Heading survives movement.
The pure functions never touch the DOM.

## Panorama view

Each panorama is an equirectangular horizontal strip. The canvas draws a 90°
window from a 360° span and wraps the source horizontally. If a source is not
4:1, the offline placeholder/asset preparation path uses a cover-fit crop; it
never stretches an image at runtime. Turning continuously changes the center
sample and can wrap through the full 360° without a jump.

## Motion and interaction

W/S or Up/Down request node movement; A/D or Left/Right turn continuously.
Movement transitions last about 700 ms: forward zooms from 1.0 to 1.2 while
fading out the current view and fades the next view from 0.9 to 1.0; backward
uses the reverse visual direction. Input is locked during a transition.
All 16 node images are preloaded behind a loading screen.

The HUD shows heading, cardinal direction, coordinates, and a small minimap
with position and facing. On-screen controls mirror the keyboard for touch.
`?event=1` requests fullscreen on the first click, hides the cursor, enables a
slow attract-mode pan, and returns to the start node after 60 seconds of idle;
any input cancels attract mode immediately.

