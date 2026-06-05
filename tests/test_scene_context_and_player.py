"""Regression tests for scene-context → FrameState mapping and player timeline."""

from __future__ import annotations

from pathlib import Path

from democreate.assembly.compositor import _state_for_chunk
from democreate.export.interactive import build_timeline, export_html_player
from democreate.schema import Chunk, Demo, Scene, SceneKind


def test_scene_context_maps_to_frame_state() -> None:
    chunk = Chunk(id="c", text="hi")
    demo = Demo(title="T", scenes=[Scene(id="s", kind=SceneKind.SLIDE)])
    demo.scenes[0].chunks.append(chunk)
    context = {
        "section": "Architecture",
        "subtitle": "the overview",
        "background_image": "/tmp/bg.png",
    }
    state = _state_for_chunk(demo, SceneKind.SLIDE, "Title", context, chunk)
    assert state.section == "Architecture"
    assert state.subtitle == "the overview"
    assert state.background_image == "/tmp/bg.png"


def test_build_timeline_frames_use_global_index() -> None:
    s1 = Scene(id="s1", title="One")
    s1.chunks.extend([Chunk(id="a", text="x"), Chunk(id="b", text="y")])
    s2 = Scene(id="s2", title="Two")
    s2.chunks.append(Chunk(id="c", text="z"))
    demo = Demo(title="T", scenes=[s1, s2])
    tl = build_timeline(demo)
    frames = [cue["frame"] for cue in tl["captions"]]
    # frame names are global, zero-padded, and match the compositor's frame_NNNN
    assert frames == ["frame_0000.png", "frame_0001.png", "frame_0002.png"]
    assert len(tl["chapters"]) == 2


def test_player_lists_chapters_and_references_frames(tmp_path: Path) -> None:
    s = Scene(id="s", title="Scene One")
    s.chunks.append(Chunk(id="c", text="hello there"))
    demo = Demo(title="My Demo", scenes=[s])
    out = export_html_player(demo, None, tmp_path / "player.html", frames_dir="../frames")
    html = out.read_text(encoding="utf-8")
    assert "My Demo" in html
    assert "Scene One" in html  # chapter rendered
    assert "frame_0000.png" in html  # caption cue references the real frame name
    assert "../frames" in html
