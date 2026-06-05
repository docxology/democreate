"""Tests for the pure Pillow image effects."""

from __future__ import annotations

from PIL import Image

from democreate.assembly.effects import (
    crossfade,
    fade,
    highlight_box,
    lower_third,
)


def _solid(size=(64, 48), color=(200, 100, 50)) -> Image.Image:
    return Image.new("RGB", size, color)


def _mean_brightness(img: Image.Image) -> float:
    gray = img.convert("L")
    data = gray.tobytes()
    return sum(data) / len(data)


def test_fade_preserves_size() -> None:
    img = _solid()
    out = fade(img, 0.5)
    assert out.size == img.size


def test_fade_zero_is_darker_than_one() -> None:
    img = _solid()
    dark = fade(img, 0.0)
    bright = fade(img, 1.0)
    assert _mean_brightness(dark) < _mean_brightness(bright)
    # alpha 0 == fully black
    assert _mean_brightness(dark) == 0.0


def test_fade_clamps_out_of_range() -> None:
    img = _solid()
    over = fade(img, 5.0)
    under = fade(img, -3.0)
    assert _mean_brightness(over) == _mean_brightness(img)
    assert _mean_brightness(under) == 0.0


def test_crossfade_preserves_size_and_blends() -> None:
    a = _solid(color=(0, 0, 0))
    b = _solid(color=(255, 255, 255))
    mid = crossfade(a, b, 0.5)
    assert mid.size == a.size
    bm = _mean_brightness(mid)
    assert _mean_brightness(a) < bm < _mean_brightness(b)


def test_crossfade_endpoints() -> None:
    a = _solid(color=(0, 0, 0))
    b = _solid(color=(255, 255, 255))
    assert _mean_brightness(crossfade(a, b, 0.0)) == _mean_brightness(a)
    assert _mean_brightness(crossfade(a, b, 1.0)) == _mean_brightness(b)


def test_crossfade_resizes_mismatched_b() -> None:
    a = _solid(size=(64, 48), color=(0, 0, 0))
    b = _solid(size=(32, 24), color=(255, 255, 255))
    out = crossfade(a, b, 1.0)
    assert out.size == a.size


def test_highlight_box_preserves_size_and_changes_pixels() -> None:
    img = _solid(color=(10, 10, 10))
    before = img.tobytes()
    out = highlight_box(img, (5, 5, 50, 40), color=(255, 214, 0), width=4)
    assert out.size == img.size
    after = out.tobytes()
    assert before != after
    # the original image is untouched
    assert img.tobytes() == before
    # a pixel on the box edge should now carry the highlight color
    assert out.getpixel((5, 20)) == (255, 214, 0)


def test_lower_third_preserves_size_and_darkens_band() -> None:
    img = _solid(size=(120, 100), color=(200, 200, 200))
    out = lower_third(img, "Caption text", height=30)
    assert out.size == img.size
    # bottom band should be darker than the top region
    top = out.crop((0, 0, 120, 30))
    bottom = out.crop((0, 70, 120, 100))
    assert _mean_brightness(bottom) < _mean_brightness(top)


def test_lower_third_zero_height_is_noop_size() -> None:
    img = _solid(size=(64, 48))
    out = lower_third(img, "x", height=0)
    assert out.size == img.size


def test_lower_third_height_clamped_to_image() -> None:
    img = _solid(size=(64, 48))
    out = lower_third(img, "tall band", height=500)
    assert out.size == img.size
