"""Paper summaries and figure selection over real, self-contained fixtures."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from democreate.paper import pdf as paper_pdf
from democreate.paper.extract import collect_figures, summarize_paper

_needs_poppler = pytest.mark.skipif(
    not paper_pdf.poppler_available(), reason="poppler binaries are unavailable"
)


def test_collect_figures_filters_and_sorts_nonrecursively(sample_figures: Path) -> None:
    assert collect_figures(sample_figures) == [
        sample_figures / "a.png", sample_figures / "b.jpg"
    ]


def test_collect_figures_limit(tmp_path: Path) -> None:
    from PIL import Image

    for idx in range(5):
        Image.new("RGB", (2, 2), "red").save(tmp_path / f"fig_{idx}.png")
    (tmp_path / "notes.txt").write_text("ignore me", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    Image.new("RGB", (2, 2), "blue").save(tmp_path / "sub/nested.png")
    assert collect_figures(tmp_path, limit=3) == [
        tmp_path / f"fig_{idx}.png" for idx in range(3)
    ]
    assert collect_figures(tmp_path, limit=0) == []


def test_collect_figures_missing_dir(tmp_path: Path) -> None:
    assert collect_figures(tmp_path / "nope") == []


@_needs_poppler
def test_summarize_pdf_exports_actual_metadata_abstract_and_assets(
    sample_paper: Path, sample_figures: Path, sample_abstract: str
) -> None:
    summary = summarize_paper(sample_paper, figures_dir=sample_figures)
    data = json.loads(json.dumps(summary.to_dict()))
    assert data == {
        "title": "Portable PDF Fixture",
        "authors": "DemoCreate Tests",
        "abstract": sample_abstract,
        "page_count": 2,
        "figures": [str(sample_figures / "a.png"), str(sample_figures / "b.jpg")],
        "pdf_path": str(sample_paper.resolve()),
    }


@_needs_poppler
def test_summarize_truncates_the_abstract_not_other_text(
    sample_paper: Path, sample_abstract: str
) -> None:
    summary = summarize_paper(sample_paper, max_abstract_chars=120)
    assert summary.abstract == sample_abstract[:120].strip()
