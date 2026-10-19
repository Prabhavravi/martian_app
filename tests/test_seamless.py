"""Tests for seamless tiling."""

import numpy as np
from PIL import Image

from src.generate.seamless import make_seamless


def test_seamless_same_size_and_mode():
    img = Image.new("RGB", (256, 256), color=(100, 150, 200))
    seamless = make_seamless(img)
    assert seamless.size == (256, 256)
    assert seamless.mode == "RGB"


def test_seamless_edges_match():
    # Create a gradient image where left edge != right edge
    arr = np.zeros((64, 64, 3), dtype=np.uint8)
    arr[:, :, 0] = np.tile(np.arange(64, dtype=np.uint8).reshape(1, 64), (64, 1))
    img = Image.fromarray(arr, mode="RGB")

    seamless = make_seamless(img, blend_pct=0.25)

    # Left and right edges should now match closely
    left_edge = np.asarray(seamless)[0:64, 0, 0].astype(int)
    right_edge = np.asarray(seamless)[0:64, -1, 0].astype(int)
    diff = np.mean(np.abs(left_edge - right_edge))
    assert diff < 5, f"Left/right edges still differ by {diff}"

    top_edge = np.asarray(seamless)[0, 0:64, 0].astype(int)
    bottom_edge = np.asarray(seamless)[-1, 0:64, 0].astype(int)
    diff = np.mean(np.abs(top_edge - bottom_edge))
    assert diff < 5, f"Top/bottom edges still differ by {diff}"


def test_seamless_grayscale():
    img = Image.new("L", (128, 128), color=128)
    seamless = make_seamless(img)
    assert seamless.mode == "L"
    assert seamless.size == (128, 128)
