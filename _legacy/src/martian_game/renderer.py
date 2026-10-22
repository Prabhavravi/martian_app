from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFont

import pygame

from .world import visible_tiles


class Renderer:
    TERRAIN_LAYERS = frozenset({"far", "mid", "base"})
    BACKGROUND_COLOR = (20, 24, 30)
    SINGLE_PANORAMA_BASE_LAYER = "base"

    # Perspective rendering parameters for single_panorama_perspective mode.
    PERSPECTIVE_SCALE_H = 128
    PERSPECTIVE_GROUND_STRIP_H = 16
    PERSPECTIVE_NEAR_SCALE = 2.2
    PERSPECTIVE_FAR_SCALE = 1.0
    PERSPECTIVE_MIN_GROUND_Z = 0.25
    PERSPECTIVE_ZOOM_BUCKETS = 64

    # Camera motion effect parameters (subtle).
    BOBBLE_AMPLITUDE = 2.2
    ROLL_AMPLITUDE = 0.6
    DUST_COUNT = 18
    DUST_ALPHA = 80
    ROVER_HOOD_ALPHA = 120

    def __init__(self, screen, manifest, assets_root, cache) -> None:
        self.screen = screen
        self.manifest = manifest
        self.cache = cache
        self.cache_refill = False
        self.font = ImageFont.load_default()
        self.debug = False
        self.fps = 0.0
        self._scaled_surfaces = {}
        self._persp_surf = None
        self._persp_layer = None
        self._persp_strips = {}
        self._horizon_y = self._compute_horizon_y()
        # Camera motion state for subtle rover-driving effects.
        self._camera = None
        self._dust_particles = []
        self._dust_initialized = False
        self._cached_hood = None
        self._dust_sprite = None
        self._sky_strip = None

    def _compute_horizon_y(self) -> int:
        ratio = 0.45
        if self.manifest.depth is not None:
            ratio = self.manifest.depth.horizon_ratio
        vp_h = self.manifest.viewport_h
        return int(vp_h * ratio)

    def _horizon_ratio(self) -> float:
        if self.manifest.depth is not None:
            return self.manifest.depth.horizon_ratio
        return 0.45

    def _depth_transform(self, depth: float) -> tuple[float, float]:
        config = self.manifest.depth
        if config is None:
            return 1.0, 0.0
        span = config.max - config.min
        t = 0.5 if span <= 0 else (depth - config.min) / span
        t = max(0.0, min(1.0, t))
        zoom = config.zoom_far + (config.zoom_near - config.zoom_far) * t
        offset = config.offset_far_px + (config.offset_near_px - config.offset_far_px) * t
        return zoom, offset

    def _scaled_surface(self, layer_name: str, index: int, surface, zoom: float):
        zoom_bucket = round(zoom * 32.0) / 32.0
        key = (layer_name, index, zoom_bucket)
        scaled = self._scaled_surfaces.get(key)
        if scaled is None:
            size = (
                max(1, round(surface.get_width() * zoom_bucket)),
                max(1, round(surface.get_height() * zoom_bucket)),
            )
            scaled = pygame.transform.scale(surface, size)
            self._scaled_surfaces[key] = scaled
        return scaled, key

    def _find_layer(self, name: str):
        for layer in self.manifest.layers:
            if layer.name == name:
                return layer
        return None

    def _prune_scaled(self, needed_scaled: set) -> None:
        for key in list(self._scaled_surfaces):
            if key not in needed_scaled:
                del self._scaled_surfaces[key]

    def render(self, effective, depth: float | None = None, camera=None) -> int:
        vp_w, vp_h = self.screen.get_size()
        self._camera = camera
        self.screen.fill(self.BACKGROUND_COLOR)
        if depth is None:
            config = self.manifest.depth
            depth = config.start if config is not None else 0.5
        if self.manifest.render_mode == "single_panorama_perspective":
            drawn = self._render_single_panorama_perspective(effective, depth, vp_w, vp_h)
        elif self.manifest.render_mode == "single_panorama":
            drawn = self._render_single_panorama(effective, depth, vp_w, vp_h)
        else:
            drawn = self._render_layered(effective, depth, vp_w, vp_h)
        # Apply subtle camera motion effects (bob, roll) via a viewport
        # transform when a camera is available. These do not affect the sky
        # band which is drawn fixed; only the ground layer shifts.
        if camera is not None and self.manifest.render_mode == "single_panorama_perspective":
            self._apply_camera_effects(effective, depth, vp_w, vp_h, drawn)
        if self.debug:
            self._draw_debug(effective, depth, drawn)
        return drawn

    def _apply_camera_effects(self, effective, depth, vp_w, vp_h, drawn) -> None:
        # Subtle rover-camera effects: vertical bob, slight roll/sway during
        # horizontal movement, dust particles near the bottom, and a fixed
        # rover hood + shadow overlay. These are restrained and never obscure
        # the landscape.
        camera = self._camera
        bob_y = camera.bob_offset_y() if camera is not None else 0.0
        roll = camera.roll() if camera is not None else 0.0
        h_vel = camera.horizontal_velocity if camera is not None else 0.0
        depth_vel = camera.velocity if camera is not None else 0.0

        # Only apply effects when there is actual motion.
        motion = abs(h_vel) + abs(depth_vel)
        if motion > 0.1:
            self._draw_dust(vp_w, vp_h, effective, motion)
            self._draw_rover_hood_cast_shadow(vp_w, vp_h, bob_y, roll, h_vel)

    def _init_dust(self, vp_w: int, vp_h: int) -> None:
        import random
        if self._dust_initialized:
            return
        self._dust_particles = []
        for _ in range(self.DUST_COUNT):
            self._dust_particles.append(
                {
                    "x": random.uniform(0, vp_w),
                    "y": random.uniform(vp_h * 0.55, vp_h * 0.92),
                    "size": random.uniform(1, 3),
                }
            )
        self._dust_initialized = True

    def _draw_dust(self, vp_w: int, vp_h: int, effective: float, motion: float) -> None:
        # Dust particles near the bottom of the screen, drifting horizontally.
        # Subtle: low alpha, small sprites, only visible during movement.
        self._init_dust(vp_w, vp_h)
        speed_ratio = min(1.0, abs(motion) / 350.0)
        if speed_ratio < 0.05:
            return
        alpha = int(self.DUST_ALPHA * speed_ratio)
        if alpha < 10:
            return
        # Use a single pre-rendered dust sprite surface for efficiency.
        if not hasattr(self, '_dust_sprite') or self._dust_sprite is None:
            self._dust_sprite = pygame.Surface((3, 3), pygame.SRCALPHA)
            pygame.draw.circle(self._dust_sprite, (180, 140, 80, alpha), (1, 1), 1)
        drift = effective * 0.15
        for p in self._dust_particles:
            px = int((p["x"] - drift) % vp_w)
            py = int(p["y"])
            size = max(1, int(p["size"]))
            self.screen.blit(self._dust_sprite, (px, py))

    def _draw_rover_hood_cast_shadow(self, vp_w: int, vp_h: int, bob_y: float, roll: float, h_vel: float) -> None:
        # A subtle rover hood silhouette at the bottom-center of the screen and
        # a soft cast shadow, fixed to the camera. The hood is dark but
        # semi-transparent so it never obscures the landscape. Uses small
        # targeted surfaces to avoid expensive full-screen alpha blends.
        horizon_y = self._horizon_y
        ground_h = vp_h - horizon_y
        hood_w = max(20, vp_w // 4)
        hood_h = max(8, ground_h // 7)
        hood_x = (vp_w - hood_w) // 2
        sway = int(h_vel * 0.02 + roll * 2.0)
        hood_x += sway
        hood_y = vp_h - hood_h - 4 + int(bob_y)
        shadow_x = hood_x
        shadow_y = hood_y + hood_h
        shadow_w = hood_w
        shadow_h = max(3, hood_h // 3)

        # Cache the hood shape so we only redraw the small overlay each frame.
        if self._cached_hood is None:
            self._cached_hood = pygame.Surface((hood_w, max(hood_h + shadow_h + 4, 16)), pygame.SRCALPHA)
            pygame.draw.ellipse(
                self._cached_hood,
                (0, 0, 0, 60),
                pygame.Rect(0, hood_h, shadow_w, shadow_h),
            )
            pygame.draw.polygon(
                self._cached_hood,
                (10, 14, 20, self.ROVER_HOOD_ALPHA),
                [
                    (0, hood_h),
                    (hood_w, hood_h),
                    (hood_w - hood_w // 6, 0),
                    (hood_w // 6, 0),
                ],
            )
        # Only blit the small cached hood surface at the correct position.
        self.screen.blit(self._cached_hood, (hood_x, hood_y))

    def _world_to_source(self, layer, tex_index: int) -> pygame.Surface | None:
        by_index = {entry.index: entry for entry in layer.tiles}
        if tex_index not in by_index:
            return None
        entry = by_index[tex_index]
        self.cache_refill = True
        return self.cache.get(layer, entry)

    def _render_single_panorama_perspective(self, effective, depth, vp_w, vp_h) -> int:
        # The base tile is a complete opaque panorama with sky in the top
        # portion and ground in the bottom portion. We split it and render a
        # Mode 7-style perspective ground plane over a fixed sky band. The sky
        # never scales; the ground scales with depth so forward motion brings
        # the ground toward the rover and backward motion pushes it toward the
        # horizon.
        base_layer = self._find_layer(self.SINGLE_PANORAMA_BASE_LAYER)
        if base_layer is None:
            return 0

        # Fetch one representative base surface (all base tiles are identical
        # full panoramas; horizontal scrolling samples across them with wrapping).
        reference_surface = self._world_to_source(base_layer, 0)
        if reference_surface is None:
            return 0
        src_w = reference_surface.get_width()
        src_h = reference_surface.get_height()

        horizon_y = self._compute_horizon_y()
        sky_src_h = max(1, int(src_h * (horizon_y / vp_h)))
        ground_src_top = sky_src_h
        ground_src_h = max(1, src_h - ground_src_top)
        sky_dst_h = max(1, horizon_y)
        ground_dst_h = max(1, vp_h - horizon_y)

        # --- Sky: fixed band that scrolls slowly with horizontal movement only.
        # The sky is drawn directly onto the screen and never scaled, so it
        # remains visually stable as the rover drives forward/backward.
        needed = set()
        needed.add((base_layer.name, 0))
        drawn = self._render_sky_band(
            effective, base_layer, src_w, sky_src_h, sky_dst_h, vp_w, needed,
        )

        # --- Ground: Mode 7 perspective projection rendered at low resolution.
        # The ground region of the source is src_h - sky_src_h tall. We map
        # each screen row in the lower viewport to a source y and a per-row
        # horizontal scale that grows toward the bottom (near) and shrinks
        # toward the horizon (far). Forward/backward depth controls the near
        # scale.
        zoom, _ = self._depth_transform(depth)
        depth_scale = (zoom - self.PERSPECTIVE_FAR_SCALE) / (
            self.PERSPECTIVE_NEAR_SCALE - self.PERSPECTIVE_FAR_SCALE + 1e-9
        )
        depth_scale = max(0.0, min(1.0, depth_scale))
        near_scale_eff = self.PERSPECTIVE_FAR_SCALE + (
            self.PERSPECTIVE_NEAR_SCALE - self.PERSPECTIVE_FAR_SCALE
        ) * depth_scale
        near_scale_eff = max(near_scale_eff, self.PERSPECTIVE_MIN_GROUND_Z)

        scale_h = self.PERSPECTIVE_SCALE_H
        scale_w = max(1, round(vp_w * ground_src_h / scale_h))
        if self._persp_surf is None or self._persp_surf.get_size() != (scale_w, scale_h):
            self._persp_surf = pygame.Surface((scale_w, scale_h)).convert()
            self._persp_layer = pygame.Surface((scale_w, scale_h)).convert()
        self._persp_surf.fill(self.BACKGROUND_COLOR)

        # Cache per-strip scaled ground strips keyed by zoom bucket so the
        # expensive smoothscale only runs when depth (and thus the zoom) changes.
        zoom_bucket = round(zoom * self.PERSPECTIVE_ZOOM_BUCKETS)
        strips = self._persp_strips.get(zoom_bucket)
        n_strips = max(1, math.ceil(scale_h / self.PERSPECTIVE_GROUND_STRIP_H))
        if strips is None:
            strips = self._build_ground_strips(
                reference_surface, src_w, src_h,
                ground_src_top, ground_src_h, near_scale_eff,
                n_strips, scale_w, scale_h,
            )
            self._persp_strips[zoom_bucket] = strips
            if len(self._persp_strips) > self.PERSPECTIVE_ZOOM_BUCKETS * 2:
                oldest = sorted(self._persp_strips)[:-self.PERSPECTIVE_ZOOM_BUCKETS]
                for k in oldest:
                    del self._persp_strips[k]

        # Blit cached strips onto the low-res layer with per-strip horizontal
        # scroll (parallax: distant strips scroll slowly, near strips quickly),
        # then scale only the ground portion to the viewport's lower region.
        self._persp_layer.fill(self.BACKGROUND_COLOR)
        h_scroll_base = effective * base_layer.speed
        for i in range(len(strips)):
            scaled_strip, dst_strip_h = strips[i]
            frac = i / max(1, len(strips) - 1) if len(strips) > 1 else 1.0
            dst_y = i * dst_strip_h
            if dst_y >= scale_h:
                break
            # Parallax: distant strips scroll slowly, near strips quickly.
            h_scroll = h_scroll_base * (0.35 + 0.65 * frac)
            sw = scaled_strip.get_width()
            off_x = int(h_scroll) % sw
            band_w = self._persp_layer.get_width()
            x = -off_x
            while x < band_w:
                self._persp_layer.blit(scaled_strip, (x, dst_y))
                x += sw
            drawn += 1

        # Scale only the ground portion of the low-res surface to the viewport's
        # lower region. The sky (already drawn above) is untouched.
        final = pygame.transform.smoothscale(self._persp_layer, (vp_w, ground_dst_h))
        self.screen.blit(final, (0, horizon_y))
        self.cache.prune(needed)
        if self.debug:
            self._draw_debug(effective, depth, drawn)
        return drawn

    def _build_ground_strips(self, reference_surface, src_w, src_h,
                             ground_src_top, ground_src_h, near_scale_eff,
                             n_strips, scale_w, scale_h) -> list[tuple[pygame.Surface, int]]:
        # Pre-render each perspective ground strip at its scaled width. The
        # strips are cached per zoom bucket and reused every frame, so the
        # per-frame work is just blitting and the single final smoothscale.
        strips = []
        far_scale = self.PERSPECTIVE_FAR_SCALE
        dst_strip_h = self.PERSPECTIVE_GROUND_STRIP_H
        for i in range(n_strips):
            frac = i / max(1, n_strips - 1) if n_strips > 1 else 1.0
            dist = 1.0 - frac
            strip_scale = far_scale + (near_scale_eff - far_scale) * dist
            strip_scale = max(0.05, strip_scale)
            # Source row: distant strips sample from the top of the ground
            # region (near the horizon), near strips sample from the bottom.
            src_y = int(ground_src_top + ground_src_h * (1.0 - dist))
            src_y = max(0, min(src_h - 1, src_y))
            # Use a source row height proportional to the ground region so that
            # distant (compressed) strips sample a thin slice and near (stretched)
            # strips sample a thicker slice, giving natural perspective foreshortening.
            source_row_h = max(1, round(ground_src_h / max(1, n_strips) * (0.5 + 0.5 * strip_scale)))
            strip_src_h_src = min(source_row_h, src_h - src_y)
            strip_rect = pygame.Rect(0, src_y, src_w, strip_src_h_src)
            strip_surf = reference_surface.subsurface(strip_rect)
            # Scale relative to the low-res surface width so strips tile seamlessly.
            scaled_w = max(1, round(scale_w * strip_scale))
            scaled_h = dst_strip_h
            scaled_strip = pygame.transform.smoothscale(strip_surf, (scaled_w, scaled_h))
            strips.append((scaled_strip, dst_strip_h))
        return strips

    def _render_sky_band(self, effective, layer, src_w, sky_src_h, sky_dst_h, vp_w, needed) -> int:
        # Draw the sky band (top portion of the base panorama) as a seamless
        # horizontally scrolling strip. The sky is never scaled vertically, so
        # it stays stable while the rover moves forward/backward.
        #
        # The base tiles are horizontal segments of the full panorama: tile 0
        # covers world x [0, src_w), tile 1 covers [src_w, 2*src_w), etc. We
        # compose ALL tiles side-by-side into one wide sky strip (cached) and
        # then scroll it to fill the viewport width. Since the world loops,
        # every tile may be visible at some point, so we build the full strip
        # once and reuse it every frame.
        drawn = 0
        by_index = {entry.index: entry for entry in layer.tiles}

        # Build or reuse the full sky strip (all tiles composited horizontally).
        full_w = layer.tile_count * src_w
        if self._sky_strip is None or self._sky_strip.get_width() != full_w:
            self._sky_strip = pygame.Surface((full_w, sky_dst_h)).convert()
            for tex in range(layer.tile_count):
                entry = by_index.get(tex)
                if entry is None:
                    continue
                surface = self._world_to_source(layer, tex)
                if surface is None:
                    continue
                src_strip = surface.subsurface(pygame.Rect(0, 0, src_w, sky_src_h))
                dst_strip = pygame.transform.smoothscale(src_strip, (src_w, sky_dst_h))
                self._sky_strip.blit(dst_strip, (tex * src_w, 0))
                needed.add((layer.name, tex))

        sky_offset = int(effective * layer.speed) % full_w
        for ox in (sky_offset, sky_offset - full_w):
            if -full_w < ox < vp_w:
                self.screen.blit(self._sky_strip, (ox, 0))
                drawn += 1
        return drawn

    def _render_single_panorama(self, effective, depth, vp_w, vp_h) -> int:
        # In single-panorama mode the base layer is a complete, opaque full-frame
        # panorama: the sky, distant terrain and foreground are all baked into it.
        # Drawing the separate sky/far/mid layers would both be redundant and
        # (because they are opaque bands) visually wrong. Only the base layer is
        # drawn. The depth transform still drives a zoom, but it is clamped so the
        # scaled panorama always covers the full viewport height, and the image is
        # bottom-anchored to the viewport so no dark background can leak through at
        # the bottom when the rover moves backward toward the foreground.
        base_layer = self._find_layer(self.SINGLE_PANORAMA_BASE_LAYER)
        if base_layer is None:
            return 0
        source_h = base_layer.tile_h
        source_w = base_layer.tile_w
        min_zoom = vp_h / source_h if source_h > 0 else 1.0
        zoom, _ = self._depth_transform(depth)
        effective_zoom = max(zoom, min_zoom)

        needed = set()
        needed_scaled = set()
        drawn = 0
        by_index = {entry.index: entry for entry in base_layer.tiles}
        for screen_x, tex in visible_tiles(
            effective,
            base_layer.speed,
            source_w,
            vp_w,
            source_w,
            base_layer.tile_count,
            self.manifest.end_behavior,
        ):
            entry = by_index[tex]
            surface = self.cache.get(base_layer, entry)
            transformed, scaled_key = self._scaled_surface(
                self.SINGLE_PANORAMA_BASE_LAYER, entry.index, surface, effective_zoom
            )
            sx_ratio = transformed.get_width() / float(source_w)
            dest_x = screen_x * sx_ratio + (vp_w / 2.0) * (1.0 - sx_ratio)
            dest_y = vp_h - transformed.get_height()
            self.screen.blit(transformed, (round(dest_x), round(dest_y)))
            needed.add((base_layer.name, entry.index))
            needed_scaled.add(scaled_key)
            drawn += 1
        self.cache.prune(needed)
        self._prune_scaled(needed_scaled)
        if self.debug:
            self._draw_debug(effective, depth, drawn)
        return drawn

    def _render_layered(self, effective, depth, vp_w, vp_h) -> int:
        # Original layered rendering path, unchanged. Used by placeholder /
        # development manifests that do not opt into single-panorama rendering.
        needed = set()
        needed_scaled = set()
        drawn = 0
        config = self.manifest.depth
        zoom, offset = self._depth_transform(depth)
        horizon_y = vp_h * (config.horizon_ratio if config else 0.45)
        for layer in self.manifest.layers:
            by_index = {entry.index: entry for entry in layer.tiles}
            for screen_x, tex in visible_tiles(
                effective,
                layer.speed,
                layer.tile_w,
                vp_w,
                layer.tile_w,
                layer.tile_count,
                self.manifest.end_behavior,
            ):
                entry = by_index[tex]
                surface = self.cache.get(layer, entry)
                y = (vp_h - entry.height) // 2
                if layer.name in self.TERRAIN_LAYERS:
                    transformed, scaled_key = self._scaled_surface(
                        layer.name, entry.index, surface, zoom
                    )
                    tile_center_x = screen_x + surface.get_width() / 2.0
                    tile_center_y = y + surface.get_height() / 2.0
                    center_x = vp_w / 2.0 + (tile_center_x - vp_w / 2.0) * zoom
                    center_y = horizon_y + (tile_center_y - horizon_y) * zoom + offset
                    dest = (
                        round(center_x - transformed.get_width() / 2.0),
                        round(center_y - transformed.get_height() / 2.0),
                    )
                    self.screen.blit(transformed, dest)
                    needed_scaled.add(scaled_key)
                else:
                    self.screen.blit(surface, (screen_x, y))
                needed.add((layer.name, entry.index))
                drawn += 1
        self.cache.prune(needed)
        self._prune_scaled(needed_scaled)
        if self.debug:
            self._draw_debug(effective, depth, drawn)
        return drawn

    def _text_surface(self, text, size=20):
        img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default(size)
        bbox = draw.textbbox((0, 0), text, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        img = Image.new("RGBA", (w + 4, h + 4), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.text((2 - bbox[0], 2 - bbox[1]), text, font=font, fill=(255, 255, 255, 255))
        return pygame.image.fromstring(img.tobytes(), img.size, "RGBA").convert_alpha()

    def _draw_debug(self, effective, depth, drawn) -> None:
        lines = [
            f"{self.manifest.end_behavior[:3]} eff={effective:9.1f}",
            f"depth={depth:5.2f}",
            f"tiles={drawn} cached={len(self.cache)}",
            f"fps={self.fps:5.1f}",
        ]
        surf = self._text_surface("  |  ".join(lines), size=18)
        self.screen.blit(surf, (10, 10))
