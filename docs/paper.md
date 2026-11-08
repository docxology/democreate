# Paper workflow: PDF extraction, supplied figures and narrated scenes

With poppler and a usable speech/encoding environment, DemoCreate can compile a
PDF's extracted text and supplied images into a narrated walkthrough. Extraction
is heuristic, not a validated semantic reading of arbitrary papers. `--no-render`
emits the declarative artifact without claiming voiced video.

The subsystem is `src/democreate/paper/`:

| Module | Role |
|--------|------|
| `pdf.py` | Poppler CLI wrapper (`pdfinfo` / `pdftotext` / `pdftoppm`) — **zero pip deps**. Reads metadata, extracts text, rasterizes PDF pages to PNGs. |
| `extract.py` | `summarize_paper()` → `PaperSummary` (title, authors, abstract, page count, figures). |
| `structure.py` | Heuristic abstract, figure-caption and section detection with TOC filtering; inspect results against the source PDF. |
| `script.py` | `build_paper_demo()` — turns a `PaperSummary` (+ pages, figures, captions, sections, codebase) into a declarative `Demo`. |

## The one-liner

```bash
democreate paper paper.pdf --repo /path/to/code --figures /path/to/figs --theme paper
```

This reads the PDF, walks the codebase, renders the requested PDF pages and an
architecture diagram, assembles a `Demo`, and renders + verifies the video.

## How a paper becomes a demo

`build_paper_demo()` assembles scenes deterministically (template narration, no
LLM, for fixed extracted text, figures, options and runtime):

1. **Title card** — `"<title>. A <N>-page paper by <authors>."`
2. **Title page** — the first rendered PDF page as a full-frame background (if
   `--pages` includes it).
3. **Abstract** — detected prose, paced into narration chunks. TOC filtering is a
   heuristic and may select the wrong block or omit content.
4. **Structure** — a "how the paper is organised" slide listing the paper's
   **sections** (`extract_sections()`), present only when sections are found.
5. **Figures** — up to `max_figures` (6) images from `--figures`, each a
   full-frame background slide. When a **real figure caption** was extracted for
   that figure number, it is narrated verbatim (`"Figure N. <caption>"`);
   otherwise a generic line is used.
6. **Additional pages** — further rendered PDF pages (`pages[1:4]`) as
   backgrounds.
7. **Codebase architecture** — a rendered architecture diagram
   (`animation/diagram.py::render_architecture_diagram`) of the codebase walked
   from `--repo`, grouped into columns by top-level directory; or a text slide
   stating the module count if no diagram was produced.
8. **Closing card** — template-authored outro, not independent reproducibility proof.

Figures and PDF pages are carried as full-frame `background_image` scene context.
Base images use proportional contain fitting. Camera zoom and overlays may still
hide content; inspect encoded frames. `--theme paper` selects a warm light
palette and is the `paper` command's default (`render` defaults to `noir`).
Neither setting establishes semantic correctness, faithful mathematical notation
or empirical paper results.

## How the PDF is read (poppler, zero pip)

`paper/pdf.py` shells out to the poppler utilities that ship on most scientific
workstations — **no pip PDF dependency**:

- `pdfinfo` → metadata (title, author, page count) via `pdf_info()` /
  `pdf_page_count()`.
- `pdftotext` → leading text for the abstract via `extract_text(first, last)`.
- `pdftoppm` → rasterize pages to PNGs via `render_page()` / `render_pages()`
  (default 150 DPI; the CLI uses 140).

Every function checks its binary is on `PATH` first and raises
`BackendUnavailableError(backend="poppler")` if it is missing.
`poppler_available()` checks all required executable paths, not PDF validity or
semantic extraction accuracy.

## Deeper structure: real abstract, captions, sections

`structure.py` adds pure-text extraction (no poppler in the pure functions — they
operate on already-extracted text and are fully testable) that fixes the naive
summarizer's two weaknesses: it would grab the title block instead of the abstract,
and narrate figures generically. The **table of contents is the adversary
throughout** — every extractor explicitly rejects TOC artifacts (dotted leaders
`....`, trailing page numbers).

- **Abstract candidate** (`extract_abstract()`). Searches standalone markers,
  filters likely TOC text and bounds returned prose. Heuristic fallback can
  select another paragraph; “substantial” text is not semantic validation.
- **Real figure captions** (`extract_figure_captions()`). Matches
  `"Figure N: ..."` / `"Figure N. ..."` / `"Fig. N ..."`. The caption body is
  captured **across line breaks** (a `DOTALL` tail up to a blank line, the next
  figure/table marker, or end of text) so a math caption that **wraps onto a
  second line** is no longer truncated mid-formula; `_bound_caption()` then trims
  it to its first sentence. Captions are deduplicated by figure number and
  cross-reference/TOC fragments are skipped. These are what get narrated on the
  figure scenes.
- **Sections** (`extract_sections()`). Recognizes numbered headings
  (`"1 Introduction"`, `"2.1 Setup"`), `Part N — Title` headings, and well-known
  named sections (Introduction, Methods, Results, …), deduplicated by title — the
  source of the **structure** scene.

**Glyph folding for on-screen text (NFKC).** Extracted abstract, caption, and
section text is run through `_fold_text()` before it becomes narration/overlay
text. Scientific PDFs use astral-plane *Mathematical Alphanumeric Symbols* (e.g.
U+1D706 mathematical-italic lambda) and math operators (U+22C6 star) that a UI
sans font cannot draw — they show as tofu boxes on screen. `_fold_text()` applies
Unicode **NFKC** normalization (folding the math-alphanumerics down to their plain
Latin/Greek BMP forms) and then a small `_MATH_OPERATOR_FOLD` table for the
operators NFKC leaves alone (`⋆`/`∗`→`*`, `−`→`-`, `…`→`...`).
This is lossy display normalization, not faithful mathematical transcription;
the bundled font has limited glyph coverage. Check against original notation.

`summarize_structure(pdf)` is the single guarded entry point; the `paper` command
wraps it in `try/except` so structure extraction is best-effort and a render still
succeeds if it yields nothing. Older Active Inference-paper observations are
historical and unbound; controlled synthetic PDF fixtures prove mechanics, not
accuracy on that unshipped research source.

## Options and reusable paper assets

The [CLI paper reference](cli.md#paper) owns the option/default table. Use
`--no-render` to emit `output/demos/paper.json` without claiming voiced media;
poppler is still required. The command writes generated pages and architecture
assets into the output workspace. Supplied figure images must remain within
the selected figure directory (or the PDF directory when no figure root is set).

After a complete build/render, `output/demos/demo.json` is the resolved,
workspace-relative bundle. Reuse it with an explicit asset root:

```bash
democreate render output/demos/demo.json --asset-root output \
  -o output/paper-rerender --theme paper --tts system
```

The earlier `paper.json` is an authored intermediate, not that resolved bundle;
its generated workspace-relative references are not automatically relative to
its `demos/` parent. Inspect or normalize those references before using it as a
standalone CLI input. Missing or outside-root assets fail, not silently disappear.

## Historical paper example, not a current result

Earlier documentation described a 170-page *Policy Entanglement in Active
Inference* paper, 47 figures and a 145-module codebase, with an approximately
188-second template-generated video. Its source-video digest and extraction
date are unrecorded. Those observations do not prove current output or semantic
accuracy; the external PDF/code/figures are not shipped. See
[media identities](videos.md) for the separate curated paper recipe and historical
stills. Controlled synthetic PDF fixtures establish mechanics, not empirical
results on an unshipped research source.

## See also

- [cli.md](cli.md) — the full `paper` command reference.
- [config.md](config.md) — the `paper` theme and `RenderConfig`.
- [video.md](video.md) — the animated render and no-crop figure/page layout.
- [backends.md](backends.md) — poppler as a zero-pip system backend.
