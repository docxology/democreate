"""Native poppler behavior over a controlled, repository-local two-page PDF."""

from __future__ import annotations

from contextlib import chdir
from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError, DemoCreateError
from democreate.paper import pdf as paper_pdf

_HAVE_POPPLER = paper_pdf.poppler_available()
_needs_poppler = pytest.mark.skipif(
    not _HAVE_POPPLER, reason="poppler binaries are unavailable"
)


def test_poppler_available_returns_bool() -> None:
    assert isinstance(paper_pdf.poppler_available(), bool)


@_needs_poppler
def test_pdf_info_decodes_document_metadata(sample_paper: Path) -> None:
    info = paper_pdf.pdf_info(sample_paper)
    assert info["title"] == "Portable PDF Fixture"
    assert info["author"] == "DemoCreate Tests"
    assert all(key == key.lower() for key in info)


@_needs_poppler
def test_pdf_page_count_reads_the_page_tree(sample_paper: Path) -> None:
    assert paper_pdf.pdf_page_count(sample_paper) == 2


@_needs_poppler
def test_extract_text_respects_page_boundaries(sample_paper: Path) -> None:
    first = paper_pdf.extract_text(sample_paper, first=1, last=1)
    second = paper_pdf.extract_text(sample_paper, first=2, last=2)
    assert "1 Introduction" in first and "2 Methods" not in first
    assert "2 Methods" in second and "1 Introduction" not in second


@_needs_poppler
def test_render_page_preserves_geometry_and_visible_content(
    sample_paper: Path, tmp_path: Path
) -> None:
    from PIL import Image

    result = paper_pdf.render_page(sample_paper, 1, tmp_path / "page.png", dpi=72)
    with Image.open(result) as image:
        assert image.size == (612, 792)
        assert image.convert("RGB").getpixel((60, 260)) == (255, 0, 0)


@_needs_poppler
def test_render_pages_preserves_requested_page_order(
    sample_paper: Path, tmp_path: Path
) -> None:
    from PIL import Image

    results = paper_pdf.render_pages(
        sample_paper, tmp_path / "pages", pages=[1, 2], dpi=72, prefix="pg"
    )
    colors = []
    for result in results:
        with Image.open(result) as image:
            colors.append(image.convert("RGB").getpixel((60, 260)))
    assert colors == [(255, 0, 0), (0, 0, 255)]


@_needs_poppler
def test_invalid_and_missing_pdf_paths_raise(tmp_path: Path) -> None:
    bogus = tmp_path / "not_a.pdf"
    bogus.write_text("this is not a pdf", encoding="utf-8")
    for path in (bogus, tmp_path / "missing.pdf"):
        with pytest.raises(DemoCreateError):
            paper_pdf.pdf_info(path)

def test_pdf_info_raises_backend_when_poppler_missing(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(paper_pdf.shutil, "which", lambda _name: None)
    target = tmp_path / "x.pdf"
    target.write_bytes(b"%PDF-1.7")
    with pytest.raises(BackendUnavailableError) as exc:
        paper_pdf.pdf_info(target)
    assert exc.value.backend == "poppler"
    assert exc.value.extra is None  # poppler is an OS binary, not a pip extra


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


@pytest.mark.skipif(not _HAVE_POPPLER, reason="poppler not installed")
def test_render_page_preserves_multidot_destination_identity(tmp_path: Path) -> None:
    from PIL import Image

    pdf = tmp_path / "input.pdf"
    Image.new("RGB", (64, 48), "red").save(pdf, "PDF", resolution=72)
    neighbor = tmp_path / "figure.png"
    Image.new("RGB", (64, 48), "blue").save(neighbor)
    original = neighbor.read_bytes()
    destination = tmp_path / "figure.v1.png"
    result = paper_pdf.render_page(pdf, 1, destination, dpi=72)
    assert result == destination
    with Image.open(result) as image:
        red, green, blue = image.convert("RGB").getpixel((32, 24))
        assert red > 200 and green < 50 and blue < 50
    assert neighbor.read_bytes() == original


@_needs_poppler
@pytest.mark.parametrize("filename", ["ordinary.pdf", "-v", "-", "-h.pdf"])
def test_relative_option_like_pdf_names_use_real_file_bytes(
    sample_paper: Path, tmp_path: Path, filename: str
) -> None:
    from PIL import Image

    original = sample_paper.read_bytes()
    source = tmp_path / filename
    source.write_bytes(original)
    with chdir(tmp_path):
        pdf = Path(filename)
        info = paper_pdf.pdf_info(pdf)
        assert info["title"] == "Portable PDF Fixture"
        assert info["pages"] == "2"
        text = paper_pdf.extract_text(pdf, first=1, last=1)
        assert "1 Introduction" in text and "2 Methods" not in text
        result = paper_pdf.render_page(pdf, 1, Path("-raster.v1.png"), dpi=72)
        assert result == Path("-raster.v1.png")
        with Image.open(result) as image:
            assert image.size == (612, 792)
            assert image.convert("RGB").getpixel((60, 260)) == (255, 0, 0)
        results = paper_pdf.render_pages(
            pdf, Path("-pages"), dpi=72, prefix="-figure.v1"
        )
        assert results == [
            Path("-pages/-figure.v1_001.png"), Path("-pages/-figure.v1_002.png")
        ]
        with Image.open(results[1]) as image:
            assert image.convert("RGB").getpixel((60, 260)) == (0, 0, 255)
    assert source.read_bytes() == original


@_needs_poppler
@pytest.mark.parametrize(
    ("destination", "expected"),
    [
        ("page.png", "page.png"),
        ("figure.v1.png", "figure.v1.png"),
        ("-v.png", "-v.png"),
        ("-", "-.png"),
        ("plain", "plain.png"),
    ],
)
def test_raster_argv_normalization_preserves_relative_return_paths(
    sample_paper: Path, tmp_path: Path, destination: str, expected: str
) -> None:
    from PIL import Image

    with chdir(tmp_path):
        result = paper_pdf.render_page(
            sample_paper, 2, Path(destination), dpi=72
        )
        assert result == Path(expected)
        assert not result.is_absolute()
        with Image.open(result) as image:
            assert image.size == (612, 792)
            assert image.convert("RGB").getpixel((60, 260)) == (0, 0, 255)
