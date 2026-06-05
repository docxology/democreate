"""Tests for v0.5: typing/cursor animation, paper structure, export commands."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat
from typer.testing import CliRunner

from democreate.assembly.animator import (
    AnimationConfig,
    _draw_cursor,
    render_animation_frames,
)
from democreate.cli import app
from democreate.config import ASPECTS, RenderConfig
from democreate.media import AudioClip, FrameState
from democreate.paper.extract import PaperSummary
from democreate.paper.script import build_paper_demo
from democreate.paper.structure import FigureCaption, PaperSection
from democreate.pipeline import _typing_flags
from democreate.schema import Action, ActionType, Chunk, Demo, Scene, SceneKind

runner = CliRunner()


# --- config aspect --------------------------------------------------------

def test_set_aspect_changes_geometry() -> None:
    cfg = RenderConfig()
    cfg.set_aspect("9:16")
    assert (cfg.video.width, cfg.video.height) == ASPECTS["9:16"]
    cfg.set_aspect("nonsense")  # ignored
    assert (cfg.video.width, cfg.video.height) == ASPECTS["9:16"]


# --- typing flags ---------------------------------------------------------

def test_typing_flags_only_editor_typecode() -> None:
    s1 = Scene(id="code", kind=SceneKind.CODEBASE)
    s1.chunks.append(Chunk(id="c1", text="x", actions=[
        Action(ActionType.CREATE_FILE, {"path": "a.py", "code": "x=1"})]))
    s2 = Scene(id="slide", kind=SceneKind.SLIDE)  # not editor
    s2.chunks.append(Chunk(id="c2", text="y", actions=[
        Action(ActionType.TYPE_CODE, {"code": "z=2"})]))
    s3 = Scene(id="bg", kind=SceneKind.CODEBASE, context={"background_image": "/x.png"})
    s3.chunks.append(Chunk(id="c3", text="z", actions=[
        Action(ActionType.TYPE_CODE, {"code": "q=3"})]))
    s4 = Scene(id="plain", kind=SceneKind.CODEBASE)  # editor but no type action
    s4.chunks.append(Chunk(id="c4", text="w", actions=[
        Action(ActionType.OPEN_FILE, {"path": "b.py"})]))
    demo = Demo(title="T", scenes=[s1, s2, s3, s4])
    assert _typing_flags(demo) == [True, False, False, False]


# --- cursor drawing -------------------------------------------------------

def test_draw_cursor_marks_pixels() -> None:
    img = Image.new("RGB", (200, 200), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    _draw_cursor(draw, (100, 100), 1.0, ripple=0.5)
    assert ImageStat.Stat(img.convert("L")).var[0] > 0  # something was drawn


# --- typing animation end to end -----------------------------------------

def _mkwav(path: Path, ms: int) -> None:
    n = int(22050 * ms / 1000)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", 8000 if i % 2 else -8000) for i in range(n)))


def test_typing_render_reveals_progressively(tmp_path: Path) -> None:
    base_dir = tmp_path / "f"
    base_dir.mkdir()
    p = base_dir / "frame_0000.png"
    Image.new("RGB", (640, 360), (20, 22, 28)).save(p)
    clip = AudioClip(path=tmp_path / "a.wav", duration_ms=2000, chunk_id="c0")
    _mkwav(tmp_path / "v.wav", 2000)
    state = FrameState(
        scene_kind=SceneKind.CODEBASE, file_path="demo.py",
        code_lines=["def f():", "    return 1", "    # done here"],
    )
    cfg = AnimationConfig(fps=10, bars=30, typing=True, typing_fraction=0.7,
                          transitions=False, ken_burns=False, cursor=False)
    written, total = render_animation_frames(
        [p], [clip], tmp_path / "v.wav", tmp_path / "anim", size=(640, 360),
        config=cfg, frame_states=[state], typing_flags=[True],
    )
    assert total == 2000 and len(written) == 20
    # an early frame has fewer non-background pixels than a late one (more typed)
    early = Image.open(written[2]).convert("L")
    late = Image.open(written[14]).convert("L")
    early_ink = sum(early.histogram()[61:])  # pixels brighter than background
    late_ink = sum(late.histogram()[61:])
    assert late_ink > early_ink  # more characters revealed later


# --- paper structure in build_paper_demo ----------------------------------

def test_build_paper_demo_uses_real_captions_and_sections() -> None:
    summary = PaperSummary(
        title="P", authors="A", abstract="We test. It works.", page_count=10,
        figures=[Path("/f1.png"), Path("/f2.png")], pdf_path="/x.pdf",
    )
    caps = [FigureCaption(number=1, caption="The first real caption."),
            FigureCaption(number=2, caption="The second real caption.")]
    secs = [PaperSection(number="1", title="Introduction"),
            PaperSection(number="2", title="Results")]
    demo = build_paper_demo(summary, figure_captions=caps, sections=secs, max_figures=2)
    texts = [c.text for c in demo.iter_chunks()]
    assert any("The first real caption." in t for t in texts)
    assert any("organised into 2 parts" in t and "Introduction" in t for t in texts)


# --- CLI: thumbnail + gif -------------------------------------------------

def test_cli_thumbnail(tmp_path: Path) -> None:
    demo = tmp_path / "d.json"
    runner.invoke(app, ["init", str(demo)])
    out = tmp_path / "poster.png"
    res = runner.invoke(app, ["thumbnail", str(demo), "--out", str(out)])
    assert res.exit_code == 0, res.stdout
    img = Image.open(out)
    assert img.size[0] > 0 and ImageStat.Stat(img.convert("L")).var[0] > 0


def test_cli_gif(tmp_path: Path) -> None:
    demo = tmp_path / "d.json"
    runner.invoke(app, ["init", str(demo)])
    out = tmp_path / "demo.gif"
    res = runner.invoke(app, ["gif", str(demo), "-o", str(tmp_path / "g"), "--gif", str(out)])
    assert res.exit_code == 0, res.stdout
    gif = Image.open(out)
    assert getattr(gif, "n_frames", 1) >= 1


# --- chapters export ------------------------------------------------------

def test_chapters_youtube_and_ffmetadata() -> None:
    from democreate.export.chapters import to_ffmetadata, to_youtube_chapters

    s1 = Scene(id="a", title="Intro")
    s1.chunks.append(Chunk(id="c1", text="one two three"))
    s2 = Scene(id="b", title="Body")
    s2.chunks.append(Chunk(id="c2", text="four five six"))
    demo = Demo(title="T", scenes=[s1, s2])
    yt = to_youtube_chapters(demo)
    assert yt.splitlines()[0].startswith("0:00")
    meta = to_ffmetadata(demo)
    assert ";FFMETADATA1" in meta
    assert meta.count("[CHAPTER]") == 2
