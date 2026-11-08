"""Tests for :mod:`democreate.assembly.audio`.

Exercises real PCM WAV silence/concat/measure helpers and, when available,
real FFmpeg normalization/fades, including legacy Python reader compatibility.
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
from democreate.errors import BackendUnavailableError, RenderError


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


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is unavailable")
@pytest.mark.parametrize("operation", ["normalize_audio", "apply_fade"])
def test_real_ffmpeg_write_failure_is_render_error(tmp_path: Path, operation: str) -> None:
    from democreate.assembly import audio

    source = _write_wav(tmp_path / "valid.wav", 250)
    original = source.read_bytes()
    destination = tmp_path / "unwritable.wav"
    destination.mkdir()
    with pytest.raises(RenderError):
        getattr(audio, operation)(source, destination)
    assert destination.is_dir()
    assert measure_duration_ms(source) == 250
    assert source.read_bytes() == original


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is unavailable")
@pytest.mark.parametrize(
    "sample_rate,channels", [(22050, 1), (44100, 2), (96000, 1), (44100, 3)]
)
def test_normalize_and_fade_preserve_pcm_timing_and_legacy_wav(
    tmp_path: Path, sample_rate: int, channels: int
) -> None:
    """A real tone survives both filters with Python 3.11-readable PCM headers."""
    import math
    import struct

    from democreate.assembly.audio import apply_fade, normalize_audio

    source = tmp_path / "tone.wav"
    frames = round(sample_rate / 2)
    samples = b"".join(
        struct.pack("<h", round(2000 * math.sin(2 * math.pi * 440 * frame / sample_rate)))
        * channels
        for frame in range(frames)
    )
    with wave.open(str(source), "wb") as output:
        output.setparams((channels, 2, sample_rate, 0, "NONE", "not compressed"))
        output.writeframes(samples)
    original = source.read_bytes()
    normalized = normalize_audio(source, tmp_path / "normalized.wav")
    faded = apply_fade(normalized, tmp_path / "faded.wav", fade_ms=80)
    for path in (normalized, faded):
        data = path.read_bytes()
        # Format tag 1 is standard PCM; tag 65534 is unreadable by Python 3.11.
        fmt_offset = data.index(b"fmt ") + 8
        assert struct.unpack_from("<H", data, fmt_offset)[0] == 1
        with wave.open(str(path), "rb") as audio:
            assert (audio.getnchannels(), audio.getsampwidth(), audio.getframerate()) == (
                channels, 2, sample_rate
            )
            assert abs(audio.getnframes() - frames) <= 1
        assert abs(measure_duration_ms(path) - 500) <= 1
    with wave.open(str(faded), "rb") as audio:
        values = [
            sample[0] for sample in struct.iter_unpack("<h", audio.readframes(frames))
        ]
    edge = values[: round(sample_rate * channels * 0.04)]
    middle = values[
        round(sample_rate * channels * 0.2): round(sample_rate * channels * 0.3)
    ]
    assert sum(value * value for value in middle) / len(middle) > 0
    assert sum(value * value for value in edge) / len(edge) < (
        sum(value * value for value in middle) / len(middle) / 2
    )
    assert source.read_bytes() == original


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is unavailable")
@pytest.mark.parametrize("operation", ["normalize_audio", "apply_fade"])
@pytest.mark.parametrize("payload", [b"", b"RIFF\x24\x00\x00\x00WAVEfmt "])
def test_truncated_wav_is_render_error_without_replacing_output(
    tmp_path: Path, operation: str, payload: bytes
) -> None:
    """Malformed media cannot bypass the rendering error or custody contract."""
    from democreate.assembly import audio

    source = tmp_path / "truncated.wav"
    source.write_bytes(payload)
    destination = tmp_path / "existing.wav"
    destination.write_bytes(b"previous complete output")
    with pytest.raises(RenderError):
        getattr(audio, operation)(source, destination)
    assert source.read_bytes() == payload
    assert destination.read_bytes() == b"previous complete output"
