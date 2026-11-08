"""Action-to-visible-state behavior complementing test_compositor.py."""

from __future__ import annotations

from democreate.assembly.compositor import build_timeline
from democreate.schema import Action, ActionType, Chunk, Demo, Scene, SceneKind


def _state(actions, *, kind=SceneKind.CODEBASE, context=None):
    chunk = Chunk(id="c", text="narration here", actions=actions)
    demo = Demo(title="T", scenes=[Scene(
        id="s", title="Scene Title", kind=kind, context=context or {}, chunks=[chunk]
    )])
    return build_timeline(demo).entries[0].state


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


def test_recorded_string_fragments_continue_text_at_their_timestamps() -> None:
    fragments = ["a", "b", "\n", "c", " ", "d", "\t", "e"]
    actions = [Action(ActionType.CREATE_FILE, {"path": "typed.py"}, timestamp_ms=0)]
    actions.extend(
        Action(ActionType.TYPE_CODE, {"code": fragment}, timestamp_ms=(i + 1) * 100)
        for i, fragment in enumerate(fragments)
    )
    demo = Demo(title="Keys", scenes=[Scene(id="s", chunks=[Chunk(
        id="c", text="type some text", duration_ms=1000, actions=actions
    )])])
    entry = build_timeline(demo).entries[0]
    assert entry.state_at_ms(99).code_lines == []
    assert entry.state_at_ms(100).code_lines == ["a"]
    assert entry.state_at_ms(200).code_lines == ["ab"]
    assert entry.state_at_ms(300).code_lines == ["ab", ""]
    assert entry.state_at_ms(500).code_lines == ["ab", "c "]
    assert entry.state_at_ms(800).code_lines == ["ab", "c d\te"]
    assert entry.state.code_lines == ["ab", "c d\te"]


def test_string_typing_duration_reveals_only_new_text() -> None:
    demo = Demo(title="Text", scenes=[Scene(id="s", chunks=[Chunk(
        id="c", text="continue", duration_ms=1000, actions=[
            Action(ActionType.CREATE_FILE, {"path": "a.py", "code": "x="},
                   timestamp_ms=0),
            Action(ActionType.TYPE_CODE, {"code": "12\n"},
                   timestamp_ms=400, duration_ms=300),
        ],
    )])])
    entry = build_timeline(demo).entries[0]
    assert entry.state_at_ms(399).code_lines == ["x="]
    assert entry.state_at_ms(500).code_lines == ["x=1"]
    assert entry.state_at_ms(600).code_lines == ["x=12"]
    assert entry.state_at_ms(700).code_lines == ["x=12", ""]


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


