"""Synthetic real-file paper fixtures, independent of external research assets."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import pytest

__all__ = ["sample_abstract", "sample_figures", "sample_paper"]


def _pdf_literal(text: str) -> str:
    """Escape the special characters in an ASCII PDF literal string."""
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _text_block(text: str, *, y: int, size: int = 11) -> str:
    """Place wrapped Helvetica text at a fixed position in PDF coordinates."""
    lines = wrap(text, width=76)
    commands = [f"BT /F1 {size} Tf 14 TL 50 {y} Td"]
    for index, line in enumerate(lines):
        if index:
            commands.append("T*")
        commands.append(f"({_pdf_literal(line)}) Tj")
    commands.append("ET")
    return "\n".join(commands)


def _content_stream(commands: list[str]) -> bytes:
    """Encode a real, uncompressed PDF stream with its exact byte length."""
    content = ("\n".join(commands) + "\n").encode("ascii")
    return (
        f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
        + content
        + b"endstream"
    )


@pytest.fixture
def sample_abstract() -> str:
    """Return identifiable synthetic prose, not a scholarly abstract."""
    return (
        "This synthetic abstract describes a controlled document used to exercise "
        "PDF metadata, text extraction, and page rendering without external "
        "research assets. The first page separates the abstract from an "
        "introduction, while the second page contains methods and a single figure "
        "caption. Solid colored rectangles provide stable raster landmarks. "
        "These sentences are test data only and report no scholarly observations "
        "or experimental findings."
    )


@pytest.fixture
def sample_paper(tmp_path: Path, sample_abstract: str) -> Path:
    """Write a deterministic two-page PDF using only standard-library code.

    Pages have a 612 by 792 point MediaBox and standard Helvetica text. Red and
    blue rectangles occupy (50, 500, 80, 40) on the first and second pages,
    respectively; at 72 dpi, pixel (60, 260) lies inside each rectangle.
    """
    first_stream = _content_stream(
        [
            _text_block("Portable PDF Fixture", y=740, size=18),
            _text_block("Abstract", y=700, size=14),
            _text_block(sample_abstract, y=676),
            "q 1 0 0 rg 50 500 80 40 re f Q",
            _text_block("1 Introduction", y=450, size=14),
            _text_block(
                "The introduction begins here and is not part of the abstract. "
                "Its only purpose is to mark the first section boundary in this "
                "synthetic document.",
                y=426,
            ),
        ]
    )
    second_stream = _content_stream(
        [
            _text_block("2 Methods", y=740, size=14),
            _text_block(
                "The methods begin on the second page. A fixed page size, "
                "standard Helvetica text, and explicit drawing commands make "
                "this a controlled document fixture.",
                y=716,
            ),
            "q 0 0 1 rg 50 500 80 40 re f Q",
            _text_block("Figure 1. Controlled diagram.", y=450),
        ]
    )
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [4 0 R 6 0 R] /Count 2 >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica "
        b"/Encoding /WinAnsiEncoding >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 3 0 R >> >> /Contents 5 0 R >>",
        first_stream,
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 3 0 R >> >> /Contents 7 0 R >>",
        second_stream,
        b"<< /Title (Portable PDF Fixture) /Author (DemoCreate Tests) >>",
    ]
    document = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(document))
        document.extend(f"{number} 0 obj\n".encode("ascii"))
        document.extend(body)
        document.extend(b"\nendobj\n")
    xref_offset = len(document)
    object_count = len(objects) + 1
    document.extend(f"xref\n0 {object_count}\n".encode("ascii"))
    document.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        document.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    document.extend(
        (
            f"trailer\n<< /Size {object_count} /Root 1 0 R /Info 8 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    target = tmp_path / "sample-paper.pdf"
    target.write_bytes(document)
    return target


@pytest.fixture
def sample_figures(tmp_path: Path) -> Path:
    """Write real red/blue images plus nonimage and nested selection controls."""
    from PIL import Image

    directory = tmp_path / "figures"
    directory.mkdir()
    # Create in reverse name order so collection must sort the selected files.
    with Image.new("RGB", (32, 24), (0, 0, 255)) as image:
        image.save(directory / "b.jpg", quality=100, subsampling=0)
    with Image.new("RGB", (32, 24), (255, 0, 0)) as image:
        image.save(directory / "a.png")
    (directory / "notes.txt").write_text(
        "Synthetic fixture notes; this is not an image.\n", encoding="utf-8"
    )
    nested = directory / "nested"
    nested.mkdir()
    with Image.new("RGB", (32, 24), (0, 255, 0)) as image:
        image.save(nested / "nested.png")
    return directory
