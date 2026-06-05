"""Tests for :mod:`democreate.paper.extract` against real paper assets."""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.paper import pdf as paper_pdf
from democreate.paper.extract import (
    PaperSummary,
    collect_figures,
    summarize_paper,
)

_BASE = Path(
    "/Users/4d/Documents/GitHub/projects/published/"
    "actinf_policy_entanglement_lean/output"
)
_REAL_PDF = _BASE / "pdf" / "actinf_policy_entanglement_lean_combined.pdf"
_FIGURES_DIR = _BASE / "figures"

_HAVE_POPPLER = paper_pdf.poppler_available()
_HAVE_PDF = _REAL_PDF.is_file()

_needs_poppler = pytest.mark.skipif(
    not (_HAVE_POPPLER and _HAVE_PDF),
    reason="poppler binaries or the real test PDF are unavailable",
)


def test_collect_figures_sorted_and_pngs() -> None:
    if not _FIGURES_DIR.is_dir():
        pytest.skip("figures directory unavailable")
    figs = collect_figures(_FIGURES_DIR)
    assert figs, "expected at least one figure"
    assert figs == sorted(figs)
    assert all(f.suffix.lower() in (".png", ".jpg", ".jpeg") for f in figs)
    assert all(f.is_file() for f in figs)


def test_collect_figures_limit(tmp_path: Path) -> None:
    for idx in range(5):
        (tmp_path / f"fig_{idx}.png").write_bytes(b"\x89PNG\r\n")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "nested.png").write_bytes(b"\x89PNG\r\n")
    figs = collect_figures(tmp_path, limit=3)
    assert len(figs) == 3
    # non-recursive: nested file excluded
    assert all(f.parent == tmp_path for f in figs)


def test_collect_figures_missing_dir(tmp_path: Path) -> None:
    assert collect_figures(tmp_path / "nope") == []


@_needs_poppler
def test_summarize_real_paper() -> None:
    summary = summarize_paper(_REAL_PDF, figures_dir=_FIGURES_DIR)
    assert isinstance(summary, PaperSummary)
    assert "Policy Entanglement" in summary.title
    assert summary.page_count == 170
    assert summary.abstract  # non-empty
    assert len(summary.abstract) <= 900
    if _FIGURES_DIR.is_dir():
        assert summary.figures
        assert all(f.is_file() and f.suffix.lower() == ".png" for f in summary.figures)
    assert summary.pdf_path.endswith(".pdf")


@_needs_poppler
def test_summary_to_dict_round_trips_keys() -> None:
    summary = summarize_paper(_REAL_PDF, figures_dir=_FIGURES_DIR)
    data = summary.to_dict()
    assert set(data) == {
        "title",
        "authors",
        "abstract",
        "page_count",
        "figures",
        "pdf_path",
    }
    assert data["page_count"] == 170
    assert all(isinstance(fig, str) for fig in data["figures"])


@_needs_poppler
def test_summarize_respects_max_abstract_chars() -> None:
    summary = summarize_paper(
        _REAL_PDF, figures_dir=_FIGURES_DIR, max_abstract_chars=120
    )
    assert len(summary.abstract) <= 120
