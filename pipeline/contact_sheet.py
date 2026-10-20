from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def _font(size=14):
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


def contact_sheet(out_dir, layer, tile_w, tile_h, count, thumb_w=384):
    out_dir = Path(out_dir)
    tile_dir = out_dir / "tiles" / layer["name"]
    paths = sorted(tile_dir.glob(f"{layer['name']}_*.png"))
    thumbs = []
    for p in paths:
        img = Image.open(p).convert("RGB")
        scale = thumb_w / float(tile_w)
        thumb_h = max(1, int(tile_h * scale))
        thumbs.append(img.resize((thumb_w, thumb_h)))
    cols = min(6, count)
    rows = (count + cols - 1) // cols
    gap = 6
    sheet_w = cols * thumb_w + (cols + 1) * gap
    sheet_h = rows * thumb_h + (rows + 1) * gap + 34
    sheet = Image.new("RGB", (sheet_w, sheet_h), (28, 28, 34))
    draw = ImageDraw.Draw(sheet)
    font = _font(16)
    draw.text((gap, gap), f"{layer['name']}  speed={layer['speed']}  tiles={count}  {tile_w}x{tile_h}", font=font, fill=(255, 255, 255))
    for i, thumb in enumerate(thumbs):
        r, c = divmod(i, cols)
        x = gap + c * (thumb_w + gap)
        y = 34 + gap + r * (thumb_h + gap)
        sheet.paste(thumb, (x, y))
        draw.rectangle([x, y, x + thumb_w - 1, y + thumb_h - 1], outline=(255, 0, 0), width=2)
        draw.text((x + 5, y + 5), f"{i:03d}", font=font, fill=(255, 255, 0))
    # Loop point: last tile right edge joins first tile left edge.
    x0 = gap
    y0 = 34 + gap
    x_last = gap + ((count - 1) % cols) * (thumb_w + gap) + thumb_w
    y_last = 34 + gap + ((count - 1) // cols) * (thumb_h + gap)
    draw.line([x0, y0, x0, y0 + thumb_h], fill=(255, 215, 0), width=5)
    draw.line([x_last, y_last, x_last, y_last + thumb_h], fill=(255, 215, 0), width=5)
    draw.text((x0 + 8, y0 + 8), "LOOP", font=font, fill=(255, 215, 0))
    draw.text((x_last - 40, y_last + thumb_h + 2), "LOOP <- last|first", font=font, fill=(255, 215, 0))
    out_path = out_dir / f"contact_sheet_{layer['name']}.png"
    sheet.save(out_path)
    return out_path
