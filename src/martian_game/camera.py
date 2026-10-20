from __future__ import annotations


class Camera:
    def __init__(self, manifest) -> None:
        self.x = 0.0
        self.direction = 0
        self.speed = float(manifest.scroll_speed_px_per_sec)
        self.end_behavior = manifest.end_behavior
        self.viewport_w = manifest.viewport_w
        self.world_length = manifest.world_length_px

    @property
    def max_scroll(self) -> float:
        return max(0.0, float(self.world_length - self.viewport_w))

    def effective(self) -> float:
        x = self.x
        if self.end_behavior == "LOOP":
            return x
        limit = self.max_scroll
        if limit <= 0.0:
            return 0.0
        if self.end_behavior == "CLAMP":
            return min(max(x, 0.0), limit)
        period = 2.0 * limit
        t = x % period
        return t if t <= limit else 2.0 * limit - t

    def set_direction(self, direction: int) -> None:
        self.direction = direction

    def update(self, dt: float) -> None:
        self.x += self.direction * self.speed * dt
