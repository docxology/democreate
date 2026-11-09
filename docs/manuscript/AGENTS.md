# Manuscript — DemoCreate candidate 0.8.0

## Manuscript sources and authoring entrypoints

Academic manuscript describing the `democreate` package: a declarative generator
of software and research-paper demos. Core determinism requires fixed inputs,
assets, configuration and environment; default audio is silent and visuals are
synthetic. Chapters compile through Pandoc and a compatible LaTeX engine.
`config.yaml` owns chapter order/build settings; `preamble.md` owns LaTeX
packages; `references.bib` owns citations; `SYNTAX.md` owns authoring conventions.
`README.md` maps topic responsibilities and source/evidence boundaries.

## Chapter headings and stable section identifiers

| File | Section | Identifier |
|------|---------|-----------|
| `00_abstract.md` | Abstract (opens with `@fig:graphical_abstract`) | `#sec:abstract` |
| `01_introduction.md` | Editable Demo Descriptions and Evidence Boundaries | `#sec:introduction` |
| `02_architecture.md` | Demo Values, Backend Boundaries, and Workspace Custody | `#sec:architecture` |
| `03_synchronization.md` | Measured Clip Durations and Estimated Word Triggers | `#sec:synchronization` |
| `04_implementation.md` | Subsystem Responsibilities and Output Contracts | `#sec:implementation` |
| `05_composition_and_configurability.md` | Configuring Layout, Motion, Audio, and Media Exports | `#sec:composition` |
| `06_research_paper_demos.md` | From PDF Text and Supplied Figures to Demo Scenes | `#sec:paper` |
| `07_evaluation.md` | Runtime Observations, Annotation Scoring, and the Unmet Acoustic Study | `#sec:evaluation` |
| `08_reproducibility.md` | Reproducing Core Builds and Optional Voiced Renders | `#sec:reproducibility` |
| `09_scope_and_related_work.md` | Construction Models and Comparison Limits | `#sec:related` |
| `10_provenance_and_distribution.md` | Unsigned Attribution, Digest Scope, and Distribution | `#sec:provenance` |
| `99_references.md` | References | `#sec:references` |

Supporting assets: `preamble.md`, `config.yaml`, `references.bib`, `SYNTAX.md`,
`figures/`.

## Figure sources, target dimensions, and evidence classes

Generator constants own target dimensions: `make_figures.py` defines
`CANVAS = (1600, 900)` for its main set (including timing and montage) and
`WAVE_CANVAS = (1600, 300)`; `graphical_abstract.py` defines
`W, H = 2400, 1350`. These describe generation targets, not an independent
inspection of committed PNGs. `figure_layout.py` supplies shared layout helpers.
Conceptual schematics, synthetic API illustrations, retained external inputs,
source-bound timing and decoded-video samples have different evidence roles.
See `figures/README.md` for those boundaries.

From the repository root:

```bash
.venv/bin/python docs/manuscript/figures/make_figures.py
.venv/bin/python docs/manuscript/figures/graphical_abstract.py
```

| File | Label | Source or construction | Inserted in |
|------|-------|------------------------|-------------|
| `figures/graphical_abstract.png` | `#fig:graphical_abstract` | `graphical_abstract.py`: conceptual capability schematic | `00_abstract.md` |
| `figures/architecture.png` | `#fig:architecture` | `make_architecture`: authored/scheduled/output schematic | `02_architecture.md` |
| `figures/frame_code.png` | `#fig:frame_code` | `render_frame`; current `schema.Action.to_dict` source | `04_implementation.md` |
| `figures/waveform.png` | `#fig:waveform` | `compute_envelope` / `draw_waveform` on a synthesized AM tone | `04_implementation.md` |
| `figures/themes.png` | `#fig:themes` | `render_frame` × five `THEMES` plus comparison-key tile | `05_composition_and_configurability.md` |
| `figures/frame_title.png` | `#fig:frame_title` | `render_frame` on a `SLIDE` state | `05_composition_and_configurability.md` |
| `figures/frame_paper.png` | `#fig:frame_paper` | `render_frame` on a `SLIDE` with committed `paper_fig.png` | `06_research_paper_demos.md` |
| `figures/typing_filmstrip.png` | `#fig:typing_filmstrip` | current `Timeline.entry_at_ms` source + three synthetic character-count previews | `05_composition_and_configurability.md` |
| `figures/latency.png` | `#fig:latency` | separate-unit cards from `data/benchmarks-0.8.0.json` | `07_evaluation.md` |
| `figures/paper_flow.png` | `#fig:paper_flow` | `make_paper_flow`: extraction/authored-Demo/output schematic | `06_research_paper_demos.md` |
| `figures/provenance.png` | `#fig:provenance` | diagram of distinct unsigned carriers with `MetadataConfig` examples | `10_provenance_and_distribution.md` |
| `figures/video_stills.png` | `#fig:video_stills` | six digest-checked decoded frames revalidated by `data/visual-refresh-2026-11-08.json` | `07_evaluation.md` |
| `figures/paper_fig.png` | — | retained external background input; extraction date/publication status unestablished here | — |

## Invariants for agents

- **No manual section numbers.** Headers carry `{#sec:...}` identifiers only;
  numbering is applied by the toolchain.
- **Every `@cite` key must exist in `references.bib`.** `fail_on_missing: true`
  makes a dangling key a hard build failure. Add the BibTeX entry before the
  citation.
- **Cross-reference with `[@sec:...]` and figures with `[@fig:...]`**, never
  hard-coded numbers. Insert figures as
  `![Caption.](figures/x.png){#fig:x}` and reference them as `[@fig:x]`.
- **Ground claims in source and dated receipts.** Candidate 0.8.0 requires
  Python ≥3.11.5, Pillow ≥13 and schema 1.1. Keep suite counts out of prose/pixels;
  the ≥90% core coverage threshold is a gate, not a current result. Distinguish
  newly generated conceptual/synthetic illustrations from retained raw inputs
  and source-bound observations; never relabel old evidence as a fresh run.
  Clip windows are not acoustic onsets. Kokoro is implemented;
  Whisper/Chatterbox/Manim are unwired. Poster hashes are unsigned associations.
- Inline code spans for all module/class/function/command names.

## Repository-root manuscript generation and gates

From the project root, render via Pandoc and a compatible LaTeX engine using
`config.yaml` as the manifest. The bibliography is processed by Pandoc's
citeproc against `references.bib`; the reference list is emitted at the
`::: {#refs} :::` block in `99_references.md`. Regenerate `figures/` first if
the code has changed.
