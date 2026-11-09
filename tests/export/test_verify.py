"""Tests for content-asserting video verification (export.verify)."""

from __future__ import annotations

from pathlib import Path

import pytest

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


def test_verify_video_reports_missing_ffprobe(
    tmp_path: Path, monkeypatch,
) -> None:
    import pytest

    import democreate.export.verify as verify_mod
    from democreate.errors import BackendUnavailableError

    monkeypatch.setattr(verify_mod.shutil, "which", lambda _name: None)
    with pytest.raises(BackendUnavailableError) as exc:
        verify_mod.verify_video(tmp_path / "unused.mp4")
    assert exc.value.backend == "ffprobe"
    assert exc.value.extra is None


def test_verify_video_reports_missing_ffmpeg_even_with_ffprobe(
    tmp_path: Path, monkeypatch,
) -> None:
    import pytest

    import democreate.export.verify as verify_mod
    from democreate.errors import BackendUnavailableError

    original_which = verify_mod.shutil.which
    if original_which("ffprobe") is None:
        pytest.skip("requires native ffprobe to isolate missing ffmpeg")
    monkeypatch.setattr(
        verify_mod.shutil,
        "which",
        lambda name: None if name == "ffmpeg" else original_which(name),
    )
    with pytest.raises(BackendUnavailableError) as exc:
        verify_mod.verify_video(tmp_path / "unused.mp4", check_content=True)
    assert exc.value.backend == "ffmpeg"
    assert exc.value.extra is None


def _native_video(
    path: Path, *, duration: float = 0.3, silent: bool = False,
    blank: bool = False, start_s: int = 0, gop: int = 10,
) -> Path:
    """Create actual H.264/AAC content, not a probe-output substitute."""
    import shutil
    import subprocess

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("requires native ffmpeg/ffprobe with libx264 and AAC")
    video = (
        "color=c=black:size=160x90:rate=10" if blank
        else "testsrc2=size=160x90:rate=10"
    )
    audio = "anullsrc=r=48000:cl=mono" if silent else "sine=frequency=440"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", video, "-f", "lavfi", "-i", audio,
            "-t", str(duration), "-c:v", "libx264", "-preset", "ultrafast",
            "-threads", "1", "-g", str(gop), "-bf", "0", "-c:a", "aac",
            "-output_ts_offset", str(start_s), "-movflags", "+faststart", str(path),
        ],
        capture_output=True, check=True,
    )
    return path


@pytest.mark.parametrize("start_s", [0, 2])
def test_native_short_video_samples_inside_actual_interval(
    tmp_path: Path, start_s: int
) -> None:
    from democreate.export.verify import verify_video

    path = _native_video(tmp_path / "short.mp4", start_s=start_s)
    report = verify_video(path, min_duration_s=0.1)
    assert report.ok, report.problems
    assert report.frame_variance is not None and report.frame_variance > 5
    assert report.mean_volume_db is not None and report.mean_volume_db > -60


@pytest.mark.parametrize(
    ("silent", "blank", "minimum", "problem"),
    [(True, False, 0.1, "silent"), (False, True, 0.1, "blank"),
     (False, False, 1.0, "duration")],
)
def test_native_content_negative_controls_still_fail(
    tmp_path: Path, silent: bool, blank: bool, minimum: float, problem: str
) -> None:
    from democreate.export.verify import verify_video

    path = _native_video(tmp_path / "negative.mp4", silent=silent, blank=blank)
    report = verify_video(path, min_duration_s=minimum)
    assert not report.ok
    assert any(problem in reason for reason in report.problems), report.problems


def test_native_damaged_tail_fails_strict_existing_volume_decode(tmp_path: Path) -> None:
    import json
    import subprocess

    from democreate.export.verify import verify_video

    # Independent frames and a distant damaged suffix keep midpoint sampling
    # separate from full-stream rejection across native decoder versions.
    source = _native_video(tmp_path / "source.mp4", duration=6, gop=1)
    probe = json.loads(subprocess.run(
        [
            "ffprobe", "-v", "error", "-of", "json", "-show_packets",
            "-show_entries", "packet=codec_type,pos,size,pts_time", str(source),
        ],
        capture_output=True, text=True, check=True,
    ).stdout)
    data = bytearray(source.read_bytes())
    damaged = 0
    for packet in probe["packets"]:
        if packet["codec_type"] == "video" and float(packet["pts_time"]) >= 5.3:
            start, size = int(packet["pos"]), int(packet["size"])
            data[start : start + size] = bytes(size)
            damaged += 1
    assert damaged > 0
    path = tmp_path / "damaged-tail.mp4"
    path.write_bytes(data)
    strict = subprocess.run(
        [
            "ffmpeg", "-v", "error", "-xerror", "-err_detect", "explode",
            "-i", str(path), "-map", "0:v", "-f", "null", "-",
        ],
        capture_output=True, check=False,
    )
    assert strict.returncode != 0
    structural = verify_video(path, check_content=False)
    assert structural.ok, structural.problems
    assert structural.mean_volume_db is None and structural.frame_variance is None
    report = verify_video(path)
    assert not report.ok
    # The midpoint is intact: rejection must include the full strict decode,
    # rather than relying on a lucky corrupt sampled frame.
    assert report.frame_variance is not None and report.frame_variance > 5
    assert any("decode audio/video" in problem for problem in report.problems)


@pytest.mark.parametrize("duration", ["NaN", "Infinity", "-Infinity"])
def test_nonfinite_durations_do_not_pass_structure(duration: str) -> None:
    report = parse_ffprobe(
        _probe(vdur=duration, adur=duration), path=Path("invalid.mp4")
    )
    assert not report.ok
    assert report.duration_s == 0


@pytest.mark.parametrize("duration", ["0", "NaN"])
def test_zero_minimum_does_not_make_unknown_duration_valid(duration: str) -> None:
    report = parse_ffprobe(
        _probe(vdur=duration, adur=duration), path=Path("invalid.mp4"),
        min_duration_s=0,
    )
    assert not report.ok
    assert report.duration_s == 0
