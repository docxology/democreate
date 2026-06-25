"""Tests for building a demo from a research paper (paper.script)."""

from __future__ import annotations

from pathlib import Path

from democreate.paper.extract import PaperSummary
from democreate.paper.script import build_paper_demo, chunk_sentences


def test_chunk_sentences_groups_by_words() -> None:
    text = "One two three. Four five six seven eight. Nine ten."
    chunks = chunk_sentences(text, max_words=5)
    assert len(chunks) >= 2
    assert all(c for c in chunks)
    # rejoined content preserves the words
    assert "One two three" in chunks[0]


def test_chunk_sentences_empty() -> None:
    assert chunk_sentences("") == []
    assert chunk_sentences("   \n  ") == []


def test_chunk_sentences_collapses_whitespace() -> None:
    out = chunk_sentences("Hello   world.\n\nNext  one.", max_words=50)
    assert out == ["Hello world. Next one."]


def _summary(**kw) -> PaperSummary:
    base = dict(
        title="A Great Paper",
        authors="Ada Lovelace",
        abstract="We do a thing. It works well. We conclude.",
        page_count=12,
        figures=[],
        pdf_path="/tmp/x.pdf",
    )
    base.update(kw)
    return PaperSummary(**base)


def test_build_paper_demo_minimal() -> None:
    demo = build_paper_demo(_summary())
    assert demo.is_valid()
    assert demo.width == 1920 and demo.height == 1080
    sections = [s.context.get("section", "") for s in demo.scenes]
    assert "Paper" in sections  # title card
    assert "Abstract" in sections
    assert demo.metadata["kind"] == "paper"


def test_build_paper_demo_with_figures_and_pages(tmp_path: Path) -> None:
    figs = []
    for i in range(3):
        p = tmp_path / f"fig{i}.png"
        p.write_bytes(b"\x89PNG\r\n")  # path presence is what matters here
        figs.append(p)
    page = tmp_path / "page_001.png"
    page.write_bytes(b"\x89PNG\r\n")
    demo = build_paper_demo(_summary(figures=figs), page_images=[page], max_figures=2)
    ids = [s.id for s in demo.scenes]
    assert "frontpage" in ids  # first page used as a background scene
    assert ids.count("figure-1") == 1 and "figure-2" in ids
    assert "figure-3" not in ids  # capped at max_figures
    # the figure scenes carry the background image
    fig_scene = next(s for s in demo.scenes if s.id == "figure-1")
    assert fig_scene.context["background_image"].endswith("fig0.png")


def test_build_paper_demo_with_codebase() -> None:
    summaries = [
        type("M", (), {"name": "walker", "path": "src/codebase/walker.py"})(),
        type("M", (), {"name": "tts", "path": "src/narration/tts.py"})(),
    ]
    demo = build_paper_demo(_summary(), code_summaries=summaries)
    sections = [s.context.get("section", "") for s in demo.scenes]
    assert "Codebase" in sections


def test_group_modules_columns() -> None:
    from democreate.paper.script import _group_modules

    summaries = [
        {"name": "a", "path": "src/x/a.py"},
        {"name": "b", "path": "src/x/b.py"},
        {"name": "c", "path": "src/y/c.py"},
    ]
    cols = _group_modules(summaries)
    names = dict(cols)
    assert "x" in names and "y" in names
    assert sorted(names["x"]) == ["a", "b"]
