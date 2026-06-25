"""Tests for asciicast v2 terminal recordings (capture.terminal)."""

from __future__ import annotations

import json

from democreate.capture.terminal import (
    AsciicastEvent,
    AsciicastRecording,
    record_commands,
    recording_to_frame_states,
)
from democreate.schema import SceneKind


def test_record_commands_emits_input_and_output() -> None:
    rec = record_commands([("ls", "a.txt\nb.txt"), ("pwd", "/home")])
    kinds = [e.kind for e in rec.events]
    assert kinds == ["i", "o", "i", "o"]
    assert rec.events[0].data.startswith("$ ls")


def test_record_commands_custom_prompt() -> None:
    rec = record_commands([("echo hi", "hi")], prompt="> ")
    assert rec.events[0].data.startswith("> echo hi")


def test_record_commands_empty_output_has_no_output_event() -> None:
    rec = record_commands([("clear", "")])
    assert [e.kind for e in rec.events] == ["i"]


def test_timestamps_are_monotonic() -> None:
    rec = record_commands([("a", "out"), ("b", "out"), ("c", "out")])
    times = [e.time for e in rec.events]
    assert times == sorted(times)


def test_duration_is_last_event_time() -> None:
    rec = record_commands([("a", "x")])
    assert rec.duration() == rec.events[-1].time


def test_duration_empty_recording_is_zero() -> None:
    assert AsciicastRecording().duration() == 0.0


def test_to_json_header_first_then_arrays() -> None:
    rec = record_commands([("ls", "out")])
    lines = rec.to_json().splitlines()
    header = json.loads(lines[0])
    assert header == {"version": 2, "width": 80, "height": 24}
    for line in lines[1:]:
        item = json.loads(line)
        assert isinstance(item, list) and len(item) == 3


def test_roundtrip_equality() -> None:
    rec = record_commands([("ls -la", "total 0"), ("echo done", "done")])
    again = AsciicastRecording.from_json(rec.to_json())
    assert again == rec


def test_roundtrip_custom_geometry() -> None:
    rec = AsciicastRecording(
        width=120,
        height=40,
        events=[AsciicastEvent(0.0, "o", "hello\n"), AsciicastEvent(1.5, "i", "x")],
    )
    assert AsciicastRecording.from_json(rec.to_json()) == rec


def test_from_json_ignores_blank_lines() -> None:
    rec = record_commands([("a", "b")])
    text = rec.to_json() + "\n\n"
    assert AsciicastRecording.from_json(text) == rec


def test_from_json_empty_raises() -> None:
    import pytest

    with pytest.raises(ValueError):
        AsciicastRecording.from_json("   \n  ")


def test_event_to_from_list_roundtrip() -> None:
    ev = AsciicastEvent(1.25, "o", "data")
    assert AsciicastEvent.from_list(ev.to_list()) == ev


def test_equality_rejects_non_recording() -> None:
    assert (AsciicastRecording() == 5) is False


def test_recording_to_frame_states() -> None:
    rec = record_commands([("ls", "a.txt\nb.txt")])
    states = recording_to_frame_states(rec)
    assert len(states) == len(rec.events)
    assert all(s.scene_kind == SceneKind.TERMINAL for s in states)
    # the final frame should contain accumulated output lines
    assert "a.txt" in states[-1].terminal_lines
    assert "b.txt" in states[-1].terminal_lines


def test_recording_to_frame_states_empty() -> None:
    assert recording_to_frame_states(AsciicastRecording()) == []


def test_frame_states_accumulate() -> None:
    rec = record_commands([("a", "out1"), ("b", "out2")])
    states = recording_to_frame_states(rec)
    # later states should have at least as many lines as earlier ones
    counts = [len(s.terminal_lines) for s in states]
    assert counts == sorted(counts)
