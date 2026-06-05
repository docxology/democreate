"""Structured summarization of a research paper from its PDF + figures.

Turns a PDF into a small, render-ready :class:`PaperSummary`: title, authors,
abstract, page count, and a list of figure images. Metadata comes from
``pdfinfo`` (via :mod:`democreate.paper.pdf`); the abstract is extracted
heuristically from the first pages of text. Figures are collected from a sibling
directory of exported images — no PDF figure extraction is attempted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .._logging import get_logger
from . import pdf as _pdf

__all__ = ["PaperSummary", "collect_figures", "summarize_paper"]

_log = get_logger(__name__)

_FIGURE_SUFFIXES = (".png", ".jpg", ".jpeg")
_ABSTRACT_RE = re.compile(r"\babstract\b", re.IGNORECASE)
_INTRO_RE = re.compile(r"\bintroduction\b", re.IGNORECASE)
_DOT_LEADER_RE = re.compile(r"(?:\.{3,}|(?:\.\s*){3,})")
_TRAILING_PAGE_RE = re.compile(r"\b\d+\s*$")
_WS_RE = re.compile(r"\s+")

# A real abstract is a paragraph; anything shorter is TOC noise / a page number.
_MIN_ABSTRACT_CHARS = 80
# How deep to look for an abstract when the first pages are a table of contents.
_DEEP_ABSTRACT_PAGES = 8


@dataclass
class PaperSummary:
    """A compact, render-ready summary of a research paper.

    Attributes:
        title: Paper title (from PDF metadata).
        authors: Author string (from PDF metadata).
        abstract: Cleaned, length-bounded abstract text.
        page_count: Number of pages in the PDF.
        figures: Paths to collected figure images.
        pdf_path: Absolute string path to the source PDF.
    """

    title: str
    authors: str
    abstract: str
    page_count: int
    figures: list[Path] = field(default_factory=list)
    pdf_path: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-friendly dict (figure paths as strings).

        Returns:
            Mapping with keys ``title``, ``authors``, ``abstract``,
            ``page_count``, ``figures`` and ``pdf_path``.
        """
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "page_count": self.page_count,
            "figures": [str(fig) for fig in self.figures],
            "pdf_path": self.pdf_path,
        }


def collect_figures(figures_dir: Path, *, limit: int | None = None) -> list[Path]:
    """Collect sorted figure images from a directory (non-recursive).

    Args:
        figures_dir: Directory to scan for ``*.png``/``*.jpg``/``*.jpeg`` files.
        limit: Optional maximum number of figures to return.

    Returns:
        Sorted list of image paths; empty if the directory is absent.
    """
    figures_dir = Path(figures_dir)
    if not figures_dir.is_dir():
        return []
    found = [
        entry
        for entry in figures_dir.iterdir()
        if entry.is_file() and entry.suffix.lower() in _FIGURE_SUFFIXES
    ]
    found.sort()
    if limit is not None:
        found = found[:limit]
    return found


def _clean(text: str) -> str:
    """Collapse runs of whitespace into single spaces and strip.

    Args:
        text: Raw text to normalize.

    Returns:
        Whitespace-normalized text.
    """
    return _WS_RE.sub(" ", text).strip()


def _looks_like_toc(text: str) -> bool:
    """Return ``True`` when ``text`` looks like a table-of-contents fragment."""
    cleaned = _clean(text)
    if not cleaned:
        return False
    if _DOT_LEADER_RE.search(text):
        return True
    if _TRAILING_PAGE_RE.search(cleaned):
        alpha = sum(char.isalpha() for char in cleaned)
        non_alpha = sum(not char.isalpha() and not char.isspace() for char in cleaned)
        if len(cleaned) <= 140 and alpha <= max(12, non_alpha * 4):
            return True
    alpha = sum(char.isalpha() for char in cleaned)
    digits = sum(char.isdigit() for char in cleaned)
    punctuation = sum(
        not char.isalnum() and not char.isspace()
        for char in cleaned
    )
    prose_chars = alpha + digits
    return prose_chars > 0 and alpha * 2 < digits + punctuation


def _extract_abstract(text: str, *, max_chars: int) -> str:
    """Heuristically pull an abstract from leading PDF text.

    Slices from the first line matching ``/abstract/i`` up to a line matching
    ``/introduction/i`` (or ``max_chars``). If no abstract marker is present,
    falls back to the first non-trivial paragraph.

    Args:
        text: Leading text of the paper (e.g. first one or two pages).
        max_chars: Hard cap on the returned abstract length.

    Returns:
        Cleaned abstract text, possibly empty.
    """
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if _ABSTRACT_RE.search(line):
            if _looks_like_toc(line):
                continue
            start = idx
            break

    if start is not None:
        # Drop the marker line itself; keep everything after it.
        body_lines = lines[start + 1 :]
        collected: list[str] = []
        for line in body_lines:
            if _INTRO_RE.search(line):
                break
            collected.append(line)
        candidate = _clean("\n".join(collected))
        # Guard against table-of-contents noise (e.g. "Abstract .... 6"): a real
        # abstract is a paragraph, so require some substance before trusting it.
        if candidate and not _looks_like_toc(candidate) and len(candidate) >= _MIN_ABSTRACT_CHARS:
            return candidate[:max_chars].strip()

    # Fallback: first paragraph with real content after the title block.
    paragraphs = re.split(r"\n\s*\n", text)
    for para in paragraphs:
        cleaned = _clean(para)
        if cleaned and not _looks_like_toc(para) and len(cleaned) >= _MIN_ABSTRACT_CHARS:
            return cleaned[:max_chars].strip()
    # Last resort: whatever leading text we have.
    cleaned_text = _clean(text)
    if _looks_like_toc(cleaned_text):
        return ""
    return cleaned_text[:max_chars].strip()


def summarize_paper(
    pdf: Path,
    *,
    figures_dir: Path | None = None,
    max_abstract_chars: int = 900,
) -> PaperSummary:
    """Build a :class:`PaperSummary` from a PDF and optional figures directory.

    Args:
        pdf: Path to the source PDF.
        figures_dir: Optional directory of exported figure images.
        max_abstract_chars: Maximum length of the extracted abstract.

    Returns:
        A populated :class:`PaperSummary`.

    Raises:
        BackendUnavailableError: If poppler is not installed.
        DemoCreateError: If the PDF is missing or metadata is unreadable.
    """
    pdf = Path(pdf)
    info = _pdf.pdf_info(pdf)
    title = info.get("title", "").strip()
    authors = info.get("author", "").strip()
    page_count = _pdf.pdf_page_count(pdf)

    leading = _pdf.extract_text(pdf, first=1, last=2)
    abstract = _extract_abstract(leading, max_chars=max_abstract_chars)
    # Long papers front-load a table of contents, so the real abstract may sit a
    # few pages in. If the first two pages yield nothing substantial, widen the
    # window once before giving up.
    if (not abstract or len(abstract) < _MIN_ABSTRACT_CHARS or _looks_like_toc(abstract)) and page_count > 2:
        deeper_last = min(page_count, _DEEP_ABSTRACT_PAGES)
        deeper = _pdf.extract_text(pdf, first=1, last=deeper_last)
        deeper_abstract = _extract_abstract(deeper, max_chars=max_abstract_chars)
        if deeper_abstract and not _looks_like_toc(deeper_abstract):
            if _looks_like_toc(abstract) or not abstract or len(deeper_abstract) >= len(abstract):
                abstract = deeper_abstract

    if _looks_like_toc(abstract):
        abstract = ""

    figures = collect_figures(figures_dir) if figures_dir is not None else []

    return PaperSummary(
        title=title,
        authors=authors,
        abstract=abstract,
        page_count=page_count,
        figures=figures,
        pdf_path=str(pdf.resolve()),
    )
