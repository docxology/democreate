"""Tests for the declarative demo spine (democreate.schema)."""

from __future__ import annotations

import pytest

from democreate.schema import (
    DEFAULT_WPM,
    SCHEMA_VERSION,
    Action,
    ActionType,
    Chunk,
    Demo,
    Scene,
    SceneKind,
    WordTimestamp,
)


def test_action_enum_coercion_from_string() -> None:
    a = Action("open_file", {"path": "x.py"})
    assert a.type is ActionType.OPEN_FILE


def test_action_roundtrip_omits_unset_optionals() -> None:
    a = Action(ActionType.TYPE_CODE, {"code": "x=1"})
    d = a.to_dict()
    assert "trigger_word" not in d and "timestamp_ms" not in d
    assert Action.from_dict(d) == a


def test_action_roundtrip_with_all_fields() -> None:
    a = Action(
        ActionType.ZOOM,
        {"scale": 2},
        trigger_word="here",
        timestamp_ms=1200,
        duration_ms=500,
    )
    assert Action.from_dict(a.to_dict()) == a


def test_chunk_word_count_and_estimate() -> None:
    c = Chunk(id="c", text="one two three four five")
    assert c.word_count() == 5
    # 5 words at default wpm
    expected = int(round(5 / DEFAULT_WPM * 60_000))
    assert c.estimated_duration_ms() == expected


def test_empty_chunk_has_minimum_beat() -> None:
    assert Chunk(id="c", text="").estimated_duration_ms() == 300


def test_scene_enum_coercion_and_duration() -> None:
    s = Scene(id="s", title="T", kind="terminal")
    assert s.kind is SceneKind.TERMINAL
    s.chunks.append(Chunk(id="c", text="a b c"))
    assert s.estimated_duration_ms() == s.chunks[0].estimated_duration_ms()


def test_word_timestamp_roundtrip() -> None:
    w = WordTimestamp("hello", 100, 400)
    assert WordTimestamp.from_dict(w.to_dict()) == w


def _demo() -> Demo:
    s = Scene(id="s1", title="Intro", kind=SceneKind.CODEBASE)
    s.chunks.append(
        Chunk(
            id="c1",
            text="open the file please",
            actions=[Action(ActionType.OPEN_FILE, {"path": "m.py"}, trigger_word="open")],
        )
    )
    return Demo(title="T", scenes=[s])


def test_demo_iterators() -> None:
    d = _demo()
    assert len(d.iter_chunks()) == 1
    assert len(d.iter_actions()) == 1
    assert d.estimated_duration_ms() > 0


def test_demo_roundtrips() -> None:
    d = _demo()
    assert Demo.from_dict(d.to_dict()) == d
    assert Demo.from_json(d.to_json()) == d
    assert Demo.from_yaml(d.to_yaml()) == d
    assert d.to_dict()["schema_version"] == SCHEMA_VERSION


def test_validate_clean_demo() -> None:
    assert _demo().validate() == []
    assert _demo().is_valid()


def test_validate_flags_empty_title() -> None:
    assert any("title" in p for p in Demo(title="  ").validate())


def test_validate_flags_bad_geometry_and_fps() -> None:
    d = _demo()
    d.width = 0
    d.fps = 0
    problems = d.validate()
    assert any("geometry" in p for p in problems)
    assert any("fps" in p for p in problems)


def test_validate_flags_duplicate_scene_ids() -> None:
    s1 = Scene(id="dup")
    s2 = Scene(id="dup")
    assert any("duplicate scene" in p for p in Demo(title="T", scenes=[s1, s2]).validate())


def test_validate_flags_duplicate_chunk_ids() -> None:
    s = Scene(id="s")
    s.chunks = [Chunk(id="dup"), Chunk(id="dup")]
    assert any("duplicate chunk" in p for p in Demo(title="T", scenes=[s]).validate())


def test_demo_not_equal_to_other_type() -> None:
    assert (_demo() == 42) is False


def test_from_dict_defaults() -> None:
    d = Demo.from_dict({"title": "Only Title"})
    assert d.width == 1920 and d.height == 1080 and d.fps == 30
    assert d.scenes == []


@pytest.mark.parametrize("kind", list(SceneKind))
def test_all_scene_kinds_roundtrip(kind: SceneKind) -> None:
    s = Scene(id="s", kind=kind)
    assert Scene.from_dict(s.to_dict()).kind is kind
