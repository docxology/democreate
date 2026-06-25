"""Extra coverage for the compositor: every action->FrameState branch and the
pure-Pillow fallback renderer. Complements tests/assembly/test_compositor.py.
"""

from __future__ import annotations

from democreate.assembly.compositor import (
    ManifestCompositor,
    _state_for_chunk,
    build_timeline,
)
from democreate.schema import Action, ActionType, Chunk, Demo, Scene, SceneKind


def _state(actions, *, kind=SceneKind.CODEBASE, context=None):
    chunk = Chunk(id="c", text="narration here", actions=actions)
    demo = Demo(title="T", scenes=[Scene(id="s", kind=kind, context=context or {})])
    demo.scenes[0].chunks.append(chunk)
    return _state_for_chunk(demo, kind, "Scene Title", context or {}, chunk)


def test_base_url_context_sets_url() -> None:
    s = _state([], kind=SceneKind.WEBSITE, context={"base_url": "https://x.test"})
    assert s.url == "https://x.test"


def test_create_file_with_string_and_list_code() -> None:
    s = _state([Action(ActionType.CREATE_FILE, {"path": "a.py", "code": "x=1\ny=2"})])
    assert s.file_path == "a.py" and s.title == "a.py"
    assert s.code_lines == ["x=1", "y=2"]
    s2 = _state([Action(ActionType.OPEN_FILE, {"path": "b.py", "code": ["l1", "l2"]})])
    assert s2.code_lines == ["l1", "l2"]


def test_type_code_appends_lines_list_and_str() -> None:
    s = _state(
        [
            Action(ActionType.OPEN_FILE, {"path": "a.py", "code": "x=1"}),
            Action(ActionType.TYPE_CODE, {"code": ["y=2", "z=3"]}),
        ]
    )
    assert s.code_lines == ["x=1", "y=2", "z=3"]
    s2 = _state([Action(ActionType.TYPE_CODE, {"code": "single"})])
    assert s2.code_lines == ["single"]


def test_highlight_lines_list_and_int() -> None:
    s = _state([Action(ActionType.HIGHLIGHT_LINES, {"lines": [1, 2, 3]})])
    assert s.highlight_lines == [1, 2, 3]
    s2 = _state([Action(ActionType.HIGHLIGHT_LINES, {"lines": 5})])
    assert s2.highlight_lines == [5]


def test_run_command_switches_to_terminal_and_collects_output() -> None:
    s = _state(
        [Action(ActionType.RUN_COMMAND, {"command": "ls", "output": ["a", "b"]})]
    )
    assert s.scene_kind == SceneKind.TERMINAL
    assert s.terminal_lines == ["$ ls", "a", "b"]


def test_print_output_string_splits_lines() -> None:
    s = _state([Action(ActionType.PRINT_OUTPUT, {"output": "line1\nline2"})])
    assert s.terminal_lines == ["line1", "line2"]


def test_navigate_switches_to_website() -> None:
    s = _state([Action(ActionType.NAVIGATE, {"url": "https://y.test"})])
    assert s.scene_kind == SceneKind.WEBSITE
    assert s.url == "https://y.test"


def test_move_mouse_sets_cursor() -> None:
    s = _state([Action(ActionType.MOVE_MOUSE, {"xy": [100, 200]})])
    assert s.cursor_xy == (100, 200)
    s2 = _state([Action(ActionType.MOVE_MOUSE, {"position": (5, 6)})])
    assert s2.cursor_xy == (5, 6)


def test_zoom_and_pan_set_scale() -> None:
    s = _state([Action(ActionType.ZOOM, {"scale": 2.0})])
    assert s.scale == 2.0
    s2 = _state([Action(ActionType.PAN, {"scale": 1.5})])
    assert s2.scale == 1.5


def test_build_timeline_guards_backwards_synced_start() -> None:
    # A later chunk with a synced start_ms BEFORE the running cursor must be
    # clamped forward so entries never overlap/decrease.
    scene = Scene(id="s", kind=SceneKind.CODEBASE)
    scene.chunks.append(Chunk(id="c1", text="one two three four five", start_ms=0))
    scene.chunks.append(Chunk(id="c2", text="six seven eight", start_ms=10))  # too early
    demo = Demo(title="T", scenes=[scene])
    timeline = build_timeline(demo)
    starts = [e.start_ms for e in timeline.entries]
    assert starts == sorted(starts)
    assert timeline.entries[1].start_ms >= timeline.entries[0].end_ms


def test_fallback_renderer_runs_when_capture_absent(tmp_workspace, monkeypatch) -> None:
    # Force the core-only fallback path by pretending capture.screen is unavailable.
    comp = ManifestCompositor(width=320, height=240)
    monkeypatch.setattr(comp, "_resolve_render_frame", lambda: None)
    demo = Demo(title="Fallback", scenes=[Scene(id="s", kind=SceneKind.TERMINAL)])
    demo.scenes[0].chunks.append(
        Chunk(
            id="c",
            text="run it",
            actions=[Action(ActionType.RUN_COMMAND, {"command": "ls", "output": "a"})],
        )
    )
    timeline = build_timeline(demo)
    manifest = comp.compose(timeline, tmp_workspace)
    assert manifest.exists()
    frames = sorted(tmp_workspace.frames.glob("frame_*.png"))
    assert frames and all(f.stat().st_size > 0 for f in frames)


def test_fallback_renderer_website_and_slide(tmp_workspace, monkeypatch) -> None:
    comp = ManifestCompositor(width=200, height=150)
    monkeypatch.setattr(comp, "_resolve_render_frame", lambda: None)
    for kind, action in (
        (SceneKind.WEBSITE, Action(ActionType.NAVIGATE, {"url": "https://z.test"})),
        (SceneKind.SLIDE, Action(ActionType.OPEN_FILE, {"path": "deck"})),
    ):
        demo = Demo(title="K", scenes=[Scene(id="s", kind=kind)])
        demo.scenes[0].chunks.append(Chunk(id="c", text="caption", actions=[action]))
        comp.compose(build_timeline(demo), tmp_workspace)
    assert sorted(tmp_workspace.frames.glob("frame_*.png"))
