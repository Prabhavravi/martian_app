from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import pygame

from .camera import Camera
from .manifest import Manifest
from .renderer import Renderer
from .tile_cache import TileCache


class Game:
    def __init__(self, manifest_path: str | Path, assets_root: str | Path | None = None) -> None:
        self.manifest = Manifest.load(manifest_path)
        self.assets_root = Path(assets_root) if assets_root is not None else Path(manifest_path).parent
        import os

        pygame.init()
        try:
            self.screen = pygame.display.set_mode(
                (self.manifest.viewport_w, self.manifest.viewport_h)
            )
        except pygame.error:
            os.environ["SDL_VIDEODRIVER"] = "dummy"
            pygame.quit()
            pygame.init()
            self.screen = pygame.display.set_mode(
                (self.manifest.viewport_w, self.manifest.viewport_h)
            )
        pygame.display.set_caption("Martian side scroller")
        self.clock = pygame.time.Clock()
        self.camera = Camera(self.manifest)
        self.cache = TileCache(self.assets_root)
        self.renderer = Renderer(self.screen, self.manifest, self.assets_root, self.cache)
        self.running = True
        self.direction = 0

    def handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    self.direction = -1
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.direction = 1
                elif event.key == pygame.K_SPACE:
                    self.renderer.debug = not self.renderer.debug
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_a, pygame.K_d):
                    self.direction = 0

    def update(self, dt: float) -> None:
        self.camera.set_direction(self.direction)
        self.camera.update(dt)

    def frame(self, dt: float) -> float:
        start = time.perf_counter()
        self.handle_events()
        if not self.running:
            return 0.0
        self.update(dt)
        effective = self.camera.effective()
        self.renderer.fps = self.clock.get_fps()
        self.renderer.render(effective)
        pygame.display.flip()
        return time.perf_counter() - start

    def run(self) -> None:
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.frame(dt)
        pygame.quit()

    def bench(self, seconds: float = 60.0, warmup: float = 2.0) -> dict:
        self.direction = 1
        tracemalloc.start()

        def cache_bytes() -> int:
            total = 0
            for surface in self.cache._surfaces.values():
                r = surface.get_rect()
                total += r.w * r.h * 3
            return total

        def rss_kb() -> int:
            try:
                import subprocess

                out = subprocess.check_output(
                    ["ps", "-o", "rss=", "-p", str(__import__("os").getpid())],
                    text=True,
                )
                return int(out.strip())
            except Exception:
                return -1

        # warmup: scroll without timing so tiles fault into the cache
        warm_deadline = time.perf_counter() + warmup
        while time.perf_counter() < warm_deadline:
            self.frame(self.clock.tick(60) / 1000.0)

        dt = 1.0 / 60.0
        times = []
        mem_samples = []
        deadline = time.perf_counter() + seconds
        frames = 0
        while time.perf_counter() < deadline:
            t0 = time.perf_counter()
            self.frame(dt)
            times.append(time.perf_counter() - t0)
            self.clock.tick(60)
            frames += 1
            if frames % 60 == 0:
                py_mem, _ = tracemalloc.get_traced_memory()
                mem_samples.append(
                    (py_mem, cache_bytes(), rss_kb(), len(self.cache))
                )
        pygame.quit()
        times.sort()
        worst = times[-1] if times else 0.0
        avg = sum(times) / len(times) if times else 0.0
        under = sum(1 for t in times if t < 1.0 / 60.0) / len(times) if times else 0.0
        report = {
            "frames": frames,
            "seconds": seconds,
            "avg_frame_ms": avg * 1000.0,
            "worst_frame_ms": worst * 1000.0,
            "p95_frame_ms": times[int(len(times) * 0.95)] * 1000.0 if times else 0.0,
            "under_16_6ms_pct": under * 100.0,
        }
        if mem_samples:
            report["mem_start_py_kb"] = mem_samples[0][0] / 1024.0
            report["mem_end_py_kb"] = mem_samples[-1][0] / 1024.0
            report["mem_max_py_kb"] = max(s[0] for s in mem_samples) / 1024.0
            report["cache_start_bytes"] = mem_samples[0][1]
            report["cache_end_bytes"] = mem_samples[-1][1]
            report["cache_max_bytes"] = max(s[1] for s in mem_samples)
            report["cache_tiles_end"] = mem_samples[-1][3]
            report["rss_start_kb"] = mem_samples[0][2]
            report["rss_end_kb"] = mem_samples[-1][2]
            report["rss_max_kb"] = max(s[2] for s in mem_samples)
        return report


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="assets/manifest.json")
    parser.add_argument("--assets", default=None)
    parser.add_argument("--bench", type=float, default=0.0)
    args = parser.parse_args()
    game = Game(args.manifest, args.assets)
    if args.bench > 0:
        report = game.bench(args.bench)
        for key, value in report.items():
            print(f"{key}: {value}")
    else:
        game.run()
