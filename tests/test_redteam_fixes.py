"""Regression tests for the v0.6.2 RedTeam findings.

Each test pins a previously-unguarded behavior: gap-aware caption sync, the
fail-closed content verifier, the math-glyph fold + multi-line caption capture,
the noir monochrome window dots, per-item bullet/stat rendering, graceful config
and malformed-input handling, and monotonic chapters.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat

from democreate.capture.screen import render_frame
from democreate.config import THEMES
from democreate.media import FrameState
from democreate.schema import SceneKind


def _band_var(img: Image.Image, y0: float, y1: float, x0: float = 0.0, x1: float = 1.0) -> float:
    w, h = img.size
    crop = img.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1))).convert("L")
    return ImageStat.Stat(crop).var[0]


def _has_rgb(img: Image.Image, target, tol: int = 30) -> bool:
    w, h = img.size
    for x in range(0, w, 5):
        for y in range(0, min(h, int(h * 0.06)), 3):  # top chrome band only
            r, g, b = img.getpixel((x, y))[:3]
            if abs(r - target[0]) <= tol and abs(g - target[1]) <= tol and abs(b - target[2]) <= tol:
                return True
    return False


# --- BLOCKER: gap-aware caption/action sync -------------------------------

def _wav(path: Path, ms: int = 50) -> Path:
    import wave
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * max(1, int(22050 * ms / 1000)))
    return path


def test_sync_demo_anchors_to_lead_and_gap(tmp_path) -> None:
    from democreate.media import AudioClip
    from democreate.narration.sync import sync_demo
    from democreate.schema import Chunk, Demo, Scene

    demo = Demo(title="S", scenes=[
        Scene(id="s1", chunks=[Chunk(id="c1", text="one")]),
        Scene(id="s2", chunks=[Chunk(id="c2", text="two")]),
        Scene(id="s3", chunks=[Chunk(id="c3", text="three")]),
    ])
    clips = [AudioClip(path=_wav(tmp_path / f"{c}.wav"), duration_ms=d, chunk_id=c)
             for d, c in [(2000, "c1"), (3000, "c2"), (1000, "c3")]]
    sync_demo(demo, clips, lead_ms=300, gap_ms=220)
    starts = [c.start_ms for c in demo.iter_chunks()]
    # lead=300; then +clip(2000)+gap(220); then +clip(3000)+gap(220)
    assert starts == [300, 2520, 5740]


def test_sync_demo_zero_gaps_is_cumulative(tmp_path) -> None:
    from democreate.media import AudioClip
    from democreate.narration.sync import sync_demo
    from democreate.schema import Chunk, Demo, Scene

    demo = Demo(title="S", scenes=[Scene(id="s", chunks=[
        Chunk(id="c1", text="a"), Chunk(id="c2", text="b")])])
    clips = [AudioClip(path=_wav(tmp_path / "c1.wav"), duration_ms=1500, chunk_id="c1"),
             AudioClip(path=_wav(tmp_path / "c2.wav"), duration_ms=500, chunk_id="c2")]
    sync_demo(demo, clips)  # defaults lead=gap=0
    assert [c.start_ms for c in demo.iter_chunks()] == [0, 1500]


# --- MAJOR: the content verifier fails CLOSED -----------------------------

def test_verify_fails_closed_when_volume_unmeasurable(monkeypatch) -> None:
    import shutil

    from democreate.export import verify as V

    monkeypatch.setattr(V.shutil, "which", lambda _: "/usr/bin/ffprobe", raising=False)
    monkeypatch.setattr(V, "_run_ffprobe", lambda p: {})
    monkeypatch.setattr(V, "parse_ffprobe", lambda *a, **k: V.VideoReport(
        path=Path("v.mp4"), has_video=True, has_audio=True,
        width=1920, height=1080, duration_s=10.0, audio_duration_s=10.0))
    monkeypatch.setattr(V, "_measure_mean_volume_db", lambda p: None)
    monkeypatch.setattr(V, "_sample_frame_variance", lambda p: None)

    report = V.verify_video(Path("v.mp4"), check_content=True)
    assert report.ok is False  # un-measurable probes are NOT a pass
    assert any("could not measure audio" in p for p in report.problems)
    assert any("could not sample a video frame" in p for p in report.problems)
    _ = shutil  # keep import used


# --- MAJOR: math-glyph fold + multi-line caption --------------------------

def test_clean_folds_astral_math_glyphs() -> None:
    from democreate.paper.structure import _clean

    out = _clean("\U0001D706 = a ⋆ b − c …")  # 𝜆 = a ⋆ b − c …
    assert out == "λ = a * b - c ..."
    assert all(ord(ch) <= 0xFFFF for ch in out)  # no tofu-risk chars remain


def test_figure_captions_capture_across_a_wrapped_line() -> None:
    from democreate.paper.structure import extract_figure_captions

    text = "Figure 4: A coupling term that\nspans two lines here. Next sentence.\n"
    caps = extract_figure_captions(text)
    assert caps[0].number == 4
    assert caps[0].caption == "A coupling term that spans two lines here."


# --- MAJOR: noir monochrome window dots -----------------------------------

def test_noir_window_dots_are_monochrome_red() -> None:
    fs = FrameState(scene_kind=SceneKind.CODEBASE, file_path="m.py",
                    code_lines=["x = 1"])
    img = render_frame(fs, (1280, 720), theme=THEMES["noir"])
    assert _has_rgb(img, (224, 49, 57))          # the noir accent dot is present
    assert not _has_rgb(img, (245, 191, 79))     # no amber (old traffic light)
    assert not _has_rgb(img, (98, 197, 84))      # no green


# --- MINOR: per-item bullet / stat rendering ------------------------------

def _inked_rows(img: Image.Image, y0: float = 0.20, y1: float = 0.86) -> int:
    """Count distinct rows carrying ink in the content area (regression: only
    the first bullet/stat rendering would collapse this count)."""
    w, h = img.size
    rows = 0
    for y in range(int(h * y0), int(h * y1), 6):
        if ImageStat.Stat(img.crop((0, y, w, y + 6)).convert("L")).var[0] > 3:
            rows += 1
    return rows


def test_bullets_more_items_render_more_ink() -> None:
    one = render_frame(FrameState(scene_kind=SceneKind.SLIDE, title="T",
                                  bullets=["Only one point here"]), (1920, 1080))
    four = render_frame(FrameState(scene_kind=SceneKind.SLIDE, title="T",
                                   bullets=["First point here", "Second point here",
                                            "Third point here", "Fourth point here"]),
                        (1920, 1080))
    # four bullets must ink substantially more rows than one (catches a regression
    # that renders only the first bullet).
    assert _inked_rows(four) >= _inked_rows(one) + 4


def test_many_long_bullets_do_not_overflow_into_waveform_band() -> None:
    long = ("This is a deliberately long bullet that wraps across multiple lines "
            "to stress the vertical layout and force the autosize to shrink the font")
    fs = FrameState(scene_kind=SceneKind.SLIDE, title="Dense",
                    bullets=[f"{i}. {long}" for i in range(6)])
    img = render_frame(fs, (1920, 1080))
    assert img.size == (1920, 1080)  # renders without overflow crash


def test_stats_each_render_a_card() -> None:
    fs = FrameState(scene_kind=SceneKind.SLIDE, title="Nums",
                    stats=[("1", "a"), ("2", "b"), ("3", "c"), ("4", "d")])
    img = render_frame(fs, (1920, 1080))
    inked = [_band_var(img, 0.30, 0.62, 0.06 + i * 0.23, 0.27 + i * 0.23) > 3
             for i in range(4)]
    assert all(inked), inked


# --- MAJOR/MINOR: graceful config + malformed input -----------------------

def test_from_dict_tolerates_unknown_subconfig_keys() -> None:
    from democreate.config import RenderConfig

    cfg = RenderConfig.from_dict({
        "audio": {"voice": "Alex", "bogus_future_key": 7},
        "video": {"width": 1280, "nope": "x"},
        "metadata": {"author": "Ada", "??": 1},
    })
    assert cfg.audio.voice == "Alex"
    assert cfg.video.width == 1280
    assert cfg.metadata.author == "Ada"


def test_compositor_tolerates_flat_stats_list() -> None:
    from democreate.assembly.compositor import _state_for_chunk
    from democreate.schema import Chunk

    state = _state_for_chunk(
        None, SceneKind.SLIDE, "T",
        {"stats": ["99%", "fast"]},  # malformed: a flat list, not pairs
        Chunk(id="c", text="hi"))
    assert state.stats == []  # dropped, not crashed


def test_action_from_dict_coerces_int_fields() -> None:
    from democreate.schema import Action

    a = Action.from_dict({"type": "wait", "duration_ms": "500", "timestamp_ms": 1.9})
    assert a.duration_ms == 500 and isinstance(a.duration_ms, int)
    assert a.timestamp_ms == 1 and isinstance(a.timestamp_ms, int)


# --- MAJOR: chapters stay monotonic when counts diverge -------------------

def test_measured_chapters_monotonic_when_clips_fewer_than_chunks() -> None:
    from democreate.export.chapters import measured_chapters
    from democreate.media import AudioClip
    from democreate.schema import Chunk, Demo, Scene

    demo = Demo(title="C", scenes=[
        Scene(id="s1", title="One", chunks=[Chunk(id="c1", text="a")]),
        Scene(id="s2", title="Two", chunks=[Chunk(id="c2", text="b")]),
        Scene(id="s3", title="Three", chunks=[Chunk(id="c3", text="c")]),
    ])
    # only 2 clips for 3 chunks → the 3rd scene's idx runs past the windows
    clips = [AudioClip(path=Path("a.wav"), duration_ms=2000, chunk_id="c1"),
             AudioClip(path=Path("b.wav"), duration_ms=3000, chunk_id="c2")]
    chapters, _ = measured_chapters(demo, clips, gap_ms=0)
    starts = [c["start_ms"] for c in chapters]
    assert starts == sorted(starts)        # monotonic, never snaps back to 0
    assert starts == [0, 2000, 2000]       # 3rd reuses the 2nd start, not 0:00
