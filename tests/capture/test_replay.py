"""Tests for the input record/replay event model (capture.replay)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from democreate.capture.replay import (
    EventLog,
    InputEvent,
    record_session,
    replay_session,
)
from democreate.errors import BackendUnavailableError
from democreate.schema import ActionType


def _sample_log() -> EventLog:
    return EventLog(
        events=[
            InputEvent(0, "move", {"x": 10, "y": 20}),
            InputEvent(120, "click", {"x": 10, "y": 20, "button": "left"}),
            InputEvent(300, "key", {"key": "a"}),
        ]
    )


def test_input_event_roundtrip() -> None:
    ev = InputEvent(50, "move", {"x": 1, "y": 2})
    assert InputEvent.from_dict(ev.to_dict()) == ev


def test_eventlog_json_roundtrip() -> None:
    log = _sample_log()
    assert EventLog.from_json(log.to_json()) == log


def test_eventlog_json_roundtrip_empty() -> None:
    assert EventLog.from_json(EventLog().to_json()) == EventLog()


def test_to_actions_mapping() -> None:
    actions = _sample_log().to_actions()
    assert [a.type for a in actions] == [
        ActionType.MOVE_MOUSE,
        ActionType.CLICK,
        ActionType.TYPE_CODE,
    ]
    assert actions[0].timestamp_ms == 0
    assert actions[0].params == {"xy": (10, 20)}
    assert actions[2].timestamp_ms == 300
    assert actions[1].params == {"xy": (10, 20), "button": "left"}
    assert actions[2].params == {"code": "a"}


def test_to_actions_skips_unknown_kind() -> None:
    log = EventLog(events=[InputEvent(0, "scroll", {"d": 1}), InputEvent(1, "key", {"key": "z"})])
    actions = log.to_actions()
    assert [a.type for a in actions] == [ActionType.TYPE_CODE]


def test_to_actions_empty() -> None:
    assert EventLog().to_actions() == []


@pytest.mark.parametrize(
    ("key", "code"),
    [
        ("'a'", "a"),
        ('"\'"', "'"),
        (repr("\\"), "\\"),
        ("é", "é"),
        ("Key.space", " "),
        ("Key.enter", "\n"),
        ("Key.tab", "\t"),
    ],
)
def test_recorded_key_decoding(key: str, code: str) -> None:
    actions = EventLog([InputEvent(123, "key", {"key": key})]).to_actions()
    assert len(actions) == 1
    assert actions[0].params == {"code": code}
    assert actions[0].timestamp_ms == 123


@pytest.mark.parametrize(
    "key", ["Key.shift", "Key.ctrl", "Key.backspace", "Key.f1", "'\\x01'", "", "'bad"]
)
def test_unsupported_controls_are_not_inserted_as_text(key: str) -> None:
    assert EventLog([InputEvent(0, "key", {"key": key})]).to_actions() == []


def test_recorded_file_reaches_valid_visible_state(tmp_path: Path) -> None:
    from dataclasses import replace

    from PIL import ImageChops

    from democreate.assembly.compositor import build_timeline
    from democreate.capture.screen import render_frame
    from democreate.schema import Chunk, Demo, Scene, SceneKind

    log = EventLog(
        [
            InputEvent(0, "key", {"key": "'a'"}),
            InputEvent(50, "key", {"key": "'b'"}),
            InputEvent(75, "key", {"key": "Key.shift"}),
            InputEvent(100, "move", {"x": 150, "y": 120}),
            InputEvent(150, "click", {"x": 180, "y": 140, "button": "Button.right"}),
            InputEvent(200, "move", {"x": 220, "y": 160}),
        ]
    )
    recording = tmp_path / "session.json"
    recording.write_text(log.to_json(), encoding="utf-8")
    actions = EventLog.from_json(recording.read_text(encoding="utf-8")).to_actions()
    assert [action.timestamp_ms for action in actions] == [0, 50, 100, 150, 200]
    demo = Demo(
        title="Recorded session",
        scenes=[
            Scene(
                id="editor",
                kind=SceneKind.CODEBASE,
                chunks=[
                    Chunk(id="input", text="Recorded text and cursor.", actions=actions)
                ],
            )
        ],
    )
    demo_file = tmp_path / "demo.json"
    demo_file.write_text(demo.to_json(), encoding="utf-8")
    loaded = Demo.from_json(demo_file.read_text(encoding="utf-8"))
    assert loaded.validate() == []
    state = build_timeline(loaded).entries[-1].state
    assert state.code_lines == ["ab"]
    assert state.cursor_xy == (220, 160)
    image = render_frame(state, (640, 360)).convert("RGB")
    blank = render_frame(
        replace(state, code_lines=[], cursor_xy=None), (640, 360)
    ).convert("RGB")
    assert ImageChops.difference(image, blank).getbbox() is not None


def test_recorded_coordinate_click_drives_browser(tmp_path: Path) -> None:
    from democreate.capture.browser import drive_website_scene
    from democreate.schema import Chunk, Demo, Scene, SceneKind

    recording = tmp_path / "click.json"
    recording.write_text(
        EventLog(
            [InputEvent(50, "click", {"x": 30, "y": 40, "button": "Button.middle"})]
        ).to_json(),
        encoding="utf-8",
    )
    actions = EventLog.from_json(recording.read_text(encoding="utf-8")).to_actions()
    scene = Scene(
        id="browser", kind=SceneKind.WEBSITE, chunks=[Chunk(id="click", actions=actions)]
    )
    assert Demo(title="Click", scenes=[scene]).validate() == []
    assert drive_website_scene(scene) == [
        {"op": "click", "xy": [30, 40], "button": "middle"}
    ]


def test_record_session_unavailable_when_dep_missing() -> None:
    if importlib.util.find_spec("pynput") is not None:  # pragma: no cover
        pytest.skip("pynput installed; unavailability path not applicable")
    with pytest.raises(BackendUnavailableError) as exc:
        record_session(1.0)
    assert exc.value.backend == "pynput"
    assert exc.value.extra == "replay"


def test_replay_session_unavailable_when_dep_missing() -> None:
    if importlib.util.find_spec("pyautogui") is not None:  # pragma: no cover
        pytest.skip("pyautogui installed; unavailability path not applicable")
    with pytest.raises(BackendUnavailableError) as exc:
        replay_session(_sample_log())
    assert exc.value.backend == "pyautogui"
    assert exc.value.extra == "replay"
