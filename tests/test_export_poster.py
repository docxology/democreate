"""Tests for :mod:`democreate.export.poster`.

Real computation only: posters are actually rendered to temp PNGs and inspected
with Pillow's ``ImageStat``; GIF previews are built from real tiny PNG frames and
re-opened to verify frame counts. No mocks.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageStat

from democreate.config import THEMES, Theme
from democreate.export.poster import (
    _sample_indices,
    demo_to_gif,
    render_poster,
)
from democreate.schema import Demo


def _make_frame(path: Path, color: tuple[int, int, int], size=(32, 24)) -> Path:
    """Write a tiny solid-color PNG frame and return its path."""
    Image.new("RGB", size, color=color).save(path, format="PNG")
    return path


# --- render_poster --------------------------------------------------------


def test_render_poster_creates_png_of_requested_size(sample_demo: Demo, tmp_path: Path):
    out = tmp_path / "poster.png"
    result = render_poster(sample_demo, out, size=(960, 540))

    assert result == out
    assert out.exists()
    with Image.open(out) as img:
        assert img.format == "PNG"
        assert img.size == (960, 540)


def test_render_poster_is_not_uniformly_blank(sample_demo: Demo, tmp_path: Path):
    out = tmp_path / "poster.png"
    render_poster(sample_demo, out, size=(960, 540))

    with Image.open(out) as img:
        stat = ImageStat.Stat(img.convert("RGB"))
    # A blank fill has zero variance on every channel; drawn text/rule add variance.
    assert sum(stat.var) > 0


def test_render_poster_title_region_differs_from_background(
    sample_demo: Demo, tmp_path: Path
):
    theme = Theme()
    out = tmp_path / "poster.png"
    render_poster(sample_demo, out, size=(960, 540), theme=theme)

    with Image.open(out) as img:
        rgb = img.convert("RGB")
        w, h = rgb.size
        # Crop the vertical-center band where the title is composed.
        title_band = rgb.crop((0, int(h * 0.3), w, int(h * 0.7)))
        var = sum(ImageStat.Stat(title_band).var)
    bg = theme.bg_slide
    # The title band must contain pixels differing from the flat background.
    colors = title_band.getcolors(maxcolors=1_000_000) or []
    non_bg = [count for count, col in [(c[0], c[1]) for c in colors] if col != bg]
    assert var > 0
    assert sum(non_bg) > 0


def test_render_poster_default_subtitle_summarizes_demo(tmp_path: Path):
    # Distinct posters: a custom subtitle vs the generated default should differ.
    demo = Demo(title="My Tour")
    out_default = tmp_path / "default.png"
    out_custom = tmp_path / "custom.png"
    render_poster(demo, out_default, size=(640, 360))
    render_poster(demo, out_custom, size=(640, 360), subtitle="A custom tagline here")

    assert out_default.read_bytes() != out_custom.read_bytes()


def test_render_poster_accepts_preset_theme(sample_demo: Demo, tmp_path: Path):
    out_dark = tmp_path / "dark.png"
    out_paper = tmp_path / "paper.png"
    render_poster(sample_demo, out_dark, size=(640, 360), theme=THEMES["dark"])
    render_poster(sample_demo, out_paper, size=(640, 360), theme=THEMES["paper"])

    # Different themed backgrounds → different bytes.
    assert out_dark.read_bytes() != out_paper.read_bytes()


def test_render_poster_creates_parent_dirs(sample_demo: Demo, tmp_path: Path):
    out = tmp_path / "nested" / "dir" / "poster.png"
    render_poster(sample_demo, out, size=(320, 240))
    assert out.exists()


def test_render_poster_rejects_nonpositive_size(sample_demo: Demo, tmp_path: Path):
    with pytest.raises(ValueError):
        render_poster(sample_demo, tmp_path / "p.png", size=(0, 540))


def test_render_poster_handles_empty_title(tmp_path: Path):
    demo = Demo(title="   ")
    out = tmp_path / "p.png"
    render_poster(demo, out, size=(400, 300))
    assert out.exists()


# --- demo_to_gif ----------------------------------------------------------


def test_demo_to_gif_builds_multiframe_gif(tmp_path: Path):
    frames = [
        _make_frame(tmp_path / f"f{i}.png", color=(i * 50, 20, 200 - i * 30))
        for i in range(4)
    ]
    out = tmp_path / "preview.gif"
    result = demo_to_gif(frames, out, fps=8)

    assert result == out
    assert out.exists()
    with Image.open(out) as gif:
        assert gif.format == "GIF"
        assert getattr(gif, "n_frames", 1) > 1


def test_demo_to_gif_empty_raises(tmp_path: Path):
    with pytest.raises(ValueError):
        demo_to_gif([], tmp_path / "x.gif")


def test_demo_to_gif_caps_at_max_frames(tmp_path: Path):
    frames = [
        _make_frame(tmp_path / f"f{i:03d}.png", color=(i % 256, 0, 0))
        for i in range(100)
    ]
    out = tmp_path / "capped.gif"
    demo_to_gif(frames, out, fps=8, max_frames=10)

    with Image.open(out) as gif:
        assert getattr(gif, "n_frames", 1) <= 10
        assert getattr(gif, "n_frames", 1) > 1


def test_demo_to_gif_no_downsample_when_under_cap(tmp_path: Path):
    frames = [
        _make_frame(tmp_path / f"f{i}.png", color=(0, i * 40, 0)) for i in range(3)
    ]
    out = tmp_path / "small.gif"
    demo_to_gif(frames, out, fps=8, max_frames=48)

    with Image.open(out) as gif:
        assert getattr(gif, "n_frames", 1) == 3


def test_demo_to_gif_rejects_nonpositive_params(tmp_path: Path):
    frames = [_make_frame(tmp_path / "f0.png", color=(1, 2, 3))]
    with pytest.raises(ValueError):
        demo_to_gif(frames, tmp_path / "a.gif", max_frames=0)
    with pytest.raises(ValueError):
        demo_to_gif(frames, tmp_path / "b.gif", fps=0)


# --- _sample_indices ------------------------------------------------------


def test_sample_indices_includes_first_and_last():
    idx = _sample_indices(100, 10)
    assert idx[0] == 0
    assert idx[-1] == 99
    assert len(idx) <= 10
    # Strictly increasing and unique.
    assert idx == sorted(set(idx))


def test_sample_indices_passthrough_when_under_cap():
    assert _sample_indices(5, 48) == [0, 1, 2, 3, 4]


def test_sample_indices_single_frame_cap():
    assert _sample_indices(100, 1) == [0]
