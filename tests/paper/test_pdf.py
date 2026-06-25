"""Tests for :mod:`democreate.paper.pdf` against a real 170-page PDF.

These exercise the poppler CLI wrappers on a genuine research-paper PDF when
poppler is installed, and verify the missing-backend guard otherwise.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError, DemoCreateError
from democreate.paper import pdf as paper_pdf

_REAL_PDF = Path(
    "/Users/4d/Documents/GitHub/projects/published/"
    "actinf_policy_entanglement_lean/output/pdf/"
    "actinf_policy_entanglement_lean_combined.pdf"
)

_HAVE_POPPLER = paper_pdf.poppler_available()
_HAVE_PDF = _REAL_PDF.is_file()

_needs_poppler = pytest.mark.skipif(
    not (_HAVE_POPPLER and _HAVE_PDF),
    reason="poppler binaries or the real test PDF are unavailable",
)


def test_poppler_available_returns_bool() -> None:
    assert isinstance(paper_pdf.poppler_available(), bool)


@_needs_poppler
def test_pdf_info_has_policy_entanglement_title() -> None:
    info = paper_pdf.pdf_info(_REAL_PDF)
    assert "title" in info
    assert "Policy Entanglement" in info["title"]
    # keys are lowercased
    assert all(key == key.lower() for key in info)


@_needs_poppler
def test_pdf_page_count_is_170() -> None:
    assert paper_pdf.pdf_page_count(_REAL_PDF) == 170


@_needs_poppler
def test_extract_text_first_page_mentions_active_inference() -> None:
    text = paper_pdf.extract_text(_REAL_PDF, first=1, last=1)
    assert "Active Inference" in text


@_needs_poppler
def test_render_page_writes_nonempty_png(tmp_path: Path) -> None:
    from PIL import Image

    out = tmp_path / "p1.png"
    result = paper_pdf.render_page(_REAL_PDF, 1, out, dpi=72)
    assert result.is_file()
    assert result.suffix == ".png"
    assert result.stat().st_size > 0
    with Image.open(result) as img:
        width, height = img.size
    assert width > 0 and height > 0


@_needs_poppler
def test_render_pages_writes_sorted_pngs(tmp_path: Path) -> None:
    from PIL import Image

    out_dir = tmp_path / "pages"
    results = paper_pdf.render_pages(
        _REAL_PDF, out_dir, pages=[1, 2], dpi=60, prefix="pg"
    )
    assert len(results) == 2
    assert results == sorted(results)
    for png in results:
        assert png.is_file()
        assert png.stat().st_size > 0
        assert png.name.startswith("pg_")
        with Image.open(png) as img:
            assert img.size[0] > 0


@_needs_poppler
def test_non_pdf_path_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "not_a.pdf"
    bogus.write_text("this is not a pdf", encoding="utf-8")
    missing = tmp_path / "missing.pdf"
    # A missing file raises DemoCreateError before any subprocess runs.
    with pytest.raises(DemoCreateError):
        paper_pdf.pdf_info(missing)


def test_pdf_info_raises_backend_when_poppler_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(paper_pdf.shutil, "which", lambda _name: None)
    target = tmp_path / "x.pdf"
    target.write_bytes(b"%PDF-1.7")
    with pytest.raises(BackendUnavailableError) as exc:
        paper_pdf.pdf_info(target)
    assert exc.value.backend == "poppler"
    assert exc.value.extra == "pdf"


def test_extract_text_raises_backend_when_poppler_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(paper_pdf.shutil, "which", lambda _name: None)
    target = tmp_path / "x.pdf"
    target.write_bytes(b"%PDF-1.7")
    with pytest.raises(BackendUnavailableError):
        paper_pdf.extract_text(target)


def test_render_page_raises_backend_when_poppler_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(paper_pdf.shutil, "which", lambda _name: None)
    target = tmp_path / "x.pdf"
    target.write_bytes(b"%PDF-1.7")
    with pytest.raises(BackendUnavailableError):
        paper_pdf.render_page(target, 1, tmp_path / "out.png")


def test_render_pages_raises_backend_when_poppler_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(paper_pdf.shutil, "which", lambda _name: None)
    target = tmp_path / "x.pdf"
    target.write_bytes(b"%PDF-1.7")
    with pytest.raises(BackendUnavailableError):
        paper_pdf.render_pages(target, tmp_path / "out")
