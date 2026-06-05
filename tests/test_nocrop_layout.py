"""Tests for the no-crop, information-dense layout (v0.6.1).

The load-bearing invariant: nothing on a frame is ever cropped off the edges —
backgrounds fit-contain (whole image visible), code autosizes to fit, and the
Ken Burns zoom (which crops) is off by default.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from democreate.capture.screen import render_frame
from democreate.config import VideoConfig
from democreate.media import FrameState
from democreate.schema import SceneKind


def test_ken_burns_off_by_default() -> None:
    assert VideoConfig().ken_burns is False


def _has_color(img: Image.Image, target: tuple[int, int, int], tol: int = 40) -> bool:
    """True if some pixel is within ``tol`` of ``target`` (sampled on a grid)."""
    w, h = img.size
    for x in range(0, w, 7):
        for y in range(0, h, 7):
            r, g, b = img.getpixel((x, y))[:3]
            if abs(r - target[0]) <= tol and abs(g - target[1]) <= tol and abs(b - target[2]) <= tol:
                return True
    return False


def test_background_contains_whole_image_no_crop(tmp_path: Path) -> None:
    # a wide figure with distinct LEFT (yellow) and RIGHT (cyan) edge stripes
    fig = Image.new("RGB", (1600, 400), (200, 80, 40))
    for y in range(400):
        for x in range(0, 30):
            fig.putpixel((x, y), (255, 255, 0))        # left edge yellow
            fig.putpixel((1599 - x, y), (0, 255, 255))  # right edge cyan
    p = tmp_path / "wide.png"
    fig.save(p)
    fs = FrameState(scene_kind=SceneKind.SLIDE, background_image=str(p),
                    caption="caption below, not over")
    out = render_frame(fs, (1920, 1080))
    # a cover-crop of a 4:1 image into 16:9 would cut BOTH edge stripes off;
    # fit-contain keeps them — both colors must survive.
    assert _has_color(out, (255, 255, 0)), "left edge cropped"
    assert _has_color(out, (0, 255, 255)), "right edge cropped"


def test_background_caption_does_not_overlap_image(tmp_path: Path) -> None:
    # the contained image must sit above the caption band (which is near the bottom)
    fig = Image.new("RGB", (1000, 1000), (220, 30, 30))  # square, vivid red
    p = tmp_path / "sq.png"
    fig.save(p)
    fs = FrameState(scene_kind=SceneKind.SLIDE, background_image=str(p),
                    caption="A caption that sits in its own band below the image.")
    out = render_frame(fs, (1920, 1080))
    # the image (contained) does not reach the very bottom; the lower band is dark
    bottom_px = out.getpixel((960, 1060))
    assert bottom_px[0] < 120  # not the vivid red image → image stayed above


def test_code_autosizes_and_shows_all_lines() -> None:
    code = [f"line_{i} = {i}" for i in range(20)]  # many short lines
    fs = FrameState(scene_kind=SceneKind.CODEBASE, file_path="m.py", code_lines=code)
    out = render_frame(fs, (1920, 1080))
    assert out.size == (1920, 1080)
    # autosize fills: there is ink well into the lower-middle of the content area
    from PIL import ImageStat

    lower = out.crop((0, 600, 1920, 880))
    assert ImageStat.Stat(lower.convert("L")).var[0] > 0  # lines reach down the frame


def test_long_code_line_does_not_clip_at_right_edge() -> None:
    long_line = "x = " + " + ".join(f"value_{i}" for i in range(40))  # very long
    fs = FrameState(scene_kind=SceneKind.CODEBASE, file_path="m.py",
                    code_lines=["def f():", "    " + long_line, "    return x"])
    out = render_frame(fs, (1920, 1080))
    # the far-right column (last 1.5%) should be background, not clipped text glyphs
    right = out.crop((int(1920 * 0.985), 100, 1920, 700)).convert("L")
    from PIL import ImageStat

    # mostly uniform (background) → text was wrapped/sized to not run off the edge
    assert ImageStat.Stat(right).stddev[0] < 40


def test_bullet_slide_renders_all_bullets() -> None:
    fs = FrameState(scene_kind=SceneKind.SLIDE, title="What it is",
                    bullets=["First point that is reasonably long and wraps nicely here",
                             "Second point", "Third point about determinism"])
    out = render_frame(fs, (1920, 1080))
    assert out.size == (1920, 1080)
    from PIL import ImageStat
    # bullets fill the mid-frame content area with ink (not an empty title card)
    mid = out.crop((0, 300, 1920, 800)).convert("L")
    assert ImageStat.Stat(mid).var[0] > 5


def test_stat_slide_renders_cards() -> None:
    fs = FrameState(scene_kind=SceneKind.SLIDE, title="By the numbers",
                    stats=[("592", "tests"), ("7", "subsystems"), ("0", "pip core")])
    out = render_frame(fs, (1920, 1080))
    assert out.size == (1920, 1080)
    from PIL import ImageStat
    # the stat-card row produces ink across the full width band
    band = out.crop((0, 350, 1920, 650)).convert("L")
    assert ImageStat.Stat(band).var[0] > 5


def test_framestate_bullets_stats_round_trip() -> None:
    fs = FrameState(scene_kind=SceneKind.SLIDE, bullets=["a", "b"],
                    stats=[("4K", "res"), ("18", "crf")])
    d = fs.to_dict()
    assert d["bullets"] == ["a", "b"]
    assert d["stats"] == [["4K", "res"], ["18", "crf"]]


def test_measured_chapters_align_to_clip_timeline(tmp_path) -> None:
    """Chapter starts must follow the measured clip durations, not estimates."""
    from democreate.export.chapters import measured_chapters
    from democreate.media import AudioClip
    from democreate.schema import Chunk, Demo, Scene

    demo = Demo(title="Chapters", scenes=[
        Scene(id="s1", title="One", chunks=[Chunk(id="c1", text="x")]),
        Scene(id="s2", title="Two", chunks=[Chunk(id="c2", text="y")]),
        Scene(id="s3", title="Three", chunks=[Chunk(id="c3", text="z")]),
    ])
    clips = [AudioClip(path=tmp_path / f"{i}.wav", duration_ms=d, chunk_id=c)
             for i, (d, c) in enumerate([(2000, "c1"), (5000, "c2"), (1000, "c3")])]
    chapters, total = measured_chapters(demo, clips, gap_ms=0)
    starts = [c["start_ms"] for c in chapters]
    assert starts == [0, 2000, 7000]   # cumulative measured durations
    assert total == 8000
    assert [c["title"] for c in chapters] == ["One", "Two", "Three"]
