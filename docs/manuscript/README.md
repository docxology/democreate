# DemoCreate manuscript — candidate 0.8.0

Chapters describe a declarative Demo pipeline for software and research-paper
presentations. `config.yaml` is the chapter/build manifest; `SYNTAX.md` describes
Pandoc conventions. Publication is pending. The existing concept DOI currently
resolves to archived **0.6.2**, not a new 0.8.0 archive.

## Chapter responsibilities and authoritative detail

The PDF table of contents is generated from chapter headings; explicit `sec:`
identifiers remain stable when titles improve. Each topic has one detailed home:

| Chapter | Heading and responsibility |
|---|---|
| [Introduction](01_introduction.md) | Editable Demo Descriptions and Evidence Boundaries |
| [Architecture](02_architecture.md) | Demo Values, Backend Boundaries, and Workspace Custody |
| [Synchronization](03_synchronization.md) | Measured Clip Durations and Estimated Word Triggers |
| [Implementation](04_implementation.md) | Subsystem Responsibilities and Output Contracts |
| [Composition](05_composition_and_configurability.md) | Configuring Layout, Motion, Audio, and Media Exports |
| [Paper inputs](06_research_paper_demos.md) | From PDF Text and Supplied Figures to Demo Scenes |
| [Evaluation](07_evaluation.md) | Evaluation: Source-Bound Observations and Blocking Acoustic Study |
| [Reproduction recipes](08_reproducibility.md) | Reproducing Core Builds and Optional Voiced Renders |
| [Related work](09_scope_and_related_work.md) | Construction Models, Related Systems, and Comparison Limits |
| [Attribution](10_provenance_and_distribution.md) | Unsigned Attribution, Digest Scope, and Distribution |

The [Abstract](00_abstract.md) opens the paper; [References](99_references.md)
contains the bibliography insertion point. Installation/render commands live in
the reproduction chapter, timing semantics in synchronization, evidence/study
criteria in evaluation, and digest field coverage in attribution.

## Evidence boundaries

- Clip durations are measured; default word timestamps interpolate known text
  by character length. No acoustic recognition or measured onset accuracy is
  claimed. Whisper, Chatterbox and Manim remain unwired slots; Kokoro is implemented.
- The planned, blocking study requires ≥30 independently annotated voiced demos
  (≥10/mode) and both error medians ≤120 ms; see the evaluation chapter.
- The HTML output is a timed image preview without narration playback, not an
  embedded voiced player or animated MP4.
- The real-filesystem suite has a ≥90% core coverage gate. Counts and current
  coverage results belong in run receipts, not prose or pixels.
- `data/benchmarks.json` is a historical aggregate record without original run
  identity. Build timing includes TTS/sync/frames/exports; render timing covers
  the whole `render_video` call with verification disabled. Mean dB is not LUFS.
- PNG digest payloads are unsigned consistency checks, not signatures,
  authentication, or image/video identity.
- The cover, architecture, paper-flow and attribution diagrams are conceptual
  illustrations, not empirical results. Editor/slide/theme/typing images are
  generated synthetic states; the waveform uses a synthetic tone, not speech.
- The package-only 3×2 montage uses six digest-checked decoded stills identified
  in `data/release-0.8.0.json`. The raw stills and record retain source identity;
  montage labels are requested seeks at cue midpoints, not annotated onsets.
- `figures/paper_fig.png` is a retained external background input with an
  unrecorded extraction date. A newly composed paper-theme slide does not turn
  that input into a new extraction or establish a paper-video result.

| Claim type | Authoritative source | What it does not establish |
|---|---|---|
| Package behavior and dependency floors | [`src/democreate/`](../../src/democreate/) and [`pyproject.toml`](../../pyproject.toml) | A passing run or optional runtime availability |
| Old aggregate timing | [`data/benchmarks.json`](../../data/benchmarks.json) | Original run identity or current performance |
| Source-bound silent-starter timing | [`data/benchmarks-0.8.0.json`](../../data/benchmarks-0.8.0.json) | Neural-TTS performance or performance of a later edited tree |
| Identified MP4, sidecars and decoded samples | [`data/release-0.8.0.json`](../../data/release-0.8.0.json) | Listening quality, acoustic accuracy or certification of later edits |
| Prospective acoustic study | [`experiment_plan.yaml`](../../experiment_plan.yaml) | A supplied corpus or measured result |
| Engineering/release requirements | [`domain_profile.yaml`](../../domain_profile.yaml) | Passing receipts or permission to waive the blocking study |

## Regeneration from the repository root

```bash
.venv/bin/python docs/manuscript/figures/make_figures.py
.venv/bin/python docs/manuscript/figures/graphical_abstract.py
.venv/bin/python scripts/build_manuscript.py --check
.venv/bin/python scripts/build_manuscript.py
```

The figure generator uses committed repository inputs, including local
`figures/paper_fig.png`; it neither searches nor writes sibling repositories.
It mirrors figures into root `output/figures/`. Timing consumes the retained
source-bound `data/benchmarks-0.8.0.json` observation; the montage verifies
committed decoded-frame hashes against `data/release-0.8.0.json`. These records
are not measurements of subsequent edits. Old unbound inputs remain historical,
not fallbacks. A paper-figure refresh is an explicit input replacement, not automatic
acquisition of an external paper.

Pandoc, pandoc-crossref and a compatible LaTeX engine are prerequisites for the
manuscript gates/full PDF. Engineering gate declarations in `domain_profile.yaml`
are not evidence of passing runs. Source-identified run receipts hold exercised results.

The canonical package-video recipe remains Kokoro `af_heart` at 2160p; see
[../videos.md](../videos.md). The curated paper demo requires explicitly supplied,
unshipped external inputs, and is distinct from the historical template paper
render. An identified candidate package render is now recorded, but no
independent acoustic evaluation or release readiness is established.

The pre-existing blocking `sync_accuracy` criterion is pending/unmet: there is
no independently annotated corpus or executable acoustic oracle. Passing the
engineering checks cannot establish release/manuscript readiness under that bar.
