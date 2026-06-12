# Research-paper demos

DemoCreate generates narrated HD video demos of **research papers**, not just
software. Point it at a PDF (optionally with the paper's codebase and a directory
of exported figures) and it produces a narrated walkthrough: a title card, the
abstract paced into chunks, the paper's figures and selected PDF pages as
full-frame backgrounds, an architecture diagram of the implementation, and a
closing card — all rendered to a real HD MP4 and content-verified.

The subsystem is `src/democreate/paper/`:

| Module | Role |
|--------|------|
| `pdf.py` | Poppler CLI wrapper (`pdfinfo` / `pdftotext` / `pdftoppm`) — **zero pip deps**. Reads metadata, extracts text, rasterizes PDF pages to PNGs. |
| `extract.py` | `summarize_paper()` → `PaperSummary` (title, authors, abstract, page count, figures). |
| `structure.py` | Deeper, pure-text extraction: the **real abstract** (skipping the TOC), **real figure captions** (`"Figure N: ..."`), and the **section list** — via `summarize_structure()`. |
| `script.py` | `build_paper_demo()` — turns a `PaperSummary` (+ pages, figures, captions, sections, codebase) into a declarative `Demo`. |

## The one-liner

```bash
democreate paper paper.pdf --repo /path/to/code --figures /path/to/figs --theme paper
```

This reads the PDF, walks the codebase, renders the requested PDF pages and an
architecture diagram, assembles a `Demo`, and renders + verifies the video.

## How a paper becomes a demo

`build_paper_demo()` assembles scenes deterministically (template narration, no
LLM — the same paper always yields the same demo):

1. **Title card** — `"<title>. A <N>-page paper by <authors>."`
2. **Title page** — the first rendered PDF page as a full-frame background (if
   `--pages` includes it).
3. **Abstract** — the **real abstract** (TOC skipped — see below),
   `chunk_sentences()`-paced into up to 6 narration chunks on one slide scene.
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
8. **Closing card** — a "reproducible by construction" outro.

Figures and PDF pages are carried as full-frame `background_image` scene context.
By default they are fit **whole** into the frame (contain, never cropped) so no
part of a figure is lost; the **Ken Burns** slow-zoom that would crop their edges
is **off by default** and only applies to them when explicitly enabled (see
[video.md](video.md#ken-burns-off-by-default)). The `paper` theme
([config.md](config.md)) gives slides a warm paper-white, serif-ish, amber-accent
academic look — but as of `v0.6.2` the **noir** theme is the package-wide default,
and the produced paper demo is rendered in noir ([videos.md](videos.md)).

## How the PDF is read (poppler, zero pip)

`paper/pdf.py` shells out to the poppler utilities that ship on most scientific
workstations — **no pip PDF dependency**:

- `pdfinfo` → metadata (title, author, page count) via `pdf_info()` /
  `pdf_page_count()`.
- `pdftotext` → leading text for the abstract via `extract_text(first, last)`.
- `pdftoppm` → rasterize pages to PNGs via `render_page()` / `render_pages()`
  (default 150 DPI; the CLI uses 140).

Every function checks its binary is on `PATH` first and raises
`BackendUnavailableError(backend="poppler", extra="pdf")` with an actionable
message if it is missing. `poppler_available()` reports readiness.

## Deeper structure: real abstract, captions, sections

`structure.py` adds pure-text extraction (no poppler in the pure functions — they
operate on already-extracted text and are fully testable) that fixes the naive
summarizer's two weaknesses: it would grab the title block instead of the abstract,
and narrate figures generically. The **table of contents is the adversary
throughout** — every extractor explicitly rejects TOC artifacts (dotted leaders
`....`, trailing page numbers).

- **Real abstract** (`extract_abstract()`). Iterates over *every* standalone
  `Abstract` marker (a long paper has at least two: one in the TOC, one real) and
  returns the first following block that is substantial (≥ 200 chars) and not
  itself a TOC, bounded to 1200 chars. Falls back to the first substantial prose
  paragraph after the first third of the text (and never the repeated title).
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
operators NFKC leaves alone (`⋆`/`∗`→`*`, `−`→`-`, `…`→`...`). The result is text
that renders cleanly in the figure-caption and abstract scenes at any resolution.

`summarize_structure(pdf)` is the single guarded entry point; the `paper` command
wraps it in `try/except` so structure extraction is best-effort and a render still
succeeds if it yields nothing. On the *Active Inference* paper this extracts a
correct ~1200-char abstract, the real figure captions, and 6 sections.

## Options

| Option | Default | Meaning |
|--------|---------|---------|
| `PDF` (arg) | required | Path to the paper PDF. |
| `--repo`, `-r` | `None` | Associated codebase directory (architecture diagram). |
| `--figures` | `None` | Directory of exported figure images (`.png`/`.jpg`). |
| `--output`, `-o` | `output` | Output workspace. |
| `--pages` | `"1"` | Comma-separated 1-based PDF pages to show. |
| `--theme` | `paper` | `paper` / `noir` / `dark` / `light` / `midnight`. |
| `--voice`, `-v` | `""` (OS default) | Optional system voice name. |
| `--tts` | `system` | TTS backend. |
| `--aspect` | `""` (demo's size) | Aspect preset: `16:9` / `9:16` / `1:1` / `4:3` / `4:5`. |
| `--resolution` | `""` (demo's size) | 16:9 tier: `720p` / `1080p` / `1440p` / `2160p` / `4k`. |
| `--author` | `""` (the PDF's author) | Override the creator name (defaults to the PDF metadata's author). |
| `--watermark` | `""` | Persistent watermark text (footer far-right). |
| `--max-figures` | `6` | How many figures to feature. |
| `--config` | `None` | `RenderConfig` YAML (overrides `--theme`). |
| `--render / --no-render` | `--render` | Render the video, or only emit `paper.json`. |

## Worked example (verified end-to-end)

The `Policy Entanglement in Active Inference` paper — a 170-page PDF with 47
figures and a 145-module codebase — was rendered and content-verified:

```bash
democreate paper policy-entanglement.pdf \
  --repo ./active-inference-repo \
  --figures ./figures \
  --pages 1,2 \
  --theme paper
```

Result: a **1920×1080 / ~188 s H.264 + AAC** video, `verify_video` ok (rendered in
the `v0.6.2` noir look — see [videos.md](videos.md)). The figures, the code, and
the overview were all generated from the same sources — reproducible by
construction.

## See also

- [cli.md](cli.md) — the full `paper` command reference.
- [config.md](config.md) — the `paper` theme and `RenderConfig`.
- [video.md](video.md) — the animated render and no-crop figure/page layout.
- [backends.md](backends.md) — poppler as a zero-pip system backend.
