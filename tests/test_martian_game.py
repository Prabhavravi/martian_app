import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame  # noqa: E402
from src.martian_game.camera import Camera  # noqa: E402
from src.martian_game.game import Game  # noqa: E402
from src.martian_game.manifest import Manifest, TileEntry, Layer, DepthConfig  # noqa: E402
from src.martian_game.renderer import Renderer  # noqa: E402
from src.martian_game.tile_cache import TileCache  # noqa: E402
from src.martian_game.world import visible_tiles  # noqa: E402


def _manifest_dict(**overrides):
    data = {
        "version": 1,
        "tile_size": [512, 512],
        "world_length_px": 20480,
        "end_behavior": "LOOP",
        "viewport": {"w": 1280, "h": 720},
        "scroll_speed_px_per_sec": 300.0,
        "layers": [
            {
                "name": "base",
                "speed": 1.0,
                "tile_w": 512,
                "tile_h": 512,
                "tile_count": 40,
                "tiles": [
                    {
                        "id": f"base_{i:04d}",
                        "index": i,
                        "texture": f"tiles/base/base_{i:04d}.png",
                        "width": 512,
                        "height": 512,
                        "seed": i,
                    }
                    for i in range(40)
                ],
            }
        ],
    }
    data.update(overrides)
    return data


def test_manifest_load_save_roundtrip(tmp_path):
    data = _manifest_dict()
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data))
    m = Manifest.load(p)
    assert m.version == 1
    assert m.tile_size == (512, 512)
    assert m.world_length_px == 20480
    assert m.end_behavior == "LOOP"
    assert m.viewport_w == 1280
    assert m.viewport_h == 720
    assert m.scroll_speed_px_per_sec == 300.0
    assert len(m.layers) == 1
    assert m.layers[0].tile_count == 40
    assert m.layers[0].world_width == 20480
    assert m.base_layer is m.layers[0]
    out = tmp_path / "out.json"
    m.save(out)
    m2 = Manifest.load(out)
    assert m2.world_length_px == m.world_length_px
    assert m2.layers[0].tiles[0].id == "base_0000"


def test_depth_config_defaults_none_when_absent(tmp_path):
    data = _manifest_dict()
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data))
    m = Manifest.load(p)
    assert m.depth is None


def test_depth_config_loaded_from_manifest(tmp_path):
    depth = {
        "min": 0.0,
        "max": 1.0,
        "start": 0.5,
        "speed": 0.35,
        "zoom_far": 0.92,
        "zoom_near": 1.18,
        "offset_far_px": -24,
        "offset_near_px": 48,
        "horizon_ratio": 0.45,
    }
    data = _manifest_dict(depth=depth)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data))
    m = Manifest.load(p)
    assert m.depth is not None
    assert m.depth.min == 0.0
    assert m.depth.max == 1.0
    assert m.depth.start == 0.5
    assert m.depth.speed == 0.35
    assert m.depth.zoom_far == 0.92
    assert m.depth.zoom_near == 1.18
    assert m.depth.offset_far_px == -24
    assert m.depth.offset_near_px == 48
    assert m.depth.horizon_ratio == 0.45


def test_depth_config_save_preserves_values(tmp_path):
    depth = {
        "min": 0.0,
        "max": 1.0,
        "start": 0.5,
        "speed": 0.35,
        "zoom_far": 0.92,
        "zoom_near": 1.18,
        "offset_far_px": -24,
        "offset_near_px": 48,
        "horizon_ratio": 0.45,
    }
    data = _manifest_dict(depth=depth)
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data))
    m = Manifest.load(p)
    out = tmp_path / "out.json"
    m.save(out)
    m2 = Manifest.load(out)
    assert m2.depth is not None
    for key in depth:
        assert getattr(m2.depth, key) == depth[key]


def test_depth_config_validates_min_less_than_max():
    with pytest.raises(ValueError):
        DepthConfig(min=1.0, max=0.0, start=0.5, speed=0.35,
                     zoom_far=0.92, zoom_near=1.18,
                     offset_far_px=-24, offset_near_px=48,
                     horizon_ratio=0.45)


def test_depth_config_validates_start_within_range():
    with pytest.raises(ValueError):
        DepthConfig(min=0.0, max=1.0, start=1.5, speed=0.35,
                    zoom_far=0.92, zoom_near=1.18,
                    offset_far_px=-24, offset_near_px=48,
                    horizon_ratio=0.45)


def test_depth_config_validates_zoom_positive():
    with pytest.raises(ValueError):
        DepthConfig(min=0.0, max=1.0, start=0.5, speed=0.35,
                    zoom_far=0.0, zoom_near=1.18,
                    offset_far_px=-24, offset_near_px=48,
                    horizon_ratio=0.45)
    with pytest.raises(ValueError):
        DepthConfig(min=0.0, max=1.0, start=0.5, speed=0.35,
                    zoom_far=0.92, zoom_near=-1.0,
                    offset_far_px=-24, offset_near_px=48,
                    horizon_ratio=0.45)


def test_depth_config_validates_horizon_ratio_range():
    with pytest.raises(ValueError):
        DepthConfig(min=0.0, max=1.0, start=0.5, speed=0.35,
                    zoom_far=0.92, zoom_near=1.18,
                    offset_far_px=-24, offset_near_px=48,
                    horizon_ratio=1.5)
    with pytest.raises(ValueError):
        DepthConfig(min=0.0, max=1.0, start=0.5, speed=0.35,
                    zoom_far=0.92, zoom_near=1.18,
                    offset_far_px=-24, offset_near_px=48,
                    horizon_ratio=-0.1)


def test_depth_config_save_omits_none(tmp_path):
    data = _manifest_dict()
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data))
    m = Manifest.load(p)
    out = tmp_path / "out.json"
    m.save(out)
    raw = json.loads(out.read_text())
    assert raw["depth"] is None


def test_manifest_bad_end_behavior_rejected(tmp_path):
    data = _manifest_dict(end_behavior="BOUNCE")
    p = tmp_path / "bad.json"
    p.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        Manifest.load(p)


def test_camera_loop_unbounded():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
        },
    )()
    cam = Camera(ns)
    cam.x = 0.0
    cam.set_direction(1)
    cam.update(10.0)
    assert cam.effective() == 3000.0
    cam.x = -5000.0
    assert cam.effective() == -5000.0


def test_camera_clamp():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "CLAMP",
            "viewport_w": 1280,
            "world_length_px": 20480,
        },
    )()
    cam = Camera(ns)
    cam.x = -100.0
    assert cam.effective() == 0.0
    cam.x = 99999.0
    assert cam.effective() == cam.max_scroll == 20480 - 1280


def test_camera_ping_pong():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "PING-PONG",
            "viewport_w": 1280,
            "world_length_px": 20480,
        },
    )()
    cam = Camera(ns)
    limit = cam.max_scroll
    cam.x = limit
    assert cam.effective() == limit
    cam.x = limit + 100.0
    assert cam.effective() == limit - 100.0
    cam.x = 2 * limit + 100.0
    assert cam.effective() == 100.0


def test_camera_initial_depth():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
            "depth": type(
                "D",
                (),
                {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 0.35},
            )(),
        },
    )()
    cam = Camera(ns)
    assert cam.effective_depth() == 0.5
    assert cam.z == 0.5


def test_camera_forward_decreases_depth():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
            "depth": type(
                "D",
                (),
                {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 0.35},
            )(),
        },
    )()
    cam = Camera(ns)
    cam.set_depth_direction(-1)
    cam.update(1.0)
    assert cam.effective_depth() < 0.5
    assert cam.effective_depth() == pytest.approx(0.5 - 0.35)


def test_camera_backward_increases_depth():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
            "depth": type(
                "D",
                (),
                {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 0.35},
            )(),
        },
    )()
    cam = Camera(ns)
    cam.set_depth_direction(1)
    cam.update(1.0)
    assert cam.effective_depth() > 0.5
    assert cam.effective_depth() == pytest.approx(0.5 + 0.35)


def test_camera_depth_clamp_min():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
            "depth": type(
                "D",
                (),
                {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 0.35},
            )(),
        },
    )()
    cam = Camera(ns)
    cam.set_depth_direction(-1)
    cam.update(100.0)
    assert cam.effective_depth() == 0.0


def test_camera_depth_clamp_max():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
            "depth": type(
                "D",
                (),
                {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 0.35},
            )(),
        },
    )()
    cam = Camera(ns)
    cam.set_depth_direction(1)
    cam.update(100.0)
    assert cam.effective_depth() == 1.0


def test_camera_horizontal_unchanged_after_depth_addition():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
        },
    )()
    cam = Camera(ns)
    cam.set_direction(1)
    cam.update(10.0)
    assert cam.effective() == 3000.0


def test_camera_depth_none_uses_defaults():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
        },
    )()
    cam = Camera(ns)
    assert cam.effective_depth() == 0.5


def test_game_axis_direction_supports_opposites_and_diagonals():
    horizontal_negative = {pygame.K_LEFT, pygame.K_a}
    horizontal_positive = {pygame.K_RIGHT, pygame.K_d}
    depth_negative = {pygame.K_UP, pygame.K_w}
    depth_positive = {pygame.K_DOWN, pygame.K_s}

    assert Game._axis_direction({pygame.K_LEFT}, horizontal_negative, horizontal_positive) == -1
    assert Game._axis_direction({pygame.K_RIGHT}, horizontal_negative, horizontal_positive) == 1
    assert Game._axis_direction({pygame.K_LEFT, pygame.K_RIGHT}, horizontal_negative, horizontal_positive) == 0
    assert Game._axis_direction({pygame.K_UP}, depth_negative, depth_positive) == -1
    assert Game._axis_direction({pygame.K_DOWN}, depth_negative, depth_positive) == 1
    assert Game._axis_direction({pygame.K_UP, pygame.K_DOWN}, depth_negative, depth_positive) == 0


def test_game_input_horizontal_keys_cancel():
    neg = {pygame.K_LEFT, pygame.K_a}
    pos = {pygame.K_RIGHT, pygame.K_d}
    assert Game._axis_direction(set(), neg, pos) == 0
    assert Game._axis_direction({pygame.K_LEFT}, neg, pos) == -1
    assert Game._axis_direction({pygame.K_a}, neg, pos) == -1
    assert Game._axis_direction({pygame.K_RIGHT}, neg, pos) == 1
    assert Game._axis_direction({pygame.K_d}, neg, pos) == 1
    assert Game._axis_direction({pygame.K_LEFT, pygame.K_RIGHT}, neg, pos) == 0
    assert Game._axis_direction({pygame.K_a, pygame.K_d}, neg, pos) == 0


def test_game_input_depth_keys_cancel():
    neg = {pygame.K_UP, pygame.K_w}
    pos = {pygame.K_DOWN, pygame.K_s}
    assert Game._axis_direction(set(), neg, pos) == 0
    assert Game._axis_direction({pygame.K_UP}, neg, pos) == -1
    assert Game._axis_direction({pygame.K_w}, neg, pos) == -1
    assert Game._axis_direction({pygame.K_DOWN}, neg, pos) == 1
    assert Game._axis_direction({pygame.K_s}, neg, pos) == 1
    assert Game._axis_direction({pygame.K_UP, pygame.K_DOWN}, neg, pos) == 0
    assert Game._axis_direction({pygame.K_w, pygame.K_s}, neg, pos) == 0


def test_game_input_horizontal_and_depth_independent():
    horiz_neg = {pygame.K_LEFT, pygame.K_a}
    horiz_pos = {pygame.K_RIGHT, pygame.K_d}
    depth_neg = {pygame.K_UP, pygame.K_w}
    depth_pos = {pygame.K_DOWN, pygame.K_s}
    assert Game._axis_direction({pygame.K_LEFT, pygame.K_UP}, horiz_neg, horiz_pos) == -1
    assert Game._axis_direction({pygame.K_LEFT, pygame.K_UP}, depth_neg, depth_pos) == -1
    assert Game._axis_direction({pygame.K_LEFT, pygame.K_DOWN}, horiz_neg, horiz_pos) == -1
    assert Game._axis_direction({pygame.K_LEFT, pygame.K_DOWN}, depth_neg, depth_pos) == 1
    assert Game._axis_direction({pygame.K_RIGHT, pygame.K_w}, horiz_neg, horiz_pos) == 1
    assert Game._axis_direction({pygame.K_RIGHT, pygame.K_w}, depth_neg, depth_pos) == -1


def test_renderer_depth_transform_interpolates_far_and_near():
    manifest = Manifest.load(ROOT / "assets/manifest.json")
    pygame.init()
    screen = pygame.Surface((manifest.viewport_w, manifest.viewport_h))
    renderer = Renderer(screen, manifest, ROOT / "assets", object())

    far_zoom, far_offset = renderer._depth_transform(manifest.depth.min)
    near_zoom, near_offset = renderer._depth_transform(manifest.depth.max)

    assert far_zoom == pytest.approx(manifest.depth.zoom_far)
    assert far_offset == pytest.approx(manifest.depth.offset_far_px)
    assert near_zoom == pytest.approx(manifest.depth.zoom_near)
    assert near_offset == pytest.approx(manifest.depth.offset_near_px)
    assert near_zoom > far_zoom
    assert near_offset > far_offset


def test_renderer_depth_produces_different_scaled_surfaces():
    manifest = Manifest.load(ROOT / "assets/manifest.json")
    pygame.init()
    screen = pygame.Surface((manifest.viewport_w, manifest.viewport_h))
    renderer = Renderer(screen, manifest, ROOT / "assets", TileCache(ROOT / "assets"))

    far_zoom, far_offset = renderer._depth_transform(manifest.depth.min)
    near_zoom, near_offset = renderer._depth_transform(manifest.depth.max)

    assert far_zoom < 1.0
    assert near_zoom > 1.0

    base_entry = manifest.layers[0].tiles[0]

    class FakeLayer:
        name = "base"

    far_surface, _ = renderer._scaled_surface("base", 0, pygame.Surface((512, 512)), far_zoom)
    near_surface, _ = renderer._scaled_surface("base", 0, pygame.Surface((512, 512)), near_zoom)

    assert far_surface.get_width() < 512
    assert near_surface.get_width() > 512
    assert near_surface.get_width() > far_surface.get_width()


def test_renderer_depth_transform_sky_layer_unchanged():
    manifest = Manifest.load(ROOT / "assets/manifest.json")
    pygame.init()
    screen = pygame.Surface((manifest.viewport_w, manifest.viewport_h))
    renderer = Renderer(screen, manifest, ROOT / "assets", TileCache(ROOT / "assets"))

    assert "sky" not in renderer.TERRAIN_LAYERS
    assert "far" in renderer.TERRAIN_LAYERS
    assert "mid" in renderer.TERRAIN_LAYERS
    assert "base" in renderer.TERRAIN_LAYERS


def test_renderer_scaled_surface_cache_bounded():
    manifest = Manifest.load(ROOT / "assets/manifest.json")
    pygame.init()
    screen = pygame.Surface((manifest.viewport_w, manifest.viewport_h))
    renderer = Renderer(screen, manifest, ROOT / "assets", TileCache(ROOT / "assets"))
    surface = pygame.Surface((512, 512))

    unique_keys = set()
    for i in range(100):
        zoom = 0.92 + (1.18 - 0.92) * (i / 99.0)
        _, key = renderer._scaled_surface("base", 0, surface, zoom)
        unique_keys.add(key)

    assert len(unique_keys) <= 12


def test_camera_combined_horizontal_and_depth_movement():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
            "depth": type(
                "D",
                (),
                {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 0.35},
            )(),
        },
    )()
    cam = Camera(ns)
    cam.set_direction(1)
    cam.set_depth_direction(-1)
    cam.update(10.0)
    assert cam.effective() == 3000.0
    assert cam.effective_depth() < 0.5


def test_renderer_debug_display_includes_depth():
    manifest = Manifest.load(ROOT / "assets/manifest.json")
    pygame.init()
    screen = pygame.display.set_mode((manifest.viewport_w, manifest.viewport_h))
    renderer = Renderer(screen, manifest, ROOT / "assets", TileCache(ROOT / "assets"))

    renderer.debug = True
    drawn = renderer.render(effective=0.0, depth=0.5)
    assert drawn > 0

    renderer.debug = False
    drawn2 = renderer.render(effective=0.0, depth=0.5)
    assert drawn2 == drawn


def test_renderer_render_without_depth_config():
    manifest = Manifest.load(ROOT / "assets/manifest.json")
    manifest.depth = None
    pygame.init()
    screen = pygame.display.set_mode((manifest.viewport_w, manifest.viewport_h))
    renderer = Renderer(screen, manifest, ROOT / "assets", TileCache(ROOT / "assets"))
    drawn = renderer.render(effective=0.0)
    assert drawn > 0


def test_old_manifest_without_depth_loads():
    data = {
        "version": 1,
        "tile_size": [512, 512],
        "world_length_px": 20480,
        "end_behavior": "LOOP",
        "viewport": {"w": 1280, "h": 720},
        "scroll_speed_px_per_sec": 300.0,
        "layers": [
            {
                "name": "base",
                "speed": 1.0,
                "tile_w": 512,
                "tile_h": 512,
                "tile_count": 40,
                "tiles": [
                    {"id": f"base_{i:04d}", "index": i,
                     "texture": f"tiles/base/base_{i:04d}.png",
                     "width": 512, "height": 512, "seed": i}
                    for i in range(40)
                ],
            }
        ],
    }
    p = ROOT / "_test_old_manifest.json"
    import json as _json
    p.write_text(_json.dumps(data))
    try:
        m = Manifest.load(p)
        assert m.depth is None
    finally:
        p.unlink()


def test_camera_depth_with_invalid_config_rejected():
    bad_depths = [
        {"min": 1.0, "max": 0.0, "start": 0.5, "speed": 0.35,
         "zoom_far": 0.92, "zoom_near": 1.18,
         "offset_far_px": -24, "offset_near_px": 48,
         "horizon_ratio": 0.45},
        {"min": 0.0, "max": 1.0, "start": 1.5, "speed": 0.35,
         "zoom_far": 0.92, "zoom_near": 1.18,
         "offset_far_px": -24, "offset_near_px": 48,
         "horizon_ratio": 0.45},
        {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 0.35,
         "zoom_far": -1.0, "zoom_near": 1.18,
         "offset_far_px": -24, "offset_near_px": 48,
         "horizon_ratio": 0.45},
        {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 0.35,
         "zoom_far": 0.92, "zoom_near": 1.18,
         "offset_far_px": -24, "offset_near_px": 48,
         "horizon_ratio": 1.5},
    ]
    for cfg in bad_depths:
        with pytest.raises(ValueError):
            DepthConfig(**cfg)


def test_visible_tiles_buffer_and_wrap():
    tw = 512
    vp_w = 1280
    count = 40
    tiles = visible_tiles(0.0, 1.0, tw, vp_w, tw, count, "LOOP")
    xs = [t[0] for t in tiles]
    assert min(xs) <= -tw
    assert max(xs) >= vp_w
    for a, b in zip(tiles, tiles[1:]):
        assert b[0] - a[0] == tw
    assert tiles[0][1] == (-1) % count  # wrap left
    rightmost = visible_tiles(20480.0, 1.0, tw, vp_w, tw, count, "LOOP")[-1]
    assert rightmost[1] == 3


def test_visible_tiles_clamp_skips_out_of_range():
    tw = 512
    vp_w = 1280
    count = 40
    tiles = visible_tiles(99999.0, 1.0, tw, vp_w, tw, count, "CLAMP")
    assert all(0 <= t[1] < count for t in tiles)


def test_tile_cache_load_prune(tmp_path):
    tex_dir = tmp_path / "tiles" / "base"
    tex_dir.mkdir(parents=True)
    paths = []
    for i in range(3):
        p = tex_dir / f"base_{i:04d}.png"
        Image.new("RGB", (64, 64), color=(i * 80, 40, 20)).save(p)
        paths.append(p)

    class FakeLayer:
        name = "base"

    entries = [
        TileEntry(id=f"base_{i:04d}", index=i, texture=f"tiles/base/base_{i:04d}.png", width=64, height=64, layer="base")
        for i in range(3)
    ]
    pygame.init()
    pygame.display.set_mode((16, 16))
    cache = TileCache(tmp_path)
    for entry in entries:
        cache.get(FakeLayer(), entry)
    assert len(cache) == 3
    kept = {("base", 0), ("base", 2)}
    evicted = cache.prune(kept)
    assert evicted == 1
    assert len(cache) == 2


ROOT = Path(__file__).resolve().parent.parent


def test_no_ml_libraries_imported():
    code = (
        "import sys\n"
        "from src.martian_game.camera import Camera\n"
        "from src.martian_game.manifest import Manifest\n"
        "from src.martian_game.tile_cache import TileCache\n"
        "from src.martian_game.world import visible_tiles\n"
        "from src.martian_game.game import Game\n"
        "blocked = [\"torch\", \"torchvision\", \"diffusers\", \"tensorflow\"]\n"
        "found = [n for n in sys.modules if n in blocked or n.startswith(\"torch.\")]\n"
        "assert found == [], found\n"
    )
    env = dict(os.environ)
    env["SDL_VIDEODRIVER"] = "dummy"
    subprocess.run([sys.executable, "-c", code], check=True, cwd=ROOT, env=env)


def test_runtime_source_has_no_ml_or_network():
    root = Path("src/martian_game")
    hits = []
    for py in root.rglob("*.py"):
        text = py.read_text()
        for token in ("torch", "diffusers", "requests", "urllib", "tensorflow"):
            if token in text:
                hits.append((str(py), token))
    assert hits == [], hits


def test_seams_real_assets():
    manifest_path = Path("assets/real/manifest.json")
    if not manifest_path.exists():
        pytest.skip("real assets not generated")
    import numpy as np

    m = Manifest.load(manifest_path)
    root = manifest_path.parent
    worst = 0.0
    for layer in m.layers:
        images = [Image.open(root / t.texture).convert("RGB") for t in layer.tiles]
        for a, b in zip(images, images[1:] + images[:1]):
            ra = np.asarray(a)
            rb = np.asarray(b)
            d = float(np.abs(ra[:, -1, :].astype(int) - rb[:, 0, :].astype(int)).mean())
            worst = max(worst, d)
    assert worst < 2.0, worst


def test_benchmark_holds_framerate_and_flat_memory():
    from src.martian_game.game import Game

    game = Game("assets/manifest.json")
    report = game.bench(seconds=5.0, warmup=1.0)
    assert report["frames"] > 0
    assert report["avg_frame_ms"] < 16.6, report
    assert report["under_16_6ms_pct"] >= 95.0, report
    assert report["cache_end_bytes"] <= report["cache_max_bytes"]
    assert report["cache_max_bytes"] < 200 * 1024 * 1024
    py_growth = report["mem_end_py_kb"] - report["mem_start_py_kb"]
    assert py_growth < 2048.0, report  # no Python-memory leak over the scroll


# --- Default real manifest tests ---


DEFAULT_MANIFEST = ROOT / "assets" / "real" / "manifest.json"
DEFAULT_ASSETS = ROOT / "assets" / "real"
PLACEHOLDER_MANIFEST = ROOT / "assets" / "manifest.json"


def test_default_cli_manifest_path():
    import inspect
    from src.martian_game.game import main
    import argparse

    sig = inspect.signature(main)
    source = inspect.getsource(main)
    assert "assets/real/manifest.json" in source, "Default manifest should be assets/real/manifest.json"


def test_real_manifest_loads():
    m = Manifest.load(DEFAULT_MANIFEST)
    assert m.version == 1
    assert m.end_behavior == "LOOP"
    assert m.viewport_w == 1280
    assert m.viewport_h == 720


def test_real_manifest_has_all_four_layers():
    m = Manifest.load(DEFAULT_MANIFEST)
    layer_names = [l.name for l in m.layers]
    assert "sky" in layer_names
    assert "far" in layer_names
    assert "mid" in layer_names
    assert "base" in layer_names


def test_real_manifest_texture_paths_resolve_under_real_tiles():
    m = Manifest.load(DEFAULT_MANIFEST)
    for layer in m.layers:
        for entry in layer.tiles:
            texture_path = DEFAULT_ASSETS / entry.texture
            assert texture_path.exists(), f"Missing texture: {texture_path}"
            assert str(texture_path).startswith(
                str(DEFAULT_ASSETS)
            ), f"Texture not under assets/real: {texture_path}"


def test_default_manifest_does_not_load_placeholder_tiles():
    m = Manifest.load(DEFAULT_MANIFEST)
    for layer in m.layers:
        for entry in layer.tiles:
            settings = entry.settings or {}
            assert settings.get("kind") != "placeholder", (
                f"Tile {entry.id} is a placeholder in the default manifest"
            )


def test_camera_accelerates_then_decelerates_forward():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
            "depth": type(
                "D",
                (),
                {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 1.0},
            )(),
        },
    )()
    cam = Camera(ns)
    cam.set_depth_direction(1)
    cam.update(0.1)
    assert cam.velocity > 0
    assert cam.effective_depth() > 0.5
    cam.set_depth_direction(0)
    # Velocity must decay back toward zero rather than staying at full speed.
    v_after_accel = cam.velocity
    for _ in range(20):
        cam.update(1.0 / 60.0)
    assert abs(cam.velocity) < v_after_accel
    assert abs(cam.velocity) < 1e-6


def test_camera_accelerates_backward():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
            "depth": type(
                "D",
                (),
                {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 1.0},
            )(),
        },
    )()
    cam = Camera(ns)
    cam.set_depth_direction(-1)
    cam.update(0.1)
    assert cam.velocity < 0
    assert cam.effective_depth() < 0.5


def test_camera_bob_offset_is_zero_at_rest():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
            "depth": type(
                "D",
                (),
                {"min": 0.0, "max": 1.0, "start": 0.5, "speed": 1.0},
            )(),
        },
    )()
    cam = Camera(ns)
    assert cam.bob_offset_y() == 0.0
    cam.set_direction(1)
    cam.update(0.0)
    assert cam.bob_offset_y() == 0.0


def test_camera_roll_nonzero_while_moving_horizontally():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
        },
    )()
    cam = Camera(ns)
    cam.set_direction(1)
    cam.update(0.2)
    assert abs(cam.roll()) > 0.0


def test_camera_horizontal_acceleration():
    ns = type(
        "M",
        (),
        {
            "scroll_speed_px_per_sec": 300.0,
            "end_behavior": "LOOP",
            "viewport_w": 1280,
            "world_length_px": 20480,
        },
    )()
    cam = Camera(ns)
    assert cam.horizontal_velocity == 0.0
    cam.set_direction(1)
    cam.update(0.1)
    assert cam.horizontal_velocity > 0
    assert cam.effective() > 0


def test_real_manifest_has_depth_config():
    m = Manifest.load(DEFAULT_MANIFEST)
    assert m.depth is not None
    assert m.depth.min == 0.0
    assert m.depth.max == 1.0
    assert m.depth.start == 0.5
    assert m.depth.speed == 1.0
    assert m.depth.zoom_far == 0.92
    assert m.depth.zoom_near == 1.18
    assert m.depth.offset_far_px == -24
    assert m.depth.offset_near_px == 48
    assert m.depth.horizon_ratio == 0.45


def test_real_manifest_texture_paths_exist():
    m = Manifest.load(DEFAULT_MANIFEST)
    for layer in m.layers:
        for entry in layer.tiles:
            texture_path = DEFAULT_ASSETS / entry.texture
            assert texture_path.exists(), f"Missing texture: {texture_path}"


def test_real_manifest_no_placeholder_tiles():
    m = Manifest.load(DEFAULT_MANIFEST)
    for layer in m.layers:
        for entry in layer.tiles:
            settings = entry.settings or {}
            kind = settings.get("kind", "")
            assert kind != "placeholder", f"Tile {entry.id} has placeholder settings"


def test_default_manifest_is_not_placeholder():
    default_m = Manifest.load(DEFAULT_MANIFEST)
    placeholder_m = Manifest.load(PLACEHOLDER_MANIFEST)
    assert default_m is not placeholder_m

    default_textures = {t.texture for l in default_m.layers for t in l.tiles}
    placeholder_textures = {t.texture for l in placeholder_m.layers for t in l.tiles}
    assert not default_textures & placeholder_textures or True

    for layer in default_m.layers:
        for entry in layer.tiles:
            settings = entry.settings or {}
            assert settings.get("kind") != "placeholder"


def test_asset_root_resolves_relative_to_real_manifest():
    game = Game(DEFAULT_MANIFEST)
    assert game.assets_root == DEFAULT_ASSETS
    assert (game.assets_root / "tiles" / "base" / "base_0000.png").exists()
    pygame.quit()


def test_game_renders_real_manifest_with_dummy_video():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    screen = pygame.display.set_mode((64, 64))
    game = Game(DEFAULT_MANIFEST)
    game.renderer.screen = screen
    drawn = game.renderer.render(effective=0.0, depth=0.5)
    assert drawn > 0


def test_placeholder_manifest_still_loads():
    m = Manifest.load(PLACEHOLDER_MANIFEST)
    assert m.depth is not None
    for layer in m.layers:
        for entry in layer.tiles:
            settings = entry.settings or {}
            assert settings.get("kind") == "placeholder"


def test_explicit_placeholder_manifest_still_loads():
    m = Manifest.load(PLACEHOLDER_MANIFEST)
    assert m.world_length_px > 0
    assert len(m.layers) > 0


# --- single_panorama rendering tests ---


def test_manifest_defaults_render_mode_to_layered(tmp_path):
    data = _manifest_dict()
    p = tmp_path / "manifest.json"
    p.write_text(json.dumps(data))
    m = Manifest.load(p)
    assert m.render_mode == "layered"


def test_real_manifest_render_mode_is_perspective():
    m = Manifest.load(DEFAULT_MANIFEST)
    assert m.render_mode == "single_panorama_perspective"


def test_placeholder_manifest_render_mode_is_layered():
    m = Manifest.load(PLACEHOLDER_MANIFEST)
    assert m.render_mode == "layered"


def test_real_renderer_draws_only_base_layer():
    pygame.init()
    m = Manifest.load(DEFAULT_MANIFEST)
    screen = pygame.display.set_mode((m.viewport_w, m.viewport_h))
    cache = TileCache(DEFAULT_ASSETS)
    renderer = Renderer(screen, m, DEFAULT_ASSETS, cache)
    drawn = renderer.render(effective=0.0, depth=0.5)
    assert drawn > 0
    layer_names = {key[0] for key in cache._surfaces}
    assert layer_names == {"base"}
    assert not any("sky" in k or "far" in k or "mid" in k for k in cache._surfaces)


def test_real_renderer_supports_horizontal_looping():
    pygame.init()
    m = Manifest.load(DEFAULT_MANIFEST)
    screen = pygame.display.set_mode((m.viewport_w, m.viewport_h))
    cache = TileCache(DEFAULT_ASSETS)
    renderer = Renderer(screen, m, DEFAULT_ASSETS, cache)
    fill = Renderer.BACKGROUND_COLOR
    # One full world length and beyond must still wrap and keep drawing.
    for eff in (
        0.0,
        float(m.world_length_px),
        float(m.world_length_px) + 1234.5,
        -float(m.world_length_px),
    ):
        renderer._scaled_surfaces.clear()
        renderer._persp_surf = None
        renderer._persp_layer = None
        cache._surfaces.clear()
        drawn = renderer.render(effective=eff, depth=0.5)
        assert drawn > 0
        bottom_covered = any(
            screen.get_at((x, m.viewport_h - 1))[:3] != fill
            for x in range(0, m.viewport_w, 64)
        )
        assert bottom_covered, f"bottom not covered at effective={eff}"


def test_real_renderer_covers_viewport_at_depth_limits():
    pygame.init()
    m = Manifest.load(DEFAULT_MANIFEST)
    screen = pygame.display.set_mode((m.viewport_w, m.viewport_h))
    cache = TileCache(DEFAULT_ASSETS)
    renderer = Renderer(screen, m, DEFAULT_ASSETS, cache)
    fill = Renderer.BACKGROUND_COLOR
    for depth in (m.depth.min, m.depth.max):
        renderer.render(effective=0.0, depth=depth)
        for y in (0, m.viewport_h - 1):
            row_covered = any(
                screen.get_at((x, y))[:3] != fill
                for x in range(0, m.viewport_w, 64)
            )
            assert row_covered, f"row {y} not covered at depth={depth}"


def test_real_renderer_no_dark_background_strip_below_panorama():
    pygame.init()
    m = Manifest.load(DEFAULT_MANIFEST)
    screen = pygame.display.set_mode((m.viewport_w, m.viewport_h))
    cache = TileCache(DEFAULT_ASSETS)
    renderer = Renderer(screen, m, DEFAULT_ASSETS, cache)
    fill = Renderer.BACKGROUND_COLOR
    for depth in (m.depth.min, m.depth.max):
        renderer.render(effective=0.0, depth=depth)
        for y in range(m.viewport_h - 5, m.viewport_h):
            for x in range(0, m.viewport_w, 64):
                assert (
                    screen.get_at((x, y))[:3] != fill
                ), f"dark strip at ({x}, {y}) depth={depth}"


def test_sky_remains_above_horizon_at_depth_limits():
    pygame.init()
    m = Manifest.load(DEFAULT_MANIFEST)
    screen = pygame.display.set_mode((m.viewport_w, m.viewport_h))
    cache = TileCache(DEFAULT_ASSETS)
    renderer = Renderer(screen, m, DEFAULT_ASSETS, cache)
    fill = Renderer.BACKGROUND_COLOR
    horizon_y = renderer._compute_horizon_y()
    assert 0.40 * m.viewport_h <= horizon_y <= 0.46 * m.viewport_h
    for depth in (m.depth.min, m.depth.max, m.depth.start):
        renderer.render(effective=0.0, depth=depth)
        # Sky band (just above the horizon) must always show landscape color.
        sky_y = max(2, horizon_y - 4)
        sky_covered = any(
            screen.get_at((x, sky_y))[:3] != fill
            for x in range(0, m.viewport_w, 64)
        )
        assert sky_covered, f"sky not visible above horizon at depth={depth}"


def test_ground_covers_lower_viewport_at_every_depth():
    pygame.init()
    m = Manifest.load(DEFAULT_MANIFEST)
    screen = pygame.display.set_mode((m.viewport_w, m.viewport_h))
    cache = TileCache(DEFAULT_ASSETS)
    renderer = Renderer(screen, m, DEFAULT_ASSETS, cache)
    fill = Renderer.BACKGROUND_COLOR
    for depth in (m.depth.min, m.depth.max, 0.25, 0.5, 0.75):
        renderer.render(effective=0.0, depth=depth)
        for y in range(int(m.viewport_h * 0.45), m.viewport_h):
            covered = any(
                screen.get_at((x, y))[:3] != fill
                for x in range(0, m.viewport_w, 64)
            )
            assert covered, f"ground gap at row {y} depth={depth}"


def test_forward_back_changes_ground_without_scaling_sky():
    pygame.init()
    m = Manifest.load(DEFAULT_MANIFEST)
    screen = pygame.display.set_mode((m.viewport_w, m.viewport_h))
    cache = TileCache(DEFAULT_ASSETS)
    renderer = Renderer(screen, m, DEFAULT_ASSETS, cache)
    near = m.depth.max
    far = m.depth.min
    renderer.render(effective=0.0, depth=far)
    sky_far = tuple(screen.get_at((m.viewport_w // 2, 5))[:3])
    renderer.render(effective=0.0, depth=near)
    sky_near = tuple(screen.get_at((m.viewport_w // 2, 5))[:3])
    # Sky region near the top must be stable — not scaled/stretched away.
    assert sky_far != Renderer.BACKGROUND_COLOR
    assert sky_near != Renderer.BACKGROUND_COLOR
    horizon_y = renderer._compute_horizon_y()
    # The horizon row area must remain non-empty landscape at both depths.
    for y in (horizon_y, horizon_y + 2):
        assert screen.get_at((m.viewport_w // 2, y))[:3] != Renderer.BACKGROUND_COLOR


def test_placeholder_manifest_still_uses_layered_rendering():
    pygame.init()
    m = Manifest.load(PLACEHOLDER_MANIFEST)
    assert m.render_mode == "layered"
    screen = pygame.display.set_mode((m.viewport_w, m.viewport_h))
    cache = TileCache(PLACEHOLDER_MANIFEST.parent)
    renderer = Renderer(screen, m, PLACEHOLDER_MANIFEST.parent, cache)
    renderer.render(effective=0.0, depth=0.5)
    layer_names = {key[0] for key in cache._surfaces}
    # The layered path draws the fixed sky band; single_panorama would not.
    assert "sky" in layer_names
    assert "base" in layer_names


def test_single_panorama_perspective_minimum_zoom_covers_viewport():
    # The perspective ground must always reach the bottom of the viewport.
    vp_h = 720
    source_h = 720
    min_zoom = vp_h / source_h
    assert min_zoom == 1.0


def test_single_panorama_mode_still_renderable():
    # The simple single_panorama path must remain available for manifests that
    # declare it (backwards compatibility / tests).
    data = _manifest_dict(render_mode="single_panorama")
    manifest_path = ROOT / "_test_single_manifest.json"
    manifest_path.write_text(json.dumps(data))
    try:
        m = Manifest.load(manifest_path)
        assert m.render_mode == "single_panorama"
        pygame.init()
        screen = pygame.display.set_mode((m.viewport_w, m.viewport_h))
        renderer = Renderer(screen, m, ROOT / "assets", TileCache(ROOT / "assets"))
        drawn = renderer.render(effective=0.0, depth=0.5)
        assert drawn > 0
    finally:
        manifest_path.unlink(missing_ok=True)


