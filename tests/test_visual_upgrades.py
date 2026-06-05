"""Tests for the v0.3 visual upgrades: fonts, animator, richer renderer features."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest
from PIL import Image, ImageStat

from democreate.animation.fonts import load_font, resolve_font_path, scaled_font
from democreate.assembly.animator import (
    AnimationConfig,
    active_index_at,
    chunk_timing,
    render_animation_frames,
)
from democreate.capture.screen import (
    WAVEFORM_BAND_FRAC,
    render_frame,
    waveform_band_box,
)
from democreate.media import AudioClip, FrameState
from democreate.schema import SceneKind

# --- fonts ----------------------------------------------------------------

def test_load_font_returns_usable_font() -> None:
    f = load_font(48)
    # truetype fonts expose .size; bitmap fallback is still a valid font object
    assert f is not None


def test_scaled_font_scales_with_height() -> None:
    small = scaled_font(360, 0.05)
    big = scaled_font(1080, 0.05)
    # both load; if real truetype, the bigger frame yields a bigger font
    if hasattr(small, "size") and hasattr(big, "size"):
        assert big.size >= small.size


def test_resolve_font_path_returns_tuple_or_none() -> None:
    res = resolve_font_path()
    assert res is None or (isinstance(res, tuple) and len(res) == 2)
    mono = resolve_font_path(mono=True)
    assert mono is None or Path(mono[0]).exists()


# --- richer renderer features --------------------------------------------

def test_waveform_band_box_geometry() -> None:
    box = waveform_band_box(1920, 1080)
    assert box[0] == 0 and box[2] == 1920
    assert box[3] == 1080
    assert box[1] == 1080 - round(1080 * WAVEFORM_BAND_FRAC)


def test_render_slide_with_subtitle_and_section() -> None:
    fs = FrameState(
        scene_kind=SceneKind.SLIDE, title="DemoCreate",
        subtitle="Declarative Audio-Visual Demos", section="Intro",
    )
    img = render_frame(fs, (1280, 720))
    assert img.size == (1280, 720)
    assert ImageStat.Stat(img.convert("L")).var[0] > 5  # not blank


def test_render_browser_and_caption_wrap() -> None:
    fs = FrameState(
        scene_kind=SceneKind.WEBSITE, title="Dashboard", url="http://localhost:8000",
        caption="This is a deliberately long caption that must wrap across multiple "
        "lines so the lower third stays readable on a high definition frame.",
    )
    img = render_frame(fs, (1280, 720))
    assert img.size == (1280, 720)


def test_render_with_background_image(tmp_path: Path) -> None:
    bg = tmp_path / "bg.png"
    Image.new("RGB", (800, 600), (12, 80, 160)).save(bg)
    fs = FrameState(
        scene_kind=SceneKind.SLIDE, background_image=str(bg),
        caption="Real screenshot background.", section="Dashboard",
    )
    img = render_frame(fs, (1280, 720))
    assert img.size == (1280, 720)
    # the blue background should dominate the upper area
    px = img.getpixel((640, 200))
    assert px[2] > px[0]  # bluish


def test_render_missing_background_is_graceful(tmp_path: Path) -> None:
    fs = FrameState(scene_kind=SceneKind.SLIDE, background_image=str(tmp_path / "nope.png"))
    img = render_frame(fs, (640, 360))
    assert img.size == (640, 360)


# --- animator -------------------------------------------------------------

def test_chunk_timing_is_gap_free() -> None:
    clips = [
        AudioClip(path=Path("a.wav"), duration_ms=1000),
        AudioClip(path=Path("b.wav"), duration_ms=500),
        AudioClip(path=Path("c.wav"), duration_ms=750),
    ]
    windows, total = chunk_timing(clips)
    assert total == 2250
    assert windows == [(0, 1000), (1000, 1500), (1500, 2250)]
    # gap-free: each start equals previous end
    for (_s0, e0), (s1, _e1) in zip(windows, windows[1:], strict=False):
        assert e0 == s1


def test_active_index_at_boundaries() -> None:
    windows = [(0, 1000), (1000, 1500)]
    assert active_index_at(windows, 0) == 0
    assert active_index_at(windows, 999) == 0
    assert active_index_at(windows, 1000) == 1
    assert active_index_at(windows, 99999) == 1  # clamps to last
    assert active_index_at([], 50) == 0


def _mkwav(path: Path, ms: int, *, loud: bool = True) -> None:
    import struct

    n = int(22050 * ms / 1000)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        sample = 12000 if loud else 0
        w.writeframes(b"".join(struct.pack("<h", sample if i % 2 else -sample) for i in range(n)))


def test_render_animation_frames_produces_uniform_frames(tmp_path: Path) -> None:
    # two base frames + two clips + a voiceover wav
    base_dir = tmp_path / "frames"
    base_dir.mkdir()
    frames = []
    for i in range(2):
        p = base_dir / f"frame_{i:04d}.png"
        Image.new("RGB", (640, 360), (20, 20 + i * 40, 30)).save(p)
        frames.append(p)
    clips = [
        AudioClip(path=tmp_path / "a.wav", duration_ms=1000, chunk_id="c0"),
        AudioClip(path=tmp_path / "b.wav", duration_ms=1000, chunk_id="c1"),
    ]
    voice = tmp_path / "voice.wav"
    _mkwav(voice, 2000, loud=True)

    out_dir = tmp_path / "anim"
    written, total = render_animation_frames(
        frames, clips, voice, out_dir, size=(640, 360),
        config=AnimationConfig(fps=10, bars=60),
    )
    assert total == 2000
    assert len(written) == 20  # 2s * 10fps
    assert all(p.exists() for p in written)
    # a mid frame is a valid non-blank image of the right size
    mid = Image.open(written[10])
    assert mid.size == (640, 360)
    assert ImageStat.Stat(mid.convert("L")).var[0] > 0


def test_render_animation_frames_validates_inputs(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        render_animation_frames([], [], tmp_path / "v.wav", tmp_path / "o", size=(10, 10))
    # two frames but one clip → length-mismatch branch
    f1 = tmp_path / "f0.png"
    Image.new("RGB", (10, 10), (0, 0, 0)).save(f1)
    f2 = tmp_path / "f1.png"
    Image.new("RGB", (10, 10), (0, 0, 0)).save(f2)
    with pytest.raises(ValueError, match="must match"):
        render_animation_frames(
            [f1, f2], [AudioClip(path=f1, duration_ms=100)],
            tmp_path / "v.wav", tmp_path / "o", size=(10, 10),
        )
