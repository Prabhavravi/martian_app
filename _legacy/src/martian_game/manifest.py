from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

END_BEHAVIORS = ("LOOP", "CLAMP", "PING-PONG")
RENDER_MODES = ("layered", "single_panorama", "single_panorama_perspective")


@dataclass
class DepthConfig:
    min: float
    max: float
    start: float
    speed: float
    zoom_far: float
    zoom_near: float
    offset_far_px: float
    offset_near_px: float
    horizon_ratio: float

    def __post_init__(self) -> None:
        if not self.min < self.max:
            raise ValueError(f"depth.min ({self.min}) must be < depth.max ({self.max})")
        if not self.min <= self.start <= self.max:
            raise ValueError(f"depth.start ({self.start}) must be within [{self.min}, {self.max}]")
        if self.zoom_far <= 0:
            raise ValueError(f"depth.zoom_far ({self.zoom_far}) must be positive")
        if self.zoom_near <= 0:
            raise ValueError(f"depth.zoom_near ({self.zoom_near}) must be positive")
        if not 0.0 <= self.horizon_ratio <= 1.0:
            raise ValueError(f"depth.horizon_ratio ({self.horizon_ratio}) must be in [0, 1]")


@dataclass
class TileEntry:
    id: str
    index: int
    texture: str
    width: int
    height: int
    layer: str
    seed: int | None = None
    prompt: str | None = None
    settings: dict[str, Any] | None = None


@dataclass
class Layer:
    name: str
    speed: float
    tile_w: int
    tile_h: int
    tile_count: int
    tiles: list[TileEntry] = field(default_factory=list)

    @property
    def world_width(self) -> int:
        return self.tile_count * self.tile_w


@dataclass
class Manifest:
    version: int
    tile_size: tuple[int, int]
    world_length_px: int
    end_behavior: str
    viewport_w: int
    viewport_h: int
    scroll_speed_px_per_sec: float
    layers: list[Layer]
    depth: DepthConfig | None = None
    render_mode: str = "layered"

    @property
    def base_layer(self) -> Layer:
        return self.layers[0]

    @classmethod
    def load(cls, path: str | Path) -> "Manifest":
        with open(path) as f:
            data = json.load(f)
        end_behavior = str(data.get("end_behavior", "LOOP"))
        if end_behavior not in END_BEHAVIORS:
            raise ValueError(f"bad end_behavior: {end_behavior}")
        layers = []
        for layer_data in data["layers"]:
            tiles = [
                TileEntry(
                    id=t["id"],
                    index=int(t["index"]),
                    texture=t["texture"],
                    width=int(t["width"]),
                    height=int(t["height"]),
                    layer=layer_data["name"],
                    seed=t.get("seed"),
                    prompt=t.get("prompt"),
                    settings=t.get("settings"),
                )
                for t in layer_data.get("tiles", [])
            ]
            layers.append(
                Layer(
                    name=layer_data["name"],
                    speed=float(layer_data.get("speed", 1.0)),
                    tile_w=int(layer_data["tile_w"]),
                    tile_h=int(layer_data["tile_h"]),
                    tile_count=int(layer_data["tile_count"]),
                    tiles=tiles,
                )
            )
        viewport = data.get("viewport", {})
        render_mode = str(data.get("render_mode", "layered"))
        if render_mode not in RENDER_MODES:
            raise ValueError(f"bad render_mode: {render_mode}")
        depth_data = data.get("depth")
        depth = None
        if depth_data is not None:
            depth = DepthConfig(
                min=float(depth_data["min"]),
                max=float(depth_data["max"]),
                start=float(depth_data["start"]),
                speed=float(depth_data["speed"]),
                zoom_far=float(depth_data["zoom_far"]),
                zoom_near=float(depth_data["zoom_near"]),
                offset_far_px=float(depth_data["offset_far_px"]),
                offset_near_px=float(depth_data["offset_near_px"]),
                horizon_ratio=float(depth_data["horizon_ratio"]),
            )
        return cls(
            version=int(data.get("version", 1)),
            tile_size=(int(data["tile_size"][0]), int(data["tile_size"][1])),
            world_length_px=int(data["world_length_px"]),
            end_behavior=end_behavior,
            viewport_w=int(viewport.get("w", data.get("viewport_w", 1280))),
            viewport_h=int(viewport.get("h", data.get("viewport_h", 720))),
            scroll_speed_px_per_sec=float(data.get("scroll_speed_px_per_sec", 300.0)),
            layers=layers,
            depth=depth,
            render_mode=render_mode,
        )

    def save(self, path: str | Path) -> None:
        layers_out = []
        for layer in self.layers:
            tiles_out = []
            for t in layer.tiles:
                tiles_out.append(
                    {
                        "id": t.id,
                        "index": t.index,
                        "texture": t.texture,
                        "width": t.width,
                        "height": t.height,
                        "seed": t.seed,
                        "prompt": t.prompt,
                        "settings": t.settings,
                    }
                )
            layers_out.append(
                {
                    "name": layer.name,
                    "speed": layer.speed,
                    "tile_w": layer.tile_w,
                    "tile_h": layer.tile_h,
                    "tile_count": layer.tile_count,
                    "tiles": tiles_out,
                }
            )
        data = {
            "version": self.version,
            "tile_size": list(self.tile_size),
            "world_length_px": self.world_length_px,
            "end_behavior": self.end_behavior,
            "viewport": {"w": self.viewport_w, "h": self.viewport_h},
            "scroll_speed_px_per_sec": self.scroll_speed_px_per_sec,
            "depth": self._depth_to_dict() if self.depth is not None else None,
            "render_mode": self.render_mode,
            "layers": layers_out,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def _depth_to_dict(self) -> dict[str, Any] | None:
        if self.depth is None:
            return None
        return {
            "min": self.depth.min,
            "max": self.depth.max,
            "start": self.depth.start,
            "speed": self.depth.speed,
            "zoom_far": self.depth.zoom_far,
            "zoom_near": self.depth.zoom_near,
            "offset_far_px": self.depth.offset_far_px,
            "offset_near_px": self.depth.offset_near_px,
            "horizon_ratio": self.depth.horizon_ratio,
        }
