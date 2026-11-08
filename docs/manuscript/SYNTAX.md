# Standalone Pandoc Authoring and Evidence Conventions

This manuscript uses local Pandoc conventions. `config.yaml`, `preamble.md`
and this guide define its standalone build/authoring contract; no sibling
template checkout is required.

## Responsibility-Specific Headings and Stable Identifiers

- Each chapter file opens with a single level-one header carrying an explicit
  Pandoc identifier, e.g. `# Demo Values, Backend Boundaries, and Workspace Custody {#sec:architecture}`.
- Sub-sections use `##` and `###`. **Never write a manual section number**
  (no `1.`, `2.1`, `A.`); numbering is applied by the Pandoc/LaTeX toolchain.
- Identifiers use the `sec:` prefix and are lowercase, hyphen-free single
  tokens where possible (`#sec:related`, `#sec:synchronization`).
- Name the responsibility, mechanism or limitation in a heading rather than
  using a generic label such as "Overview" or "Details". Keep conventional
  `Abstract` and `References` headings. Preserve existing explicit `sec:`/`fig:`
  identifiers and update orientation tables when a visible title changes.

## Numbering-Independent Section and Figure References

- Refer to sections with Pandoc cross-ref syntax: `[@sec:architecture]`,
  `[@sec:synchronization]`. Do not hard-code section numbers in prose.
- Refer to figures with `[@fig:architecture]`, `[@fig:frame_code]`, etc. Do not
  hard-code figure numbers.

## Figure Captions, Source Classes, and Regeneration

- Insert a figure with a captioned image carrying an explicit identifier:
  `![Caption text.](figures/architecture.png){#fig:architecture}`. Identifiers
  use the `fig:` prefix.
- Reference the figure in prose with `[@fig:architecture]`; numbering is applied
  by the toolchain.
- Figure outputs live in `figures/`; `make_figures.py` composes synthetic API
  illustrations, conceptual schematics, recorded timing and decoded-video
  samples. `graphical_abstract.py` generates the cover separately. Shared layout
  code does not make a diagram an empirical result. Target dimensions and input
  identities are documented in `AGENTS.md` and `figures/README.md`.
- Regenerate from the repository root with
  `.venv/bin/python docs/manuscript/figures/make_figures.py` and
  `.venv/bin/python docs/manuscript/figures/graphical_abstract.py`; never hand-edit
  PNGs. Preserve retained background inputs, raw decoded frames and their records.
- Captions must distinguish conceptual diagrams, synthetic render states and
  observed samples. Name verbatim source symbols (`Action.to_dict` and
  `Timeline.entry_at_ms`) rather than implying schematic code was executed.
  Requested video seeks are not observed onsets; a synthetic tone is not speech.
  A newly generated composition does not renew its underlying evidence.

## Existing Citation Keys and Verified New Sources

- Cite with Pandoc author-in-text or bracketed forms: `[@codevideo2024]`,
  `[@radford2023whisper; @whisperx2023]`.
- **Every `@key` must resolve to an entry in `references.bib`.** The build gate
  (`fail_on_missing: true` in `config.yaml`) treats a dangling key as a hard
  failure. When adding a citation, add the BibTeX entry first.

## Inline API Names and Language-Tagged Code

- Inline module, class, function, and command names are wrapped in backticks:
  `` `Demo` ``, `` `sync_demo` ``, `` `democreate build` ``.
- Fenced code blocks use a language tag (` ```bash `, ` ```latex `) so the
  `listings` package can format them.

## Preamble-Owned LaTeX Packages

- `preamble.md` declares the LaTeX packages available to the rendered PDF:
  `listings` (code blocks) and `siunitx` (units). Use `\SI{}{}` / `\si{}` for
  physical quantities where a chapter needs them.
- Keep raw LaTeX out of chapter bodies; confine it to `preamble.md`.

## Authoritative Topic Homes and Bounded Claims

- Markdown-first. Use tables, fenced blocks, and emphasis; avoid HTML except
  where Markdown cannot express the construct.
- Claims about the package must be grounded in the actual `src/democreate`
  code. When the implementation changes, update the affected chapter.
- Keep detailed mechanisms, recipes and criteria in their authoritative chapter
  (see `README.md`); link from other chapters instead of repeating the same
  command blocks or limitation boilerplate.
- Distinguish implemented behavior, source-bound observations, historical
  records and prospective plans. Coverage gates are not passing receipts;
  measured durations are not acoustic word onsets; unsigned content digests
  are not authentication. Fixed input/assets/configuration/environment are
  prerequisites for a deterministic-core claim.
