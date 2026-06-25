"""Tests for the speech-waveform visualization module.

Real computation on real temporary WAV files and real PIL images — no mocks,
fully deterministic. We synthesize a loud tone and a silent buffer with the
stdlib :mod:`wave` module, then assert envelope shape/normalization and that the
rendered strips have actual visual variance.
"""

from __future__ import annotations

import math
import wave
from pathlib import Path

import pytest
from PIL import ImageStat

from democreate.animation.waveform import (
    compute_envelope,
    draw_waveform,
    render_waveform_strip,
)


def _write_wav(
    path: Path,
    samples: list[int],
    *,
    n_channels: int = 1,
    framerate: int = 16000,
) -> Path:
    """Write signed 16-bit PCM samples to ``path`` and return it."""
    import array

    data = array.array("h", samples)
    import sys

    if sys.byteorder == "big":  # pragma: no cover - host dependent
        data.byteswap()
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(n_channels)
        wav.setsampwidth(2)
        wav.setframerate(framerate)
        wav.writeframes(data.tobytes())
    return path


def _loud_samples(n: int = 16000) -> list[int]:
    """A loud sine wave as 16-bit samples."""
    out = []
    for i in range(n):
        out.append(int(20000 * math.sin(2 * math.pi * 220 * i / 16000)))
    return out


def test_compute_envelope_loud_peak_is_one(tmp_path: Path) -> None:
    wav = _write_wav(tmp_path / "loud.wav", _loud_samples())
    env = compute_envelope(wav, bars=32)
    assert len(env) == 32
    assert max(env) == pytest.approx(1.0)
    assert all(0.0 <= v <= 1.0 for v in env)
    assert any(v > 0.0 for v in env)


def test_compute_envelope_silent_all_zero(tmp_path: Path) -> None:
    wav = _write_wav(tmp_path / "silent.wav", [0] * 16000)
    env = compute_envelope(wav, bars=24)
    assert len(env) == 24
    assert env == [0.0] * 24


def test_compute_envelope_stereo_averaged(tmp_path: Path) -> None:
    # Interleave loud-left / silent-right; should still produce energy.
    mono = _loud_samples(8000)
    interleaved: list[int] = []
    for s in mono:
        interleaved.append(s)
        interleaved.append(0)
    wav = _write_wav(tmp_path / "stereo.wav", interleaved, n_channels=2)
    env = compute_envelope(wav, bars=16)
    assert len(env) == 16
    assert max(env) == pytest.approx(1.0)


def test_compute_envelope_short_audio_padded(tmp_path: Path) -> None:
    # Fewer samples than bars: empty buckets pad with 0.0 (graceful).
    wav = _write_wav(tmp_path / "short.wav", [10000, -10000, 10000])
    env = compute_envelope(wav, bars=10)
    assert len(env) == 10
    assert max(env) == pytest.approx(1.0)
    # Most buckets receive no samples and stay at the zero pad.
    assert env.count(0.0) >= 7


def test_compute_envelope_empty_audio(tmp_path: Path) -> None:
    wav = _write_wav(tmp_path / "empty.wav", [])
    env = compute_envelope(wav, bars=8)
    assert env == [0.0] * 8


def test_compute_envelope_raises_on_nonpositive_bars(tmp_path: Path) -> None:
    wav = _write_wav(tmp_path / "any.wav", _loud_samples(100))
    with pytest.raises(ValueError):
        compute_envelope(wav, bars=0)
    with pytest.raises(ValueError):
        compute_envelope(wav, bars=-3)


def test_render_waveform_strip_size_and_not_blank() -> None:
    env = [0.2, 0.5, 1.0, 0.7, 0.3, 0.9, 0.1, 0.6]
    img = render_waveform_strip(env, (320, 80))
    assert img.size == (320, 80)
    assert img.mode == "RGB"
    # Variance > 0 means the image is not a uniform fill.
    stat = ImageStat.Stat(img)
    assert sum(stat.var) > 0.0


def test_render_progress_changes_pixels() -> None:
    env = [0.5] * 20
    img0 = render_waveform_strip(env, (200, 60), progress=0.0)
    img1 = render_waveform_strip(env, (200, 60), progress=1.0)
    assert img0.tobytes() != img1.tobytes()


def test_render_empty_envelope_is_blank_background() -> None:
    bg = (15, 18, 26)
    img = render_waveform_strip([], (50, 40), bg=bg)
    assert img.size == (50, 40)
    # No-op draw: every pixel is the background color (zero variance).
    stat = ImageStat.Stat(img)
    assert sum(stat.var) == pytest.approx(0.0)
    assert img.getpixel((10, 10)) == bg


def test_render_tiny_size_does_not_crash() -> None:
    img = render_waveform_strip([1.0, 0.5], (1, 1))
    assert img.size == (1, 1)


def test_draw_waveform_noop_on_empty_box() -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (40, 40), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Degenerate box: no-op, no exception.
    draw_waveform(draw, (10, 10, 10, 10), [1.0, 0.5])
    stat = ImageStat.Stat(img)
    assert sum(stat.var) == pytest.approx(0.0)


def test_draw_waveform_bars_stay_within_box() -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (100, 100), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    box = (20, 20, 80, 80)
    # Over-unity amplitudes must be clamped inside the box.
    draw_waveform(draw, box, [5.0, 5.0, 5.0, 5.0], progress=0.5)
    # Pixels outside the box stay background-black.
    assert img.getpixel((5, 5)) == (0, 0, 0)
    assert img.getpixel((90, 90)) == (0, 0, 0)
    # Something was drawn inside the box.
    region = img.crop(box)
    assert sum(ImageStat.Stat(region).var) > 0.0


def test_draw_waveform_played_vs_unplayed_colors() -> None:
    from PIL import Image, ImageDraw

    img = Image.new("RGB", (200, 60), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    played = (80, 200, 255)
    unplayed = (90, 110, 130)
    draw_waveform(
        draw,
        (0, 0, 200, 60),
        [1.0] * 20,
        progress=0.5,
        bar_color=unplayed,
        played_color=played,
    )
    colors = {c for _, c in img.getcolors(maxcolors=100000)}
    assert played in colors
    assert unplayed in colors
