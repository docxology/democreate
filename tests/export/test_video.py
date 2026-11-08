"""Tests for the video/GIF export subsystem."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError, RenderError
from democreate.export.video import (
    build_ffmpeg_command,
    encode_frame_sequence,
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


def test_ffmpeg_command_rejects_bad_fps(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        build_ffmpeg_command("f/%05d.png", None, tmp_path / "o.mp4", fps=0)


def test_ffmpeg_command_start_number(tmp_path: Path) -> None:
    """An explicit ``start_number`` lands before ``-i`` (an input option)."""
    cmd = build_ffmpeg_command(
        "frames/frame_%04d.png", None, tmp_path / "o.mp4", fps=24, start_number=0
    )
    idx = cmd.index("-start_number")
    assert cmd[idx + 1] == "0"
    assert cmd[idx + 3] == "frames/frame_%04d.png"


def test_ffmpeg_command_omits_start_number_by_default(tmp_path: Path) -> None:
    cmd = build_ffmpeg_command("f/%05d.png", None, tmp_path / "o.mp4")
    assert "-start_number" not in cmd


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


@pytest.mark.parametrize("exporter", [export_video, encode_frame_sequence])
def test_export_video_without_backend(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, exporter: Callable[..., Path]
) -> None:
    import democreate.export.video as video_mod

    monkeypatch.setattr(video_mod, "ffmpeg_available", lambda: False)
    frame = _make_png(tmp_path / "00000.png", (0, 0, 0))
    with pytest.raises(BackendUnavailableError) as exc:
        exporter([frame], None, tmp_path / "o.mp4")
    assert exc.value.backend == "ffmpeg"
    assert exc.value.extra is None


@pytest.mark.parametrize("exporter", [export_video, encode_frame_sequence])
@pytest.mark.parametrize(
    "names",
    [
        ["frame_0000.png", "frame_0002.png"],
        ["frame_0001.png", "frame_0000.png"],
        ["frame_0000.png", "frame_0000.png"],
        ["frame_0000.png", "other_0001.png"],
        ["frame_0000.png", "other/frame_0001.png"],
        ["cover.png"],
        ["percent%_0000.png"],
    ],
)
def test_numbered_exports_reject_noncontiguous_inputs(
    tmp_path: Path, exporter: Callable[..., Path], names: list[str]
) -> None:
    frames = [_make_png(tmp_path / name, (255, 0, 0)) for name in names]
    with pytest.raises(ValueError):
        exporter(frames, None, tmp_path / "out.mp4", fps=2)


@pytest.mark.parametrize("exporter", [export_video, encode_frame_sequence])
def test_numbered_exports_reject_missing_input(
    tmp_path: Path, exporter: Callable[..., Path]
) -> None:
    first = _make_png(tmp_path / "frame_0000.png", (255, 0, 0))
    with pytest.raises(RenderError):
        exporter([first, tmp_path / "frame_0001.png"], None, tmp_path / "out.mp4")


def _decoded_rgb(path: Path) -> bytes:
    """Decode actual encoded pixels, not command-line wiring."""
    import subprocess

    return subprocess.run(
        [
            "ffmpeg", "-v", "error", "-i", str(path),
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ],
        capture_output=True,
        check=True,
    ).stdout


@pytest.mark.parametrize("exporter", [export_video, encode_frame_sequence])
@pytest.mark.parametrize("count", [1, 2])
def test_native_numbered_exports_exclude_stale_neighbors(
    tmp_path: Path, exporter: Callable[..., Path], count: int
) -> None:
    from democreate.export.video import ffmpeg_available

    if not ffmpeg_available():
        pytest.skip("requires native ffmpeg with libx264")
    size = 32
    _make_png(tmp_path / "frame_0004.png", (255, 0, 255), size)
    frames = [
        _make_png(tmp_path / "frame_0005.png", (255, 0, 0), size),
        _make_png(tmp_path / "frame_0006.png", (0, 255, 0), size),
    ]
    _make_png(tmp_path / "frame_0007.png", (0, 0, 255), size)
    out = exporter(frames[:count], None, tmp_path / "out.mp4", fps=2)
    pixels = _decoded_rgb(out)
    bytes_per_frame = size * size * 3
    assert len(pixels) == count * bytes_per_frame
    for index in range(count):
        offset = index * bytes_per_frame + (size * (size // 2) + size // 2) * 3
        rgb = pixels[offset : offset + 3]
        assert rgb[index] > 200
        assert all(value < 30 for channel, value in enumerate(rgb) if channel != index)


def test_caption_request_rejects_unavailable_subtitle_filter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import democreate.export.video as video_mod

    if not video_mod.ffmpeg_available():
        pytest.skip("requires native ffmpeg")
    monkeypatch.setattr(video_mod, "_libass_available", lambda: False)
    frame = _make_png(tmp_path / "frame_0000.png", (0, 0, 0))
    captions = tmp_path / "captions.srt"
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nCAPTION\n", encoding="utf-8"
    )
    with pytest.raises(RenderError):
        encode_frame_sequence([frame], None, tmp_path / "out.mp4", captions=captions)


def test_native_frame_sequence_burns_literal_caption_path(tmp_path: Path) -> None:
    import democreate.export.video as video_mod

    if not video_mod.ffmpeg_available() or not video_mod._libass_available():
        pytest.skip("requires native ffmpeg with libass and a usable font")
    from PIL import Image

    frame = tmp_path / "frame_0000.png"
    Image.new("RGB", (320, 180), (0, 0, 0)).save(frame)
    captions = tmp_path / "captions's,[track];.srt"
    captions.write_text(
        "1\n00:00:00,000 --> 00:00:01,000\nCAPTION\n", encoding="utf-8"
    )
    plain = encode_frame_sequence([frame], None, tmp_path / "plain.mp4", fps=1)
    burned = encode_frame_sequence(
        [frame], None, tmp_path / "burned.mp4", fps=1, captions=captions
    )
    assert max(_decoded_rgb(plain)) < 10
    assert max(_decoded_rgb(burned)) > 100


def test_native_static_captions_change_inside_held_frame(tmp_path: Path) -> None:
    import democreate.export.video as video_mod

    if not video_mod.ffmpeg_available() or not video_mod._libass_available():
        pytest.skip("requires native ffmpeg with libass and a usable font")
    frame = _make_png(tmp_path / "held.png", (0, 0, 0), size=320)
    captions = tmp_path / "captions.srt"
    captions.write_text(
        "1\n00:00:00,300 --> 00:00:00,700\nCAPTION\n", encoding="utf-8"
    )
    output = video_mod.assemble_video(
        [frame], [1000], None, tmp_path / "held.mp4",
        fps=10, subtitles=captions, preset="ultrafast",
    )
    pixels = _decoded_rgb(output)
    frame_bytes = 320 * 320 * 3
    for index in (1, 8):
        assert max(pixels[index * frame_bytes : (index + 1) * frame_bytes]) < 10
    assert max(pixels[5 * frame_bytes : 6 * frame_bytes]) > 100
