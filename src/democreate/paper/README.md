# `democreate.paper` — research-paper ingestion

Turn a research-paper **PDF** (plus an optional directory of exported figures)
into a structured, render-ready summary — the first step toward a narrated video
demo of a paper, the sibling of DemoCreate's software demos.

This subsystem uses the **poppler** command-line tools (`pdfinfo`, `pdftotext`,
`pdftoppm`) via `subprocess`. There is **no pip PDF dependency**: poppler ships
on most scientific workstations (`brew install poppler`, `apt install
poppler-utils`). `ghostscript` (`gs`) is also assumed available for downstream
rasterization workflows.

## Layers

| Module       | Responsibility                                                      |
|--------------|--------------------------------------------------------------------|
| `pdf.py`     | Guarded subprocess wrappers: metadata, text, page→PNG rasters.     |
| `extract.py` | Heuristic structuring into a `PaperSummary` (title/authors/abstract/figures). |

## Public API

```python
from democreate.paper import (
    poppler_available,          # bool — are pdfinfo/pdftoppm/pdftotext on PATH?
    pdf_info,                   # dict[str, str] — lowercased pdfinfo metadata
    pdf_page_count,             # int
    extract_text,               # str — pdftotext [-f first] [-l last]
    render_page,                # Path — single page → PNG
    render_pages,               # list[Path] — many pages → out_dir/<prefix>_NNN.png
    PaperSummary,               # dataclass with .to_dict()
    collect_figures,            # list[Path] — sorted *.png/*.jpg (non-recursive)
    summarize_paper,            # PaperSummary
)
```

## Example

```python
from pathlib import Path
from democreate.paper import summarize_paper

summary = summarize_paper(
    Path("paper.pdf"),
    figures_dir=Path("figures"),
)
print(summary.title, summary.page_count, len(summary.figures))
print(summary.abstract[:200])
```

## Backend guarantee

Every binary-backed function checks `shutil.which` first and raises
`BackendUnavailableError("poppler", extra="pdf")` if a poppler tool is missing,
so callers get an actionable message instead of a raw `FileNotFoundError`.
Missing or non-PDF input files raise `DemoCreateError`.
