"""Tests for elevation map generation."""

import tempfile
from pathlib import Path

from PIL import Image

from src.generate.pregenerate import derive_elevation


def test_elevation_grayscale_same_dims():
    with tempfile.TemporaryDirectory() as d:
        tex_path = Path(d) / "tex.png"
        elev_path = Path(d) / "elev.png"
        Image.new("RGB", (256, 256), color=(100, 150, 200)).save(tex_path)

        derive_elevation(tex_path, elev_path)

        assert elev_path.exists()
        elev = Image.open(elev_path).convert("L")
        assert elev.mode == "L"
        assert elev.size == (256, 256)
