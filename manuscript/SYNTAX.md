# Manuscript Syntax Conventions

This manuscript follows the docxology `template_code_project` Markdown
conventions. Authors and tools editing these chapters must preserve them.

## Section headers

- Each chapter file opens with a single level-one header carrying an explicit
  Pandoc identifier, e.g. `# Architecture {#sec:architecture}`.
- Sub-sections use `##` and `###`. **Never write a manual section number**
  (no `1.`, `2.1`, `A.`); numbering is applied by the Pandoc/LaTeX toolchain.
- Identifiers use the `sec:` prefix and are lowercase, hyphen-free single
  tokens where possible (`#sec:related`, `#sec:synchronization`).

## Cross-references

- Refer to sections with Pandoc cross-ref syntax: `[@sec:architecture]`,
  `[@sec:synchronization]`. Do not hard-code section numbers in prose.
- Refer to figures with `[@fig:architecture]`, `[@fig:frame_code]`, etc. Do not
  hard-code figure numbers.

## Figures

- Insert a figure with a captioned image carrying an explicit identifier:
  `![Caption text.](figures/architecture.png){#fig:architecture}`. Identifiers
  use the `fig:` prefix.
- Reference the figure in prose with `[@fig:architecture]`; numbering is applied
  by the toolchain.
- All figure PNGs live in `figures/` and are produced by the real `democreate`
  APIs via `figures/make_figures.py`. Regenerate them (from the project root,
  `.venv/bin/python manuscript/figures/make_figures.py`) when the code changes;
  never hand-edit a figure PNG. The `@fig:provenance` figure
  (`figures/provenance.png`, inserted in `10_provenance_and_distribution.md`) is
  driven by a real `config.MetadataConfig`, so its labels track the package's
  own field names. The cover figure `@fig:graphical_abstract`
  (`figures/graphical_abstract.png`, the first figure in `00_abstract.md`) is
  generated separately by `figures/graphical_abstract.py`.

## Citations

- Cite with Pandoc author-in-text or bracketed forms: `[@codevideo2024]`,
  `[@radford2023whisper; @whisperx2023]`.
- **Every `@key` must resolve to an entry in `references.bib`.** The build gate
  (`fail_on_missing: true` in `config.yaml`) treats a dangling key as a hard
  failure. When adding a citation, add the BibTeX entry first.

## Code and inline literals

- Inline module, class, function, and command names are wrapped in backticks:
  `` `Demo` ``, `` `sync_demo` ``, `` `democreate build` ``.
- Fenced code blocks use a language tag (` ```bash `, ` ```latex `) so the
  `listings` package can format them.

## LaTeX and packages

- `preamble.md` declares the LaTeX packages available to the rendered PDF:
  `listings` (code blocks) and `siunitx` (units). Use `\SI{}{}` / `\si{}` for
  physical quantities where a chapter needs them.
- Keep raw LaTeX out of chapter bodies; confine it to `preamble.md`.

## Prose

- Markdown-first. Use tables, fenced blocks, and emphasis; avoid HTML except
  where Markdown cannot express the construct.
- Claims about the package must be grounded in the actual `src/democreate`
  code. When the implementation changes, update the affected chapter.
