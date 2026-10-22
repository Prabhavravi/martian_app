from __future__ import annotations

import math


class Camera:
    def __init__(self, manifest) -> None:
        self.x = 0.0
        self.direction = 0
        self.target_direction = 0
        self.speed = float(manifest.scroll_speed_px_per_sec)
        self.end_behavior = manifest.end_behavior
        self.viewport_w = manifest.viewport_w
        self.world_length = manifest.world_length_px
        depth = getattr(manifest, "depth", None)
        if depth is not None:
            self._depth_min = depth.min
            self._depth_max = depth.max
            self._depth_start = depth.start
            self._depth_speed = depth.speed
        else:
            self._depth_min = 0.0
            self._depth_max = 1.0
            self._depth_start = 0.5
            self._depth_speed = 1.0
        self.z = self._depth_start
        self.depth_direction = 0
        self.target_depth_direction = 0
        self._accel = 8.0
        self._decel = 22.0
        self._horiz_accel = 8.0
        self._horiz_decel = 24.0
        self._velocity = 0.0
        self._horiz_velocity = 0.0
        self.time = 0.0

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

    def effective_depth(self) -> float:
        return self.z

    def set_direction(self, direction: int) -> None:
        self.direction = direction

    def set_depth_direction(self, direction: int) -> None:
        self.depth_direction = direction

    def set_depth(self, z: float) -> None:
        self.z = max(self._depth_min, min(self._depth_max, z))

    def _accelerate(self, current, target, accel, decel, dt) -> float:
        diff = target - current
        if abs(diff) < 1e-9:
            return 0.0
        rate = accel if diff > 0 else decel
        delta = diff * min(1.0, rate * dt)
        new_val = current + delta
        # Snap to rest once velocity is effectively zero to avoid lingering
        # micro-jitter in the idle camera.
        if abs(target) < 1e-9 and abs(new_val) < 1e-4:
            return 0.0
        return new_val

    @property
    def velocity(self) -> float:
        return self._velocity

    @property
    def horizontal_velocity(self) -> float:
        return self._horiz_velocity

    def update(self, dt: float) -> None:
        self.time += dt
        self._velocity = self._accelerate(
            self._velocity,
            float(self.depth_direction) * self._depth_speed,
            self._accel,
            self._decel,
            dt,
        )
        self.z = max(
            self._depth_min,
            min(self._depth_max, self.z + self._velocity * dt),
        )
        self._horiz_velocity = self._accelerate(
            self._horiz_velocity,
            float(self.direction) * self.speed,
            self._horiz_accel,
            self._horiz_decel,
            dt,
        )
        self.x += self._horiz_velocity * dt

    def bob_offset_y(self) -> float:
        speed = math.sqrt(self._velocity * self._velocity + self._horiz_velocity * self._horiz_velocity)
        if abs(speed) < 1e-6:
            return 0.0
        return 2.2 * math.sin(self.time * 22.0) * (speed / self.speed)

    def roll(self) -> float:
        if abs(self._horiz_velocity) < 1e-6:
            return 0.0
        return 1.5 * math.sin(self.time * 6.0) * (
            self._horiz_velocity / self.speed
        )
