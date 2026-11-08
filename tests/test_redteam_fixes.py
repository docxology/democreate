"""Regression tests for the v0.6.2 RedTeam findings.

Behavioral regressions cover gap-aware synchronization, fail-closed native
content probes, text normalization, card rendering and monotonic chapters.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageStat

from democreate.capture.screen import render_frame
from democreate.media import FrameState
from democreate.schema import SceneKind


def _band_var(img: Image.Image, y0: float, y1: float, x0: float = 0.0, x1: float = 1.0) -> float:
    w, h = img.size
    crop = img.crop((int(w * x0), int(h * y0), int(w * x1), int(h * y1))).convert("L")
    return ImageStat.Stat(crop).var[0]




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

def test_verify_rejects_undecodable_payload_with_valid_container(tmp_path) -> None:
    import shutil
    import subprocess

    import pytest

    from democreate.export import verify as verification

    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None or shutil.which("ffprobe") is None:
        pytest.skip("requires native ffmpeg and ffprobe")
    video = tmp_path / "real.mp4"
    subprocess.run(
        [ffmpeg, "-v", "error", "-f", "lavfi", "-i",
         "testsrc=size=64x64:rate=10", "-f", "lavfi", "-i",
         "sine=frequency=440:sample_rate=16000", "-t", "1.2",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(video)],
        stdin=subprocess.DEVNULL, check=True, capture_output=True,
    )
    payload = bytearray(video.read_bytes())
    offset = 0
    while offset < len(payload):
        size = int.from_bytes(payload[offset:offset + 4], "big")
        assert size >= 8
        if payload[offset + 4:offset + 8] == b"mdat":
            payload[offset + 8:offset + size] = bytes(size - 8)
            break
        offset += size
    else:
        raise AssertionError("encoded test MP4 has no media-data box")
    video.write_bytes(payload)
    report = verification.verify_video(video, check_content=True)
    assert report.has_video and report.has_audio
    assert report.width == 64 and report.height == 64 and report.duration_s >= 1
    assert not report.ok


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


def test_stats_each_render_a_card() -> None:
    fs = FrameState(scene_kind=SceneKind.SLIDE, title="Nums",
                    stats=[("1", "a"), ("2", "b"), ("3", "c"), ("4", "d")])
    img = render_frame(fs, (1920, 1080))
    inked = [_band_var(img, 0.30, 0.62, 0.06 + i * 0.23, 0.27 + i * 0.23) > 3
             for i in range(4)]
    assert all(inked), inked


# --- MAJOR/MINOR: graceful config + malformed input -----------------------

def test_compositor_keeps_only_well_formed_stat_pairs() -> None:
    from democreate.assembly.compositor import build_timeline
    from democreate.schema import Chunk, Demo, Scene

    demo = Demo(title="Stats", scenes=[Scene(
        id="slide", kind=SceneKind.SLIDE,
        context={"stats": [["90%", "complete"], "99%", ["one"], None]},
        chunks=[Chunk(id="c", text="hello")],
    )])
    assert build_timeline(demo).entries[0].state.stats == [("90%", "complete")]


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
