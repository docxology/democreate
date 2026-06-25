"""Tests for content-asserting video verification (export.verify)."""

from __future__ import annotations

from pathlib import Path

from democreate.export.verify import VideoReport, parse_ffprobe


def _probe(width=1920, height=1080, vdur="10.0", adur="9.9", *, audio=True, video=True):
    streams = []
    if video:
        streams.append(
            {"codec_type": "video", "width": width, "height": height, "duration": vdur}
        )
    if audio:
        streams.append({"codec_type": "audio", "duration": adur})
    return {"streams": streams, "format": {"duration": vdur}}


def test_good_video_passes() -> None:
    r = parse_ffprobe(
        _probe(), path=Path("x.mp4"), expected_width=1920, expected_height=1080,
        min_duration_s=5,
    )
    assert r.ok
    assert r.has_video and r.has_audio
    assert r.width == 1920 and r.height == 1080


def test_missing_audio_is_flagged() -> None:
    r = parse_ffprobe(_probe(audio=False), path=Path("x.mp4"))
    assert not r.ok
    assert any("no audio" in p for p in r.problems)


def test_missing_video_is_flagged() -> None:
    r = parse_ffprobe(_probe(video=False), path=Path("x.mp4"))
    assert any("no video" in p for p in r.problems)


def test_wrong_dimensions_flagged() -> None:
    r = parse_ffprobe(
        _probe(width=1280, height=720), path=Path("x.mp4"),
        expected_width=1920, expected_height=1080,
    )
    assert any("width" in p for p in r.problems)
    assert any("height" in p for p in r.problems)


def test_short_duration_flagged() -> None:
    r = parse_ffprobe(_probe(vdur="0.3", adur="0.3"), path=Path("x.mp4"), min_duration_s=5)
    assert any("duration" in p for p in r.problems)


def test_audio_too_short_for_video_flagged() -> None:
    # video 10s, audio 2s — a near-silent/short track masquerading as full
    r = parse_ffprobe(_probe(vdur="10.0", adur="2.0"), path=Path("x.mp4"), min_duration_s=1)
    assert any("covers <" in p for p in r.problems)


def test_duration_falls_back_to_format() -> None:
    probe = {
        "streams": [
            {"codec_type": "video", "width": 1920, "height": 1080},
            {"codec_type": "audio"},
        ],
        "format": {"duration": "8.0"},
    }
    r = parse_ffprobe(probe, path=Path("x.mp4"), min_duration_s=5)
    assert r.duration_s == 8.0
    assert r.ok


def test_garbage_duration_coerces_to_zero() -> None:
    probe = {
        "streams": [{"codec_type": "video", "width": 10, "height": 10, "duration": "n/a"}],
        "format": {},
    }
    r = parse_ffprobe(probe, path=Path("x.mp4"), min_duration_s=1)
    assert r.duration_s == 0.0
    assert not r.ok  # zero duration + no audio


def test_report_to_dict_and_ok_property() -> None:
    r = VideoReport(path=Path("x.mp4"))
    assert r.ok is True  # no problems recorded yet
    r.problems.append("no video stream")
    assert r.ok is False
    d = r.to_dict()
    assert d["ok"] is False
    assert d["problems"] == ["no video stream"]
