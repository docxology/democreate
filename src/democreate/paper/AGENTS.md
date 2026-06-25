# AGENTS — `democreate.paper`

Guidance for AI agents editing this subsystem.

## What this package is

PDF ingestion for DemoCreate, built **only** on the poppler CLI (`pdfinfo`,
`pdftotext`, `pdftoppm`) and assuming `ghostscript` is present. No pip PDF
library is imported anywhere. This is deliberate: poppler is ubiquitous on
scientific machines and avoids a heavyweight binary-wheel dependency.

## Invariants (do not break)

- `from __future__ import annotations` at the top of every module. Full type
  hints and Google-style docstrings on every public symbol. `pathlib.Path`
  everywhere — never bare strings for filesystem paths.
- **Never** import an optional/heavy dependency at module top level. Detect
  binaries with `shutil.which`. If a poppler binary is absent when a real
  function runs, raise `BackendUnavailableError("poppler", extra="pdf")`.
- Missing or non-PDF input files raise `DemoCreateError`. Chain underlying
  subprocess failures with `... from exc`. No bare `except`.
- Subprocess bodies are marked `# pragma: no cover` — they can only run with the
  real poppler binaries, so coverage tooling skips them while tests still
  exercise the happy path against the real test PDF.
- Keep functions deterministic and read-only with respect to the input PDF.

## Conventions

- `pdf_info` returns **lowercased** keys.
- `render_page` writes `<out>.png` (poppler's `-singlefile` appends `.png`).
- `render_pages` writes `out_dir/<prefix>_<NNN>.png` (3-digit, zero-padded) and
  returns a **sorted** list.
- `summarize_paper` derives title/authors/page_count from `pdf_info`, extracts
  the abstract heuristically from the first two pages of text, and lists figures
  via `collect_figures`.

## Testing

This subsystem owns `pdf.py`, `extract.py`, `structure.py`, `script.py` and the
matching `tests/paper/test_*.py` files (`pdf`, `extract`, `structure`, `script`).

Tests run real poppler against the real 170-page paper PDF at
`…/actinf_policy_entanglement_lean/output/pdf/…_combined.pdf` and its
`…/figures` directory. They skip gracefully when poppler or the fixture PDF is
unavailable, and use `monkeypatch` on `shutil.which` to prove the
missing-backend guard raises `BackendUnavailableError`. No mocks of real
computation.
