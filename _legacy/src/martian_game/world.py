from __future__ import annotations

import math


def visible_tiles(scroll, speed, tile_w, vp_w, buffer, tile_count, end_behavior):
    scroll = scroll * speed
    i_max = math.ceil((vp_w + buffer + scroll) / tile_w) - 1
    i_min = math.floor((scroll - buffer - tile_w) / tile_w) + 1
    tiles = []
    for i in range(i_min, i_max + 1):
        if end_behavior == "LOOP":
            tex = i % tile_count
        else:
            if i < 0 or i >= tile_count:
                continue
            tex = i
        screen_x = i * tile_w - scroll
        tiles.append((int(screen_x), tex))
    return tiles
