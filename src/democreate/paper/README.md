# `democreate.paper` — research-paper ingestion

Turn a research-paper **PDF** (plus an optional directory of exported figures)
into a structured, render-ready summary — the first step toward a narrated video
demo of a paper, the sibling of DemoCreate's software demos.

This subsystem uses the **poppler** command-line tools (`pdfinfo`, `pdftotext`,
`pdftoppm`) via `subprocess`. There is **no pip PDF dependency**: poppler ships
on most scientific workstations (`brew install poppler`, `apt install
poppler-utils`). Voiced video additionally needs usable speech and ffmpeg/ffprobe.

## Layers

| Module       | Responsibility                                                      |
|--------------|--------------------------------------------------------------------|
| `pdf.py`     | Guarded subprocess wrappers: metadata, text, page→PNG rasters.     |
| `extract.py` | Heuristic structuring into a `PaperSummary` (title/authors/abstract/figures). |
| `structure.py` | Heuristic abstract/TOC filtering, figure-caption and section candidates; not semantic validation. |
| `script.py`  | Build the narrated paper `Demo` from the summary + structure (`build_paper_demo`). |

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
    # structure.py — deeper extraction
    summarize_structure,        # dict — abstract + figure_captions + sections
    extract_abstract,           # str — heuristic abstract candidate with TOC filtering
    extract_figure_captions,    # list[FigureCaption] — "Figure N: …"
    extract_sections,           # list[PaperSection]
    FigureCaption, PaperSection,
    # script.py — narrated demo
    build_paper_demo,           # Demo — from summary + structure + figures/code
    chunk_sentences,            # list[str] — sentence chunking for narration
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
`BackendUnavailableError("poppler")` if a poppler tool is missing (poppler is an
OS binary — install it with `brew install poppler` / `apt-get install
poppler-utils`), so callers get an actionable message instead of a raw
`FileNotFoundError`.
Missing or non-PDF input files raise `DemoCreateError`.

Filesystem arguments sent to poppler are absolute, so relative filenames such
as `-v` and `-` are treated as files rather than options or stdin. The intentional
`pdftotext` stdout argument remains `-`. Raster functions return paths with the
caller's relative/absolute spelling; only subprocess arguments are normalized.

Extraction and display normalization are heuristic/lossy; review against the
source paper. Pure text helpers do not need poppler, but PDF reads do: there is
no default core PDF decoder. [Paper workflow](../../../docs/paper.md) owns asset
roots and reusable output instructions; [media evidence](../../../docs/videos.md)
separates controlled fixtures, historical observations and unshipped paper inputs.
