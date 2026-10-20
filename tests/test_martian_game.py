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
from src.martian_game.manifest import Manifest, TileEntry, Layer  # noqa: E402
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
