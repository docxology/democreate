"""Tests for the document-format exports (markdown / json / chapters / pdf)."""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError
from democreate.export.formats import export_pdf, to_chapters, to_json, to_markdown
from democreate.schema import Demo, Scene


def test_to_markdown_has_title_and_scenes(sample_demo: Demo) -> None:
    md = to_markdown(sample_demo)
    assert md.startswith(f"# {sample_demo.title}")
    for scene in sample_demo.scenes:
        assert f"## {scene.title}" in md
    # narration text appears
    assert "We begin by opening the main entry point" in md
    # actions rendered as bullets
    assert "- open file" in md
    assert md.endswith("\n")


def test_to_markdown_includes_trigger_words(sample_demo: Demo) -> None:
    md = to_markdown(sample_demo)
    assert "opening" in md  # trigger word surfaced


def test_to_markdown_empty_demo() -> None:
    demo = Demo(title="Nothing Here")
    md = to_markdown(demo)
    assert md == "# Nothing Here\n"


def test_to_markdown_scene_without_actions() -> None:
    from democreate.schema import Chunk

    demo = Demo(
        title="T",
        scenes=[Scene(id="s", title="S", chunks=[Chunk(id="c", text="Just words.")])],
    )
    md = to_markdown(demo)
    assert "Just words." in md
    assert "## S" in md


def test_to_json_round_trips(sample_demo: Demo) -> None:
    js = to_json(sample_demo)
    restored = Demo.from_json(js)
    assert restored == sample_demo


def test_to_json_indent_passthrough(sample_demo: Demo) -> None:
    compact = to_json(sample_demo, indent=0)
    assert Demo.from_json(compact) == sample_demo


def test_to_chapters_count_matches_scenes(sample_demo: Demo) -> None:
    chapters = to_chapters(sample_demo)
    assert len(chapters) == len(sample_demo.scenes)
    for ch, scene in zip(chapters, sample_demo.scenes, strict=True):
        assert ch["scene_id"] == scene.id
        assert ch["title"] == scene.title
        assert "start_ms" in ch


def test_to_chapters_monotonic_starts(sample_demo: Demo) -> None:
    chapters = to_chapters(sample_demo)
    starts = [c["start_ms"] for c in chapters]
    assert starts[0] == 0
    assert starts == sorted(starts)


def test_to_chapters_respects_synced_start(sample_demo: Demo) -> None:
    sample_demo.scenes[1].chunks[0].start_ms = 9999
    chapters = to_chapters(sample_demo)
    assert chapters[1]["start_ms"] == 9999


def test_to_chapters_empty_demo() -> None:
    assert to_chapters(Demo(title="X")) == []


def test_to_chapters_uses_scene_id_when_no_title() -> None:
    demo = Demo(title="T", scenes=[Scene(id="sceneA")])
    chapters = to_chapters(demo)
    assert chapters[0]["title"] == "sceneA"


def test_export_pdf_without_engine(sample_demo: Demo, tmp_path: Path, monkeypatch) -> None:
    import democreate.export.formats as formats_mod

    monkeypatch.setattr(formats_mod, "_has_pdf_engine", lambda: False)
    with pytest.raises(BackendUnavailableError) as exc:
        export_pdf(sample_demo, tmp_path / "out.pdf")
    assert exc.value.backend == "pdf"
