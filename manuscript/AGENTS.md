# Manuscript — DemoCreate v0.6.2

## Overview

Academic manuscript describing the `democreate` package: a declarative,
deterministic generator of narrated demos of **both software and research
papers**. Chapters are numbered Markdown files compiled by Pandoc (with
XeLaTeX) into a PDF. Settings and the chapter order live in `config.yaml`;
LaTeX packages in `preamble.md`; all citations in `references.bib`. Authoring
conventions are in `SYNTAX.md`. Figures live in `figures/` and are regenerated
by `figures/make_figures.py`.

## Chapters

| File | Section | Identifier |
|------|---------|-----------|
| `00_abstract.md` | Abstract (opens with `@fig:graphical_abstract`) | `#sec:abstract` |
| `01_introduction.md` | Introduction | `#sec:introduction` |
| `02_architecture.md` | Architecture | `#sec:architecture` |
| `03_synchronization.md` | Audio-Anchored Synchronization | `#sec:synchronization` |
| `04_implementation.md` | Implementation | `#sec:implementation` |
| `05_composition_and_configurability.md` | Composition and Configurability | `#sec:composition` |
| `06_research_paper_demos.md` | Research-Paper Demos | `#sec:paper` |
| `07_evaluation.md` | Evaluation: Measured Performance, Testability, Verification, and Determinism | `#sec:evaluation` |
| `08_reproducibility.md` | Reproducibility and Use | `#sec:reproducibility` |
| `09_scope_and_related_work.md` | Scope and Related Work | `#sec:related` |
| `10_provenance_and_distribution.md` | Provenance and Distribution | `#sec:provenance` |
| `99_references.md` | References | `#sec:references` |

Supporting assets: `preamble.md`, `config.yaml`, `references.bib`, `SYNTAX.md`,
`figures/`.

## Figures

The `make_figures.py` figures are 1600×900 (waveform 1600×240, latency 1600×600)
and are produced by calling the real `democreate` public APIs (and, for
`latency.png`, the real measured `data/benchmarks.json`). The cover figure
`graphical_abstract.png` is produced separately by `figures/graphical_abstract.py`.
Regenerate the `make_figures.py` set with:

```bash
cd ..  # project root
.venv/bin/python manuscript/figures/make_figures.py
```

| File | Label | Source API | Inserted in |
|------|-------|-----------|-------------|
| `figures/graphical_abstract.png` | `#fig:graphical_abstract` | `figures/graphical_abstract.py` (cover figure) | `00_abstract.md` |
| `figures/architecture.png` | `#fig:architecture` | `animation.diagram.democreate_architecture_image` | `02_architecture.md` |
| `figures/frame_code.png` | `#fig:frame_code` | `capture.screen.render_frame` (CODEBASE) | `04_implementation.md` |
| `figures/waveform.png` | `#fig:waveform` | `animation.waveform.draw_waveform` (noir red played) | `04_implementation.md` |
| `figures/themes.png` | `#fig:themes` | `render_frame` × `config.THEMES` (3+2 grid, five themes) | `05_composition_and_configurability.md` |
| `figures/frame_title.png` | `#fig:frame_title` | `render_frame` (SLIDE) | `05_composition_and_configurability.md` |
| `figures/frame_paper.png` | `#fig:frame_paper` | `render_frame` (SLIDE + `background_image`, paper theme) | `06_research_paper_demos.md` |
| `figures/typing_filmstrip.png` | `#fig:typing_filmstrip` | `render_frame` (CODEBASE) ×3 at `cursor_typed` 25/55/100% | `05_composition_and_configurability.md` |
| `figures/latency.png` | `#fig:latency` | pure-Pillow bar chart of `data/benchmarks.json` | `07_evaluation.md` |
| `figures/paper_flow.png` | `#fig:paper_flow` | `animation.diagram.render_architecture_diagram` (paper theme) | `06_research_paper_demos.md` |
| `figures/provenance.png` | `#fig:provenance` | pure-Pillow diagram driven by a real `config.MetadataConfig` | `10_provenance_and_distribution.md` |
| `figures/paper_fig.png` | — | real published paper figure (copied background source) | — |

## Invariants for agents

- **No manual section numbers.** Headers carry `{#sec:...}` identifiers only;
  numbering is applied by the toolchain.
- **Every `@cite` key must exist in `references.bib`.** `fail_on_missing: true`
  makes a dangling key a hard build failure. Add the BibTeX entry before the
  citation.
- **Cross-reference with `[@sec:...]` and figures with `[@fig:...]`**, never
  hard-coded numbers. Insert figures as
  `![Caption.](figures/x.png){#fig:x}` and reference them as `[@fig:x]`.
- **Ground every claim in `src/democreate`.** The chapters describe a real
  package — 56 source modules across eight subsystems (`capture/`, `narration/`,
  `animation/`, `codebase/`, `assembly/`, `export/`, `paper/`, `translation/`) plus `schema.py`,
  `config.py`, `media.py`, `pipeline.py`, `cli.py`. Authoritative v0.6.2 numbers:
  690 collected tests, ≥90% coverage gate, five themes (default
  **noir**), package demo 155.6 s at 3840×2160 (15 scenes/chapters), paper demo 188.0 s
  (12 scenes/chapters, 6-part section structure), both re-rendered in noir.
  If the code changes, update the prose and regenerate the figures.
- Inline code spans for all module/class/function/command names.

## Build

From the project root, render via the project's Pandoc/XeLaTeX pipeline using
`config.yaml` as the manifest. The bibliography is processed by Pandoc's
citeproc against `references.bib`; the reference list is emitted at the
`::: {#refs} :::` block in `99_references.md`. Regenerate `figures/` first if
the code has changed.
