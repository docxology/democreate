# Examples

All JSON artifacts use schema **1.1**. Background images are relative to the
Demo file directory; each generator stages its assets under sibling `assets/`.
Do not replace those paths with author-machine or sibling-project paths.

## Canonical package showcase

`make_showcase.py` writes `democreate_showcase.json` and copies committed figure
inputs into `examples/assets/`. Fifteen scenes demonstrate slides, illustrative
code views and terminal commands—not captured repository source, a website
capture or all SceneKinds. Code panels use `illustrative_*.py` labels rather than
impersonating current source files. Stat cards describe gates, not a test total.

The canonical render is **Kokoro `af_heart`, 2160p**, requiring the `tts` extra,
model/voice files and ffmpeg. Source-bound runs, exact inputs and limitations
are recorded in [`data/visual-refresh-2026-11-08.json`](../data/visual-refresh-2026-11-08.json);
this is engineering media proof, not listening or acoustic accuracy.

```bash
.venv/bin/python examples/make_showcase.py
democreate render examples/democreate_showcase.json -o output \
  --tts kokoro --voice af_heart --resolution 2160p \
  --author "Daniel Ari Friedman"
democreate verify output/video/demo.mp4 --width 3840 --height 2160
```

The earlier 155.6-second record is historical; a regenerated narration has its own
duration. PNG provenance payloads are unsigned consistency records, not signatures.

## Earlier introduction

Nine scenes introduce the architecture, spine, backends, clip timing, player and
CLI. Committed architecture/dashboard inputs are available under `assets/`.

```bash
.venv/bin/python examples/make_intro_demo.py
democreate build examples/democreate_intro.json -o output/intro
democreate render examples/democreate_intro.json -o output/intro --tts system --voice Samantha
```

System rendering requires a successful `say`/`espeak` probe plus ffmpeg. Default
`build` is silent; it is not evidence of a successful voiced render.

## Optional curated paper

The curated paper's PDF/source/figure outputs are external prerequisites, not
bundled inputs. Obtain the intended *Policy Entanglement* project explicitly:

```bash
.venv/bin/python examples/make_paper_showcase.py --paper-root /path/to/paper
democreate render examples/democreate_paper_showcase.json -o output/paper_showcase \
  --tts system --voice Daniel
```

The builder requires `output/pdf/actinf_policy_entanglement_lean_combined.pdf`,
`src/` and its named `output/figures/*.png` inputs. Before staging any bytes, it
resolves the PDF, figures and source tree and rejects links escaping the selected
`--paper-root` (including source descendants). The explicitly selected root is
the authority, even if it is itself a link. Missing inputs fail; there is no
fallback project. It never writes into the supplied project.
See [video recipes](../docs/videos.md) for curated versus template identities.
