"""Tests for shared media value types (democreate.media)."""

from __future__ import annotations

from pathlib import Path

from democreate.media import AudioClip, FrameState
from democreate.schema import SceneKind


def test_audio_clip_to_dict() -> None:
    clip = AudioClip(path=Path("/tmp/a.wav"), duration_ms=1234, text="hi", chunk_id="c1")
    d = clip.to_dict()
    assert d["path"].endswith("a.wav")
    assert d["duration_ms"] == 1234
    assert d["sample_rate"] == 22050
    assert d["chunk_id"] == "c1"


def test_frame_state_defaults() -> None:
    fs = FrameState()
    assert fs.scene_kind is SceneKind.CODEBASE
    assert fs.scale == 1.0
    assert fs.code_lines == [] and fs.terminal_lines == []
    assert fs.cursor_xy is None


def test_frame_state_to_dict_roundtrips_fields() -> None:
    fs = FrameState(
        scene_kind=SceneKind.TERMINAL,
        title="zsh",
        caption="run it",
        terminal_lines=["$ ls", "a b c"],
        cursor_xy=(10, 20),
        scale=1.5,
    )
    d = fs.to_dict()
    assert d["scene_kind"] == "terminal"
    assert d["terminal_lines"] == ["$ ls", "a b c"]
    assert d["cursor_xy"] == [10, 20]
    assert d["scale"] == 1.5
