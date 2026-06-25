"""Tests for the input record/replay event model (capture.replay)."""

from __future__ import annotations

import importlib.util

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
    assert actions[0].params == {"x": 10, "y": 20}
    assert actions[2].timestamp_ms == 300


def test_to_actions_skips_unknown_kind() -> None:
    log = EventLog(events=[InputEvent(0, "scroll", {"d": 1}), InputEvent(1, "key", {"key": "z"})])
    actions = log.to_actions()
    assert [a.type for a in actions] == [ActionType.TYPE_CODE]


def test_to_actions_empty() -> None:
    assert EventLog().to_actions() == []


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
