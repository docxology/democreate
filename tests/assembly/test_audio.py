"""Tests for :mod:`democreate.assembly.audio`.

Exercises the pure standard-library silence/concat/measure helpers on real
temporary WAV files. The ffmpeg-backed paths (``normalize_audio``,
``apply_fade``) are guarded and never invoked here; we only assert that they
raise :class:`BackendUnavailableError` when the binary is absent.
"""

from __future__ import annotations

import shutil
import wave
from pathlib import Path

import pytest

from democreate.assembly.audio import (
    concat_with_gaps,
    ffmpeg_audio_available,
    measure_duration_ms,
    write_silence,
)
from democreate.errors import BackendUnavailableError


def _write_wav(
    path: Path,
    ms: int,
    *,
    sample_rate: int = 22050,
    channels: int = 1,
    sampwidth: int = 2,
) -> Path:
    """Write a real silent WAV of ``ms`` with explicit format parameters."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = max(1, round(sample_rate * ms / 1000))
    data = b"\x00" * (n_frames * sampwidth * channels)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(sampwidth)
        wav.setframerate(sample_rate)
        wav.writeframes(data)
    return path


def test_write_silence_creates_valid_wav(tmp_path: Path) -> None:
    out = write_silence(tmp_path / "sil.wav", 500, sample_rate=22050)
    assert out.exists()
    with wave.open(str(out), "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 22050
    assert abs(measure_duration_ms(out) - 500) <= 2


def test_write_silence_nonpositive_writes_one_frame(tmp_path: Path) -> None:
    out = write_silence(tmp_path / "tiny.wav", 0, sample_rate=22050)
    with wave.open(str(out), "rb") as wav:
        assert wav.getnframes() == 1
    out_neg = write_silence(tmp_path / "neg.wav", -100, sample_rate=22050)
    with wave.open(str(out_neg), "rb") as wav:
        assert wav.getnframes() == 1


def test_measure_duration_round_trips(tmp_path: Path) -> None:
    _write_wav(tmp_path / "a.wav", 750, sample_rate=16000)
    assert abs(measure_duration_ms(tmp_path / "a.wav") - 750) <= 2


def test_concat_durations_sum_with_gaps_lead_trail(tmp_path: Path) -> None:
    rate = 22050
    a = _write_wav(tmp_path / "a.wav", 300, sample_rate=rate)
    b = _write_wav(tmp_path / "b.wav", 400, sample_rate=rate)
    out = concat_with_gaps(
        [a, b],
        tmp_path / "out.wav",
        gap_ms=200,
        lead_ms=100,
        trail_ms=150,
    )
    expected = 300 + 400 + 200 + 100 + 150  # one gap between two clips
    assert abs(measure_duration_ms(out) - expected) <= 4
    # Format preserved.
    with wave.open(str(out), "rb") as wav:
        assert wav.getframerate() == rate
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2


def test_concat_no_gaps_is_plain_sum(tmp_path: Path) -> None:
    a = _write_wav(tmp_path / "a.wav", 250)
    b = _write_wav(tmp_path / "b.wav", 250)
    c = _write_wav(tmp_path / "c.wav", 250)
    out = concat_with_gaps([a, b, c], tmp_path / "joined.wav")
    assert abs(measure_duration_ms(out) - 750) <= 4


def test_concat_single_clip(tmp_path: Path) -> None:
    a = _write_wav(tmp_path / "a.wav", 500)
    out = concat_with_gaps([a], tmp_path / "one.wav", gap_ms=999, lead_ms=50)
    # gap_ms irrelevant with a single clip; lead applies.
    assert abs(measure_duration_ms(out) - 550) <= 4


def test_concat_uses_clip_format_for_silence(tmp_path: Path) -> None:
    rate = 8000
    a = _write_wav(tmp_path / "a.wav", 200, sample_rate=rate)
    b = _write_wav(tmp_path / "b.wav", 200, sample_rate=rate)
    out = concat_with_gaps([a, b], tmp_path / "out.wav", gap_ms=300)
    with wave.open(str(out), "rb") as wav:
        assert wav.getframerate() == rate
    assert abs(measure_duration_ms(out) - 700) <= 4


def test_concat_empty_list_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        concat_with_gaps([], tmp_path / "out.wav")


def test_concat_format_mismatch_raises(tmp_path: Path) -> None:
    a = _write_wav(tmp_path / "a.wav", 200, sample_rate=22050)
    b = _write_wav(tmp_path / "b.wav", 200, sample_rate=16000)
    with pytest.raises(ValueError):
        concat_with_gaps([a, b], tmp_path / "out.wav")


def test_concat_channel_mismatch_raises(tmp_path: Path) -> None:
    a = _write_wav(tmp_path / "a.wav", 200, channels=1)
    b = _write_wav(tmp_path / "b.wav", 200, channels=2)
    with pytest.raises(ValueError):
        concat_with_gaps([a, b], tmp_path / "out.wav")


def test_ffmpeg_audio_available_matches_which() -> None:
    assert ffmpeg_audio_available() == (shutil.which("ffmpeg") is not None)


@pytest.mark.skipif(
    shutil.which("ffmpeg") is not None,
    reason="ffmpeg present; guard cannot be exercised",
)
def test_normalize_audio_raises_without_ffmpeg(tmp_path: Path) -> None:
    from democreate.assembly.audio import normalize_audio

    src = _write_wav(tmp_path / "a.wav", 200)
    with pytest.raises(BackendUnavailableError):
        normalize_audio(src, tmp_path / "out.wav")


@pytest.mark.skipif(
    shutil.which("ffmpeg") is not None,
    reason="ffmpeg present; guard cannot be exercised",
)
def test_apply_fade_raises_without_ffmpeg(tmp_path: Path) -> None:
    from democreate.assembly.audio import apply_fade

    src = _write_wav(tmp_path / "a.wav", 200)
    with pytest.raises(BackendUnavailableError):
        apply_fade(src, tmp_path / "out.wav")
