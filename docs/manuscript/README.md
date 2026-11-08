# DemoCreate manuscript — candidate 0.8.0

Chapters describe a declarative Demo pipeline for software and research-paper
presentations. `config.yaml` is the chapter/build manifest; `SYNTAX.md` describes
Pandoc conventions. Publication is pending. The existing concept DOI currently
resolves to archived **0.6.2**, not a new 0.8.0 archive.

## Evidence boundaries

- Clip durations are measured; default word timestamps interpolate known text
  by character length. No acoustic recognition or measured onset accuracy is
  claimed. Whisper, Chatterbox and Manim remain unwired slots; Kokoro is implemented.
- The ≥30-demo annotated corpus and ≤120 ms median-error hypothesis are planned.
- The real-filesystem suite has a ≥90% core coverage gate. Counts and current
  coverage results belong in run receipts, not prose or pixels.
- `data/benchmarks.json` is a historical aggregate record without original run
  identity. Build timing includes TTS/sync/frames/exports; render timing covers
  the whole `render_video` call with verification disabled. Mean dB is not LUFS.
- PNG digest payloads are unsigned consistency checks, not signatures,
  authentication, or image/video identity.
- Committed cover, video montage and stills predate the 2026-11-07 repair.
  Original extraction dates/video digests are unrecorded; obsolete labels in the
  pixels are not current evidence. The existing montage is package-only 3×2,
  not the proposed package/paper 2×2 layout.

## Regeneration from the repository root

```bash
.venv/bin/python docs/manuscript/figures/make_figures.py
.venv/bin/python docs/manuscript/figures/graphical_abstract.py
.venv/bin/python scripts/build_manuscript.py --check
.venv/bin/python scripts/build_manuscript.py
```

The figure generator uses committed repository inputs, including local
`figures/paper_fig.png`; it neither searches nor writes sibling repositories.
It mirrors figures into root `output/figures/`. Current timing consumes
`data/benchmarks-0.8.0.json`; the montage verifies committed decoded-frame hashes
against `data/release-0.8.0.json`. Old unbound inputs remain historical, not
fallbacks. A paper-figure refresh is an explicit input replacement, not automatic
acquisition of an external paper.

Pandoc, pandoc-crossref and a compatible LaTeX engine are prerequisites for the
manuscript gates/full PDF. Engineering gate declarations in `domain_profile.yaml`
are not evidence of passing runs. Parent release receipts hold exercised results.

The canonical package-video recipe remains Kokoro `af_heart` at 2160p; see
[../videos.md](../videos.md). The curated paper demo requires explicitly supplied,
unshipped external inputs, and is distinct from the historical template paper
render. An identified candidate package render is now recorded, but no
independent acoustic evaluation or release readiness is established.

The pre-existing blocking `sync_accuracy` criterion is pending/unmet: there is
no independently annotated corpus or executable acoustic oracle. Passing the
engineering checks cannot establish release/manuscript readiness under that bar.
