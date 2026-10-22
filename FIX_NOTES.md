# Panorama node bug diagnosis

## Initial diagnosis (written before code changes)

- The active world is a 4x4 grid (16 nodes). There is 1 original real panorama source in `assets/panoramas`: `martian_panorama.png` (2048x512). The project also contains its static edge-blended copy `assets/panoramas/martian_panorama_seamless.png` (2048x512), which is the real-content start-node asset. `martian_strip.png` is a 1280x256 strip and is not used as a node panorama. The 16 `node_x_y.png` files are generated placeholders, not real panoramas.
- `world.js` maps only node `(1,3)` to `assets/panoramas/martian_panorama_seamless.png`; every other node maps to an existing, case/extension-exact `assets/panoramas/node_x_y.png` placeholder. The current mapping therefore intentionally switches from the real panorama to a brown placeholder after moving.
- The brown image is static artwork generated offline by `tools/make_placeholders.py` (`make_placeholder`). It is not a runtime animated landscape. Separately, `game.js` fills the canvas with `#351611` in `render()` and `drawNode()` silently returns when an image is unavailable, so a load failure would also leave a brown runtime fallback with no warning.
- The movement code uses `moveOneNode()` with the expected `(x,y)` direction vectors; the mapping table has no missing or mis-cased paths. Initial evidence points to a missing-real-asset/design problem plus a silent runtime fallback bug, not an x/y swap or off-by-one. Temporary move/load logging will verify the requested node and actual load result before the fix.

## Asset inventory and mapping evidence

The complete node mapping and existence/case check was run with Node using `world.js` and `fs`; all 16 currently mapped files existed and matched their names exactly. All current node PNGs are 2048x512.

The active runtime scan found no procedural terrain renderer. The only animation is the normal canvas render loop and rover bump effect; the brown placeholder-looking content comes from the placeholder PNG mappings above (or, on a missing image, the `#351611` canvas fill).

## Temporary browser move/load log

I added temporary `console.log` calls, ran the game in Chrome from a local HTTP server, and clicked Forward once from the start node `(1,3)`. The browser loaded all 16 requested files successfully; the relevant output was:

```text
[rover image] file=assets/panoramas/martian_panorama_seamless.png success=true
[rover image] file=assets/panoramas/node_1_2.png success=true
[rover move] node=(1,2) file=assets/panoramas/node_1_2.png success=true moved=true
```

The complete load log contained `success=true` for all 16 current mappings and no `success=false` entries. Therefore the observed switch is not an image-load failure and not a wrong node index: `(1,3)` correctly moves north to `(1,2)`, whose existing mapping is a static placeholder PNG. The fix is both asset/mapping-related (replace placeholder mappings with static derived panoramas) and a defensive code fix (remove the silent brown canvas fallback and use the nearest real panorama on a genuine load failure).

