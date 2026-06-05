"""Research-paper ingestion for DemoCreate.

Turns a PDF (and an optional directory of exported figures) into a structured,
render-ready summary using only the poppler command-line tools — no pip PDF
dependency. Two layers:

* :mod:`democreate.paper.pdf` — thin, guarded subprocess wrappers over
  ``pdfinfo`` / ``pdftotext`` / ``pdftoppm`` (metadata, text, page rasters).
* :mod:`democreate.paper.extract` — heuristic structuring into a
  :class:`PaperSummary` (title, authors, abstract, figures).
"""

from __future__ import annotations

from .extract import PaperSummary, collect_figures, summarize_paper
from .pdf import (
    extract_text,
    pdf_info,
    pdf_page_count,
    poppler_available,
    render_page,
    render_pages,
)
from .script import build_paper_demo, chunk_sentences
from .structure import (
    FigureCaption,
    PaperSection,
    extract_abstract,
    extract_figure_captions,
    extract_sections,
    summarize_structure,
)

__all__ = [
    # pdf.py
    "poppler_available",
    "pdf_info",
    "pdf_page_count",
    "extract_text",
    "render_page",
    "render_pages",
    # extract.py
    "PaperSummary",
    "collect_figures",
    "summarize_paper",
    # script.py
    "build_paper_demo",
    "chunk_sentences",
    # structure.py
    "FigureCaption",
    "PaperSection",
    "extract_figure_captions",
    "extract_sections",
    "extract_abstract",
    "summarize_structure",
]
