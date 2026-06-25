"""Tests for :mod:`democreate.paper.structure`.

The pure extractors are exercised with hand-built text fixtures (an abstract
block, a table-of-contents block that must be rejected, figure-caption lines,
and numbered + named headings). The guarded :func:`summarize_structure` wrapper
is exercised against the real published PDF only when poppler is installed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.paper import pdf as _pdf
from democreate.paper.structure import (
    FigureCaption,
    PaperSection,
    extract_abstract,
    extract_figure_captions,
    extract_sections,
    summarize_structure,
)

_REAL_PDF = Path(
    "/Users/4d/Documents/GitHub/projects/published/"
    "actinf_policy_entanglement_lean/output/pdf/"
    "actinf_policy_entanglement_lean_combined.pdf"
)

_TOC_BLOCK = """\
Contents
Abstract . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 6
Introduction . . . . . . . . . . . . . . . . . . . . . . . . . . . 7
Setup and Assumptions . . . . . . . . . . . . . . . . . . . . . . 16
Results . . . . . . . . . . . . . . . . . . . . . . . . . . . . . 51
References . . . . . . . . . . . . . . . . . . . . . . . . . . . . 99
"""

_ABSTRACT_TEXT = """\
A Coupling-Parameter Framework
Some Author
Institute of Things

Abstract
This manuscript introduces policy entanglement: a controlled deformation of the
usual independent policy posterior by a scalar coupling strength and explicit
compatibility and preference potentials, which preserves the finite active
inference setting while making cross-stream dependence a first-class object.

Introduction
The introduction begins here and should not appear in the abstract at all.
"""


# --------------------------------------------------------------------------- #
# FigureCaption / PaperSection dataclasses
# --------------------------------------------------------------------------- #


def test_figure_caption_to_dict() -> None:
    """A FigureCaption serializes to number/caption keys."""
    assert FigureCaption(3, "Hello world.").to_dict() == {
        "number": 3,
        "caption": "Hello world.",
    }


def test_paper_section_to_dict() -> None:
    """A PaperSection serializes to number/title keys."""
    assert PaperSection("2.1", "Setup").to_dict() == {
        "number": "2.1",
        "title": "Setup",
    }


# --------------------------------------------------------------------------- #
# extract_figure_captions
# --------------------------------------------------------------------------- #


def test_figure_captions_basic_formats() -> None:
    """All three caption formats are recognized and sorted by number."""
    text = (
        "Figure 2: The second figure shows growth. More words follow here.\n"
        "Figure 1. The first figure is simple.\n"
        "Fig. 3 A terse third caption.\n"
    )
    caps = extract_figure_captions(text)
    assert [c.number for c in caps] == [1, 2, 3]
    assert caps[1].caption == "The second figure shows growth."
    assert caps[0].caption == "The first figure is simple."
    assert caps[2].caption == "A terse third caption."


def test_figure_captions_dedup_keeps_longest() -> None:
    """Duplicate figure numbers collapse to the longest caption."""
    text = (
        "Figure 5: Short one.\n"
        "Figure 5: A considerably longer and more descriptive caption here.\n"
    )
    caps = extract_figure_captions(text)
    assert len(caps) == 1
    assert caps[0].number == 5
    assert "considerably longer" in caps[0].caption


def test_figure_captions_respects_max_chars() -> None:
    """Captions are bounded by max_caption_chars."""
    long_tail = "word " * 200  # one long run, no sentence end
    text = f"Figure 7 {long_tail}\n"
    caps = extract_figure_captions(text, max_caption_chars=40)
    assert len(caps) == 1
    assert len(caps[0].caption) <= 40


def test_figure_captions_first_sentence_only() -> None:
    """Only the first sentence of a multi-sentence caption is kept."""
    text = "Figure 9: First sentence here. Second sentence ignored entirely.\n"
    caps = extract_figure_captions(text)
    assert caps[0].caption == "First sentence here."


def test_figure_captions_skip_cross_reference_fragments() -> None:
    """A bare 'Fig. 25' cross-reference with no caption is ignored."""
    text = "Fig. 25 17\nFigure 3: A real caption with content.\n"
    caps = extract_figure_captions(text)
    assert [c.number for c in caps] == [3]


# --------------------------------------------------------------------------- #
# extract_sections
# --------------------------------------------------------------------------- #


def test_sections_numbered_and_named() -> None:
    """Both numbered and named headings are extracted in order."""
    text = (
        "Abstract\n"
        "1 Introduction\n"
        "2.1 Setup\n"
        "3. Results\n"
        "References\n"
    )
    sections = extract_sections(text)
    titles = [(s.number, s.title) for s in sections]
    assert ("", "Abstract") in titles
    assert ("1", "Introduction") in titles
    assert ("2.1", "Setup") in titles
    assert ("3", "Results") in titles
    assert ("", "References") in titles


def test_sections_skip_toc_lines() -> None:
    """Table-of-contents lines (dotted leaders / page numbers) are skipped."""
    sections = extract_sections(_TOC_BLOCK)
    assert sections == []


def test_sections_dedup_by_title() -> None:
    """Repeated headings collapse to the first occurrence."""
    text = "Introduction\nIntroduction\nMethods\n"
    sections = extract_sections(text)
    assert [s.title for s in sections] == ["Introduction", "Methods"]


def test_sections_ignore_long_lines() -> None:
    """A long prose line that starts with a number is not a heading."""
    text = (
        "1 Introduction\n"
        "2 streams tied to different effectors and sensory channels make "
        "coordinated action possible across many planning horizons indeed.\n"
    )
    sections = extract_sections(text)
    assert [s.title for s in sections] == ["Introduction"]


# --------------------------------------------------------------------------- #
# extract_abstract
# --------------------------------------------------------------------------- #


def test_abstract_after_marker() -> None:
    """The real abstract is captured and the introduction is excluded."""
    abstract = extract_abstract(_ABSTRACT_TEXT)
    assert abstract.startswith("This manuscript introduces policy entanglement")
    assert "introduction begins here" not in abstract.lower()
    assert "Some Author" not in abstract


def test_abstract_rejects_toc_and_falls_back() -> None:
    """A TOC after the marker is rejected; a later prose paragraph is used."""
    title = "Policy Entanglement Framework"
    real_para = (
        "The central result is a free-energy decomposition that separates "
        "ordinary per-stream free energy from coupling preference terms and the "
        "information cost of leaving independence, which is the multi-information."
    )
    text = (
        f"{title}\n\n"
        "Contents\n"
        "Abstract\n"
        "Abstract . . . . . . . . . . . . . . . . . . . . . . 6\n"
        "Introduction . . . . . . . . . . . . . . . . . . . . 7\n"
        "Results . . . . . . . . . . . . . . . . . . . . . . 51\n"
        "References . . . . . . . . . . . . . . . . . . . . . 99\n\n"
        f"{real_para}\n"
    )
    abstract = extract_abstract(text)
    assert "free-energy decomposition" in abstract
    assert "." * 3 not in abstract


def test_abstract_not_the_title() -> None:
    """The fallback skips a paragraph that merely repeats the title."""
    title = "A Very Specific And Unique Paper Title About Coupling"
    text = (
        f"{title}\n\n"
        "Contents\n"
        ". . . . . . 1\n. . . . . . 2\n. . . . . . 3\n\n"
        f"{title} {title} {title} {title} {title} {title}\n\n"
        "This is the genuine first substantial paragraph of prose that carries "
        "real semantic content about the deformation framework and its results, "
        "well beyond two hundred characters so the fallback accepts it as good.\n"
    )
    abstract = extract_abstract(text)
    assert abstract.lower().startswith("this is the genuine")


def test_abstract_max_chars() -> None:
    """The abstract is bounded by max_chars."""
    body = "Real prose sentence number {n} carries content. " * 80
    text = f"Title Line\n\nAbstract\n{body}\nIntroduction\n"
    abstract = extract_abstract(text, max_chars=120)
    assert len(abstract) <= 120


# --------------------------------------------------------------------------- #
# summarize_structure (guarded — real PDF)
# --------------------------------------------------------------------------- #


def test_summarize_structure_requires_poppler(monkeypatch: pytest.MonkeyPatch) -> None:
    """summarize_structure raises BackendUnavailableError without poppler."""
    from democreate.errors import BackendUnavailableError

    monkeypatch.setattr(_pdf.shutil, "which", lambda _binary: None)
    with pytest.raises(BackendUnavailableError):
        summarize_structure(_REAL_PDF)


@pytest.mark.skipif(
    not (_pdf.poppler_available() and _REAL_PDF.is_file()),
    reason="poppler not installed or real test PDF absent",
)
def test_summarize_structure_real_pdf() -> None:
    """Against the real PDF: real abstract, figures, and an Introduction."""
    result = summarize_structure(_REAL_PDF)
    abstract = result["abstract"]
    assert isinstance(abstract, str)
    assert len(abstract) >= 200
    # The abstract must NOT be just the title block.
    assert "Policy Entanglement in Active Inference" not in abstract[:80]
    assert "active inference" in abstract.lower()
    # The leading "Abstract" label must be stripped, not leak into the prose.
    assert not abstract.lower().startswith("abstract")

    captions = result["figure_captions"]
    assert captions
    assert all(isinstance(c, FigureCaption) for c in captions)
    assert all(c.number > 0 and c.caption for c in captions)

    sections = result["sections"]
    assert sections
    titles = {s.title.lower() for s in sections}
    assert any("introduction" in t for t in titles)
