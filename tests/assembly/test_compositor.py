"""Tests for the assembly compositor: timeline build + ManifestCompositor."""

from __future__ import annotations

import json

import pytest

from democreate.assembly.compositor import (
    ManifestCompositor,
    MoviePyCompositor,
    Timeline,
    TimelineEntry,
    build_timeline,
)
from democreate.errors import BackendUnavailableError
from democreate.media import FrameState
from democreate.schema import (
    Action,
    ActionType,
    Chunk,
    Demo,
    Scene,
    SceneKind,
)


def test_timeline_entry_duration_and_dict() -> None:
    state = FrameState(scene_kind=SceneKind.TERMINAL, caption="hi")
    entry = TimelineEntry(
        index=2, start_ms=1000, end_ms=2500, state=state, chunk_id="c1"
    )
    assert entry.duration_ms == 1500
    d = entry.to_dict()
    assert d["index"] == 2
    assert d["duration_ms"] == 1500
    assert d["chunk_id"] == "c1"
    assert d["state"]["caption"] == "hi"


def test_build_timeline_monotonic_non_overlapping(sample_demo: Demo) -> None:
    tl = build_timeline(sample_demo)
    assert tl.entries, "timeline must have entries"
    # one entry per chunk
    assert len(tl.entries) == len(sample_demo.iter_chunks())
    prev_end = 0
    for i, entry in enumerate(tl.entries):
        assert entry.index == i
        assert entry.start_ms == prev_end  # gap-free, back-to-back
        assert entry.end_ms > entry.start_ms
        prev_end = entry.end_ms
    assert tl.total_ms == tl.entries[-1].end_ms


def test_build_timeline_frame_count_positive(sample_demo: Demo) -> None:
    tl = build_timeline(sample_demo)
    assert tl.frame_count() > 0
    assert tl.fps == sample_demo.fps


def test_build_timeline_fps_override(sample_demo: Demo) -> None:
    tl = build_timeline(sample_demo, fps=60)
    assert tl.fps == 60
    expected = round(tl.total_ms / 1000 * 60)
    assert tl.frame_count() == expected


def test_build_timeline_empty_demo() -> None:
    demo = Demo(title="Empty")
    tl = build_timeline(demo)
    assert tl.entries == []
    assert tl.total_ms == 0
    assert tl.frame_count() == 0


def test_state_reflects_open_file_and_highlight(sample_demo: Demo) -> None:
    tl = build_timeline(sample_demo)
    open_entry = tl.entries[0]
    assert open_entry.state.scene_kind == SceneKind.CODEBASE
    assert open_entry.state.file_path == "src/democreate/cli.py"
    assert open_entry.state.highlight_lines == [1, 2, 3]
    assert open_entry.state.caption.startswith("We begin")


def test_state_reflects_type_code(sample_demo: Demo) -> None:
    tl = build_timeline(sample_demo)
    type_entry = tl.entries[1]
    assert any("Demo(title='Tour')" in line for line in type_entry.state.code_lines)


def test_state_reflects_run_command_terminal(sample_demo: Demo) -> None:
    tl = build_timeline(sample_demo)
    run_entry = tl.entries[-1]
    assert run_entry.state.scene_kind == SceneKind.TERMINAL
    assert any("democreate build" in line for line in run_entry.state.terminal_lines)


def test_state_reflects_navigate_browser() -> None:
    scene = Scene(id="web", title="Site", kind=SceneKind.WEBSITE)
    scene.chunks.append(
        Chunk(
            id="nav",
            text="We open the documentation homepage in the browser now.",
            actions=[
                Action(ActionType.NAVIGATE, {"url": "https://example.com/docs"})
            ],
        )
    )
    demo = Demo(title="Web", scenes=[scene])
    tl = build_timeline(demo)
    assert tl.entries[0].state.scene_kind == SceneKind.WEBSITE
    assert tl.entries[0].state.url == "https://example.com/docs"


def test_state_zoom_and_mouse() -> None:
    scene = Scene(id="cam", title="Cam", kind=SceneKind.CODEBASE)
    scene.chunks.append(
        Chunk(
            id="z",
            text="Zoom into the interesting region of the editor view here.",
            actions=[
                Action(ActionType.ZOOM, {"scale": 1.5}),
                Action(ActionType.MOVE_MOUSE, {"xy": [100, 200]}),
            ],
        )
    )
    demo = Demo(title="Cam", scenes=[scene])
    tl = build_timeline(demo)
    state = tl.entries[0].state
    assert state.scale == 1.5
    assert state.cursor_xy == (100, 200)


def test_build_timeline_respects_synced_start_ms() -> None:
    scene = Scene(id="s", title="S")
    scene.chunks.append(
        Chunk(id="a", text="one two three four five", start_ms=5000)
    )
    scene.chunks.append(Chunk(id="b", text="six seven eight nine ten"))
    demo = Demo(title="Synced", scenes=[scene])
    tl = build_timeline(demo)
    assert tl.entries[0].start_ms == 5000
    # second chunk follows the first, no overlap
    assert tl.entries[1].start_ms == tl.entries[0].end_ms


def test_timeline_entry_at_ms(sample_demo: Demo) -> None:
    tl = build_timeline(sample_demo)
    first = tl.entries[0]
    assert tl.entry_at_ms(first.start_ms) is first
    assert tl.entry_at_ms(first.end_ms - 1) is first
    # boundary belongs to the next entry, not this one
    assert tl.entry_at_ms(first.end_ms) is not first
    assert tl.entry_at_ms(-1) is None
    assert tl.entry_at_ms(tl.total_ms) is None


def test_timeline_to_dict_roundtrips_json(sample_demo: Demo) -> None:
    tl = build_timeline(sample_demo)
    d = tl.to_dict()
    text = json.dumps(d)
    back = json.loads(text)
    assert back["total_ms"] == tl.total_ms
    assert back["frame_count"] == tl.frame_count()
    assert len(back["entries"]) == len(tl.entries)


def test_manifest_compositor_writes_manifest_and_frames(
    sample_demo: Demo, tmp_workspace
) -> None:
    tl = build_timeline(sample_demo)
    comp = ManifestCompositor()
    manifest_path = comp.compose(tl, tmp_workspace)

    assert manifest_path.exists()
    assert manifest_path.name == "render_manifest.json"
    data = json.loads(manifest_path.read_text())
    assert len(data["entries"]) == len(tl.entries)

    frames = sorted(tmp_workspace.frames.glob("frame_*.png"))
    assert len(frames) == len(tl.entries)
    assert len(frames) >= 1
    # Real PNG bytes were written.
    for frame in frames:
        assert frame.stat().st_size > 0
        assert frame.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_manifest_compositor_frame_naming(sample_demo: Demo, tmp_workspace) -> None:
    tl = build_timeline(sample_demo)
    ManifestCompositor().compose(tl, tmp_workspace)
    assert (tmp_workspace.frames / "frame_0000.png").exists()


def test_moviepy_compositor_without_dep_raises(
    sample_demo: Demo, tmp_workspace
) -> None:
    pytest.importorskip  # noqa: B018 - just referencing
    import importlib.util

    if importlib.util.find_spec("moviepy") is not None:  # pragma: no cover
        pytest.skip("moviepy is installed; cannot test the unavailable path")
    tl = build_timeline(sample_demo)
    with pytest.raises(BackendUnavailableError) as exc:
        MoviePyCompositor().compose(tl, tmp_workspace)
    assert exc.value.backend == "moviepy"
    assert exc.value.extra == "video"


def test_timeline_is_dataclass_constructible() -> None:
    tl = Timeline(entries=[], total_ms=0, fps=30)
    assert tl.frame_count() == 0
    assert tl.entry_at_ms(0) is None
