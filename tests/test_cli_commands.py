"""CLI coverage for the render/paper/verify commands and input validation.

These were the largest untested surface in ``cli.py`` (the aggregate coverage
gate hid them at ~53%): ``render``, ``paper``, and ``verify`` had no direct CLI
invocation, the YAML demo-load branch was never exercised, and a typo'd
``--theme`` silently produced a wrong-shaped video. Real CliRunner invocations,
no mocks; the heavy paths skip cleanly when their system binary is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image
from typer.testing import CliRunner

from democreate.cli import app
from democreate.export.video import ffmpeg_available
from democreate.narration.tts import SystemTTSBackend

runner = CliRunner()

_needs_ffmpeg = pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg not installed")
_needs_voice = pytest.mark.skipif(
    not SystemTTSBackend().is_available(), reason="no system TTS voice (say/espeak)"
)


def _init(tmp_path: Path, name: str = "demo.json", fmt: str = "json") -> Path:
    path = tmp_path / name
    res = runner.invoke(app, ["init", str(path), "--format", fmt])
    assert res.exit_code == 0, res.stdout
    return path


def _one_page_pdf(path: Path) -> Path:
    """Write a real, poppler-readable one-page PDF via Pillow."""
    Image.new("RGB", (612, 792), "white").save(path, "PDF")
    return path


def test_inspect_yaml_demo(tmp_path: Path) -> None:
    """The YAML demo-load branch (cli `_load_demo`) was never read by a test."""
    demo = _init(tmp_path, "demo.yaml", fmt="yaml")
    res = runner.invoke(app, ["inspect", str(demo)])
    assert res.exit_code == 0, res.stdout
    assert "scenes" in res.stdout


def test_render_rejects_unknown_theme(tmp_path: Path) -> None:
    """A typo'd ``--theme`` must be rejected, not silently fall back to a default
    (the RedTeam silent-degradation finding). Validation happens before any
    encode, so this needs no ffmpeg."""
    demo = _init(tmp_path)
    res = runner.invoke(
        app, ["render", str(demo), "--theme", "nonexistent", "-o", str(tmp_path / "o")]
    )
    assert res.exit_code != 0, (
        "unknown --theme should be rejected, not silently default. "
        f"stdout={res.stdout!r}"
    )
    assert "nonexistent" in (res.stdout + str(res.exception or ""))


@_needs_ffmpeg
@_needs_voice
def test_render_then_verify_real_video(tmp_path: Path) -> None:
    """Full render path → a content-verified MP4. Backs ledger claims C9-C12
    (real, non-silent, non-black streams) with a runnable check rather than a
    stale manual ffprobe over a gitignored artifact."""
    demo = _init(tmp_path)
    out = tmp_path / "out"
    res = runner.invoke(
        app, ["render", str(demo), "-o", str(out), "--no-animate", "--resolution", "720p"]
    )
    assert res.exit_code == 0, res.stdout
    video = out / "video" / "demo.mp4"
    assert video.exists()
    verify = runner.invoke(app, ["verify", str(video), "--width", "1280", "--height", "720"])
    assert verify.exit_code == 0, verify.stdout
    assert json.loads(verify.stdout)["ok"] is True


@_needs_ffmpeg
def test_verify_rejects_nonvideo(tmp_path: Path) -> None:
    """`verify` on a non-video file must exit non-zero (guards the failure
    contract at the bottom of the command)."""
    not_video = tmp_path / "poster.png"
    Image.new("RGB", (64, 64), "black").save(not_video)
    res = runner.invoke(app, ["verify", str(not_video)])
    assert res.exit_code == 1


def test_paper_no_render_generates_demo(tmp_path: Path) -> None:
    """`paper <pdf> --no-render` builds a demo from a real PDF (poppler path),
    exercising the largest untested block in cli.py without ffmpeg/TTS."""
    pytest.importorskip("shutil")
    import shutil

    if not (shutil.which("pdfinfo") and shutil.which("pdftotext")):
        pytest.skip("poppler (pdfinfo/pdftotext) not installed")
    pdf = _one_page_pdf(tmp_path / "tiny.pdf")
    out = tmp_path / "out"
    res = runner.invoke(
        app, ["paper", str(pdf), "--no-render", "--pages", "1", "-o", str(out)]
    )
    assert res.exit_code == 0, res.stdout
    demo_json = out / "demos" / "paper.json"
    assert demo_json.exists(), f"expected {demo_json}; stdout={res.stdout}"
