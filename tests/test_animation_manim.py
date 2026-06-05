"""Tests for democreate.animation.manim_scenes (pure spec + guarded render)."""

from __future__ import annotations

import importlib.util
import json

import pytest

from democreate.animation.manim_scenes import build_code_scene_spec, render_manim_scene
from democreate.errors import BackendUnavailableError


def test_build_spec_basic_shape(sample_python_source: str) -> None:
    spec = build_code_scene_spec(sample_python_source, title="Tour", language="python")
    assert spec["kind"] == "code_walkthrough"
    assert spec["title"] == "Tour"
    assert spec["language"] == "python"
    assert spec["code"] == sample_python_source
    assert isinstance(spec["steps"], list)
    assert spec["steps"]


def test_build_spec_line_count_matches_steps(sample_python_source: str) -> None:
    spec = build_code_scene_spec(sample_python_source)
    n_lines = len(sample_python_source.splitlines())
    assert spec["line_count"] == n_lines
    assert len(spec["steps"]) == n_lines


def test_build_spec_steps_ordered_and_numbered() -> None:
    spec = build_code_scene_spec("a = 1\nb = 2\nc = 3")
    for i, step in enumerate(spec["steps"]):
        assert step["order"] == i
        assert step["line_no"] == i + 1
        assert step["action"] == "reveal_line"
        assert step["duration_ms"] > 0


def test_build_spec_start_times_cumulative() -> None:
    spec = build_code_scene_spec("aaa\nbbbbbb\nc")
    running = 0
    for step in spec["steps"]:
        assert step["start_ms"] == running
        running += step["duration_ms"]
    assert spec["total_duration_ms"] == running


def test_build_spec_longer_line_longer_duration() -> None:
    spec = build_code_scene_spec("x\n" + "y" * 50)
    short, long = spec["steps"][0], spec["steps"][1]
    assert long["duration_ms"] > short["duration_ms"]


def test_build_spec_empty_code() -> None:
    spec = build_code_scene_spec("")
    assert spec["line_count"] == 0
    assert spec["steps"] == []
    assert spec["total_duration_ms"] == 0


def test_build_spec_json_serializable(sample_python_source: str) -> None:
    spec = build_code_scene_spec(sample_python_source, title="X")
    dumped = json.dumps(spec)
    assert json.loads(dumped) == spec


def test_build_spec_default_title() -> None:
    spec = build_code_scene_spec("a = 1")
    assert spec["title"] == ""


@pytest.mark.skipif(
    importlib.util.find_spec("manim") is not None,
    reason="manim is installed; the unavailable-backend path does not apply",
)
def test_render_without_manim_raises(tmp_path) -> None:
    spec = build_code_scene_spec("a = 1")
    with pytest.raises(BackendUnavailableError) as exc:
        render_manim_scene(spec, tmp_path / "out.mp4")
    assert exc.value.backend == "manim"
    assert exc.value.extra == "animation"


def test_render_with_manim_if_installed(tmp_path) -> None:
    pytest.importorskip("manim")
    # When manim is present, the guard passes; the backend is not yet wired up.
    spec = build_code_scene_spec("a = 1")
    with pytest.raises((NotImplementedError, BackendUnavailableError)):
        render_manim_scene(spec, tmp_path / "out.mp4")
