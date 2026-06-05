"""Tests for audio-grounded video assembly (export.video new helpers)."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from democreate.export.video import (
    build_concat_demuxer_file,
    concat_wavs,
)


def _mkwav(path: Path, ms: int, *, rate: int = 22050, ch: int = 1, width: int = 2) -> None:
    n = int(rate * ms / 1000)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(width)
        w.setframerate(rate)
        w.writeframes(b"\x01\x02" * (n * ch))


def test_concat_wavs_sums_durations_gap_free(tmp_path: Path) -> None:
    from democreate.narration.tts import measure_wav_duration_ms

    _mkwav(tmp_path / "a.wav", 500)
    _mkwav(tmp_path / "b.wav", 300)
    _mkwav(tmp_path / "c.wav", 200)
    out = concat_wavs(
        [tmp_path / "a.wav", tmp_path / "b.wav", tmp_path / "c.wav"],
        tmp_path / "joined.wav",
    )
    assert out.exists()
    assert abs(measure_wav_duration_ms(out) - 1000) < 5


def test_concat_wavs_empty_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        concat_wavs([], tmp_path / "x.wav")


def test_concat_wavs_format_mismatch_raises(tmp_path: Path) -> None:
    _mkwav(tmp_path / "a.wav", 200, rate=22050)
    _mkwav(tmp_path / "b.wav", 200, rate=44100)  # different rate
    with pytest.raises(ValueError, match="mismatch"):
        concat_wavs([tmp_path / "a.wav", tmp_path / "b.wav"], tmp_path / "j.wav")


def test_build_concat_demuxer_holds_each_frame() -> None:
    txt = build_concat_demuxer_file(
        [(Path("/f/a.png"), 2.5), (Path("/f/b.png"), 1.0)]
    )
    assert txt.startswith("ffconcat version 1.0")
    assert "duration 2.500" in txt
    assert "duration 1.000" in txt
    # the last file is repeated so the concat demuxer honors its duration
    assert txt.count("file '") == 3


def test_build_concat_demuxer_no_repeat() -> None:
    txt = build_concat_demuxer_file([(Path("/f/a.png"), 1.0)], repeat_last=False)
    assert txt.count("file '") == 1


def test_build_concat_demuxer_rejects_empty_and_nonpositive() -> None:
    with pytest.raises(ValueError):
        build_concat_demuxer_file([])
    with pytest.raises(ValueError):
        build_concat_demuxer_file([(Path("/f/a.png"), 0.0)])


def test_build_concat_demuxer_quotes_paths_with_apostrophes() -> None:
    txt = build_concat_demuxer_file([(Path("/f/it's a frame.png"), 1.0)])
    assert r"'\''" in txt  # apostrophe POSIX-escaped


def test_assemble_video_validates_inputs(tmp_path: Path) -> None:
    from democreate.export.video import assemble_video

    with pytest.raises(ValueError):
        assemble_video([], [], None, tmp_path / "o.mp4")
    with pytest.raises(ValueError, match="same length"):
        assemble_video([tmp_path / "f.png"], [1, 2], None, tmp_path / "o.mp4")
