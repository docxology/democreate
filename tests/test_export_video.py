"""Tests for the video/GIF export subsystem."""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError, RenderError
from democreate.export.video import (
    build_ffmpeg_command,
    export_video,
    frames_to_gif,
)


def _make_png(path: Path, color: tuple[int, int, int], size: int = 8) -> Path:
    from PIL import Image

    img = Image.new("RGB", (size, size), color)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, format="PNG")
    return path


# -- build_ffmpeg_command ---------------------------------------------------


def test_ffmpeg_command_silent(tmp_path: Path) -> None:
    out = tmp_path / "out.mp4"
    cmd = build_ffmpeg_command("frames/%05d.png", None, out, fps=24)
    assert cmd[0] == "ffmpeg"
    assert "frames/%05d.png" in cmd
    assert "libx264" in cmd
    assert "yuv420p" in cmd
    # framerate and -r both reflect fps
    assert cmd.count("24") == 2
    assert "-c:a" not in cmd
    assert cmd[-1] == str(out)


def test_ffmpeg_command_with_audio(tmp_path: Path) -> None:
    out = tmp_path / "out.mp4"
    cmd = build_ffmpeg_command("f/%05d.png", "narration.wav", out, fps=30)
    assert cmd.count("-i") == 2
    assert "narration.wav" in cmd
    assert "-c:a" in cmd
    assert "aac" in cmd
    assert "-shortest" in cmd


def test_ffmpeg_command_default_fps(tmp_path: Path) -> None:
    cmd = build_ffmpeg_command("f/%05d.png", None, tmp_path / "o.mp4")
    assert cmd.count("30") == 2


def test_ffmpeg_command_rejects_bad_fps(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        build_ffmpeg_command("f/%05d.png", None, tmp_path / "o.mp4", fps=0)


# -- frames_to_gif ----------------------------------------------------------


def test_frames_to_gif_happy(tmp_path: Path) -> None:
    frames = [
        _make_png(tmp_path / "f0.png", (255, 0, 0)),
        _make_png(tmp_path / "f1.png", (0, 255, 0)),
        _make_png(tmp_path / "f2.png", (0, 0, 255)),
    ]
    out = tmp_path / "anim" / "out.gif"
    result = frames_to_gif(frames, out, fps=5)
    assert result == out
    assert out.exists()

    from PIL import Image

    with Image.open(out) as img:
        assert img.format == "GIF"
        assert getattr(img, "n_frames", 1) == 3


def test_frames_to_gif_single_frame(tmp_path: Path) -> None:
    frame = _make_png(tmp_path / "only.png", (10, 20, 30))
    out = tmp_path / "single.gif"
    frames_to_gif([frame], out)
    assert out.exists()


def test_frames_to_gif_empty_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        frames_to_gif([], tmp_path / "o.gif")


def test_frames_to_gif_bad_fps_raises(tmp_path: Path) -> None:
    frame = _make_png(tmp_path / "f.png", (1, 2, 3))
    with pytest.raises(ValueError):
        frames_to_gif([frame], tmp_path / "o.gif", fps=-1)


def test_frames_to_gif_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(RenderError):
        frames_to_gif([tmp_path / "nope.png"], tmp_path / "o.gif")


def test_frames_to_gif_non_image_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.png"
    bad.write_text("not an image")
    with pytest.raises(RenderError):
        frames_to_gif([bad], tmp_path / "o.gif")


# -- export_video (guarded) -------------------------------------------------


def test_export_video_empty_frames_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        export_video([], None, tmp_path / "o.mp4")


def test_export_video_without_backend(tmp_path: Path, monkeypatch) -> None:
    import democreate.export.video as video_mod

    monkeypatch.setattr(video_mod, "_has_ffmpeg", lambda: False)
    monkeypatch.setattr(video_mod, "_has_moviepy", lambda: False)
    frame = _make_png(tmp_path / "00000.png", (0, 0, 0))
    with pytest.raises(BackendUnavailableError) as exc:
        export_video([frame], None, tmp_path / "o.mp4")
    assert exc.value.extra == "video"
