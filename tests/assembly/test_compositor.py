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


def test_scene_events_preserve_files_and_independent_snapshots() -> None:
    chunks = [
        Chunk(id="create", text="create", actions=[Action(
            ActionType.CREATE_FILE, {"path": "a.py", "code": "x = 1"}
        )]),
        Chunk(id="highlight", text="highlight", actions=[Action(
            ActionType.HIGHLIGHT_LINES, {"lines": [1]}
        )]),
        Chunk(id="type", text="type", actions=[Action(
            ActionType.TYPE_CODE, {"code": ["y = 2"]}
        )]),
        Chunk(id="close", text="close", actions=[Action(
            ActionType.CLOSE_FILE, {"path": "a.py"}
        )]),
        Chunk(id="reopen", text="reopen", actions=[Action(
            ActionType.OPEN_FILE, {"path": "a.py"}
        )]),
    ]
    entries = build_timeline(Demo(title="Events", scenes=[
        Scene(id="s", chunks=chunks)
    ])).entries
    assert entries[0].state.code_lines == ["x = 1"]
    assert entries[0].state.highlight_lines == []
    assert entries[1].state.file_path == "a.py"
    assert entries[1].state.code_lines == ["x = 1"]
    assert entries[1].state.highlight_lines == [1]
    assert entries[2].state.code_lines == ["x = 1", "y = 2"]
    assert entries[3].state.file_path == ""
    assert entries[3].state.code_lines == []
    assert entries[4].state.code_lines == ["x = 1", "y = 2"]
    replay = entries[4].state_at_ms(entries[4].start_ms)
    replay.code_lines.append("not shared")
    assert entries[0].state.code_lines == ["x = 1"]
    assert entries[4].state.code_lines == ["x = 1", "y = 2"]


def test_terminal_browser_and_editor_state_survive_surface_changes() -> None:
    actions = [
        [Action(ActionType.CREATE_FILE, {"path": "a.py", "code": "pass"})],
        [Action(ActionType.RUN_COMMAND, {"command": "echo one", "output": "one"})],
        [Action(ActionType.PRINT_OUTPUT, {"output": "two"})],
        [Action(ActionType.NAVIGATE, {"url": "https://example.test"})],
        [],
        [Action(ActionType.OPEN_FILE, {"path": "a.py"})],
    ]
    demo = Demo(title="Surfaces", scenes=[Scene(id="s", chunks=[
        Chunk(id=str(i), text="step", actions=events)
        for i, events in enumerate(actions)
    ])])
    entries = build_timeline(demo).entries
    assert entries[2].state.terminal_lines == ["$ echo one", "one", "two"]
    assert entries[4].state.scene_kind == SceneKind.WEBSITE
    assert entries[4].state.url == "https://example.test"
    assert entries[5].state.scene_kind == SceneKind.CODEBASE
    assert entries[5].state.code_lines == ["pass"]
    assert entries[5].state.terminal_lines == ["$ echo one", "one", "two"]


def test_timed_events_reveal_at_trigger_and_continue_across_chunks() -> None:
    demo = Demo(title="Timing", scenes=[Scene(id="s", chunks=[
        Chunk(id="a", text="first", duration_ms=600, actions=[Action(
            ActionType.CREATE_FILE, {"path": "a.py", "code": "abcd"},
            timestamp_ms=500, duration_ms=200,
        )]),
        Chunk(id="b", text="second", duration_ms=400),
    ])])
    first, second = build_timeline(demo).entries
    assert first.state_at_ms(499).file_path == ""
    assert first.state_at_ms(500).file_path == "a.py"
    assert first.state_at_ms(500).code_lines == []
    assert second.state_at_ms(600).code_lines == ["ab"]
    assert second.state_at_ms(700).code_lines == ["abcd"]
    assert first.state.code_lines == ["abcd"]  # representative still, not playback


@pytest.mark.parametrize("action_type", [
    ActionType.CREATE_FILE, ActionType.OPEN_FILE, ActionType.TYPE_CODE,
])
@pytest.mark.parametrize(("code", "complete", "partial"), [
    ("abcdefgh", ["abcdefgh"], ["abcd"]),
    (["abcd", "efgh"], ["abcd", "efgh"], ["abcd"]),
])
def test_scheduled_typing_toggle_preserves_triggers_and_shared_snapshots(
    action_type: ActionType, code: str | list[str],
    complete: list[str], partial: list[str],
) -> None:
    demo = Demo(title="Typing", scenes=[Scene(id="s", chunks=[
        Chunk(id="first", text="first", duration_ms=600, actions=[Action(
            action_type, {"path": "a.py", "code": code},
            timestamp_ms=500, duration_ms=200,
        )]),
        Chunk(id="second", text="second", duration_ms=400),
    ])])
    authored = json.dumps(demo.to_dict())
    timeline = build_timeline(demo)
    stored = json.dumps(timeline.to_dict())
    first, second = timeline.entries
    assert first.actions is second.actions
    for typing in (True, False):
        before = first.state_at_ms(499, typing=typing)
        assert before.code_lines == []
        assert before.file_path == ""
        at_trigger = first.state_at_ms(500, typing=typing)
        assert at_trigger.code_lines == ([] if typing else complete)
        halfway = second.state_at_ms(600, typing=typing)
        assert halfway.code_lines == (partial if typing else complete)
        assert second.state_at_ms(700, typing=typing).code_lines == complete
        halfway.code_lines.append("private edit")
    assert first.state_at_ms(600).code_lines == partial
    assert json.dumps(timeline.to_dict()) == stored
    assert json.dumps(demo.to_dict()) == authored


@pytest.mark.parametrize("typing", [True, False])
def test_wait_delays_untimed_events_and_commands_complete_after_duration(
    typing: bool,
) -> None:
    demo = Demo(title="Wait", scenes=[Scene(id="s", chunks=[Chunk(
        id="a", text="wait then run", start_ms=300, duration_ms=1000,
        actions=[
            Action(ActionType.WAIT, duration_ms=200),
            Action(ActionType.RUN_COMMAND, {"command": "echo ok", "output": "ok"},
                   duration_ms=100),
        ],
    )])])
    entry = build_timeline(demo).entries[0]
    assert entry.state_at_ms(499, typing=typing).terminal_lines == []
    assert entry.state_at_ms(500, typing=typing).terminal_lines == ["$ echo ok"]
    assert entry.state_at_ms(599, typing=typing).terminal_lines == ["$ echo ok"]
    assert entry.state_at_ms(600, typing=typing).terminal_lines == ["$ echo ok", "ok"]


def test_measured_fast_audio_keeps_synced_timeline_windows() -> None:
    demo = Demo(title="Fast", scenes=[Scene(id="s", chunks=[
        Chunk(id="a", text="one two three four", start_ms=300, duration_ms=400),
        Chunk(id="b", text="five six seven eight", start_ms=920, duration_ms=400),
    ])])
    timeline = build_timeline(demo)
    assert [(entry.start_ms, entry.end_ms) for entry in timeline.entries] == [
        (300, 700), (920, 1320)
    ]
    assert timeline.entry_at_ms(800) is None
    assert timeline.total_ms == 1320
    padded = build_timeline(demo, trail_ms=600)
    assert padded.total_ms == 1920
    assert [(entry.start_ms, entry.end_ms) for entry in padded.entries] == [
        (300, 700), (920, 1320)
    ]
    assert padded.frame_count() == round(1920 / 1000 * demo.fps)
    assert padded.entry_at_ms(1500) is None


def test_timeline_rejects_negative_trailing_silence() -> None:
    with pytest.raises(ValueError):
        build_timeline(Demo(title="Empty"), trail_ms=-1)


@pytest.mark.parametrize("typing", [True, False])
def test_coordinate_click_and_camera_durations_follow_absolute_time(
    typing: bool,
) -> None:
    demo = Demo(title="Pointer", scenes=[Scene(id="s", chunks=[Chunk(
        id="a", text="move", duration_ms=1000, actions=[
            Action(ActionType.MOVE_MOUSE, {"xy": [0, 0]}, timestamp_ms=0),
            Action(ActionType.CLICK, {"xy": [100, 200]},
                   timestamp_ms=400, duration_ms=200),
            Action(ActionType.ZOOM, {"scale": 2.0},
                   timestamp_ms=400, duration_ms=200),
        ],
    )])])
    entry = build_timeline(demo).entries[0]
    assert entry.state_at_ms(399, typing=typing).cursor_xy == (0, 0)
    assert entry.state_at_ms(500, typing=typing).cursor_xy == (50, 100)
    assert entry.state_at_ms(500, typing=typing).scale == 1.5
    assert entry.state_at_ms(600, typing=typing).cursor_xy == (100, 200)
    assert entry.state_at_ms(600, typing=typing).scale == 2.0


def test_scene_boundary_resets_virtual_environment() -> None:
    demo = Demo(title="Scenes", scenes=[
        Scene(id="first", chunks=[Chunk(id="a", text="create", actions=[Action(
            ActionType.CREATE_FILE, {"path": "a.py", "code": "pass"}
        )])]),
        Scene(id="second", chunks=[Chunk(id="b", text="new scene")]),
    ])
    first, second = build_timeline(demo).entries
    assert first.state.file_path == "a.py"
    assert second.state_at_ms(second.start_ms).file_path == ""
    assert first.state.file_path == "a.py"
