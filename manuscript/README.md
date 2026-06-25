# DemoCreate Manuscript (v0.6.2)

Academic write-up of **DemoCreate** (`democreate`) — a Python package that
generates audio-visual demos of **software** (codebase tours, website
walkthroughs, terminal/CLI sessions) **and research papers** (PDF + figures +
codebase) from a single declarative, deterministic source.

## What the paper argues

A demo should be a *value*, not a recording. DemoCreate represents a demo as an
ordered stream of typed actions over a virtual environment (editor, terminal,
browser, camera) interleaved with chunked narration — fusing CodeVideo's
event-sourced virtual-IDE model with VSpeak's chunk-and-trigger narration model
— and *compiles* that value into frames, audio, captions, an interactive
player, and a content-verified HD MP4. Four ideas carry the design:

1. **A declarative deterministic spine** (`schema.py`): a self-validating,
   losslessly-serializable `Demo` value from which rendering is a pure function.
2. **Backends behind interfaces with pure-Python defaults**: TTS (silent
   default; zero-pip `say`/`espeak`; optional Kokoro/Chatterbox), transcription
   (Whisper), capture (mss, Playwright), animation (Manim), video assembly
   (ffmpeg), and PDF ingestion (poppler) are each upgrades over a working
   stdlib/Pillow default, so the package produces a real demo with five light
   dependencies and upgrades in fidelity, not capability.
3. **TTS→STT synchronization**: narration is synthesized, transcribed back to
   word timestamps, and each action's trigger word is anchored to a *measured*
   spoken time; each frame is held for its clip's measured duration on a
   gap-aware timeline.
4. **Configurable composition and research-paper demos**: themes, scaled fonts,
   pygments highlighting, character-by-character **typing animation**, an
   **animated cursor** with click ripple, a moving waveform, transitions, Ken
   Burns (**off by default** — zoom crops content), **aspect-ratio presets**
   (16:9 / 9:16 / 1:1 / 4:3 / 4:5), **resolution tiers** to 4K at a near-lossless
   crf 18, and EBU R128 loudness are controlled by one `RenderConfig`, with
   **chapter / poster / GIF** export alongside the MP4. The **no-crop
   layout** treats every frame as a page: Ken Burns off, background figures/pages
   fit *whole* (contain) with the caption below, code autosizes to fit and
   wraps rather than clipping, and the progress line sits at the absolute top edge
   so it never clips the top of a figure. The default look is **noir** (near-black
   with a single red accent), one of five themes, with larger type across all of
   them. The `paper/` subsystem turns a PDF into a narrated
   demo, extracting the *real* abstract (skipping the TOC), figure captions, and
   sections (worked example: the *Policy Entanglement in Active Inference* paper
   — a 170-page PDF, ~1200-char abstract, 6-part section structure,
   145-module codebase → a 188.0-second, −15.5 dB, 1920×1080 H.264 video).
5. **Three-carrier provenance and distribution**: one `MetadataConfig`
   stamps attribution onto a render via **on-screen overlay bars**, **MP4
   container tags**, and a **signed steganographic payload** hidden in lossless
   poster/bookend PNG sidecars. The hidden payload survives lossless PNG only —
   the H.264 video carries provenance through its bars and container tags — and a
   render-state-excluding content digest makes verification stable and
   tamper-evident (`verify_provenance` → `True` vs the original demo, `False` vs
   an edited one).

## Layout

| File | Contents |
|------|----------|
| `00_abstract.md` | Abstract (opens with the graphical abstract, `@fig:graphical_abstract`) |
| `01_introduction.md` | Problem space and the four-stage pipeline |
| `02_architecture.md` | Spine, backends-behind-interfaces, deterministic defaults (`@fig:architecture`) |
| `03_synchronization.md` | The TTS→STT round-trip, audio-as-ground-truth, gap-aware timeline |
| `04_implementation.md` | Subsystems incl. config/audio/animation/paper + typing-reveal pseudocode (`@fig:frame_code`, `@fig:waveform`) |
| `05_composition_and_configurability.md` | Themes, fonts, pygments, typing reveal, animated cursor, aspect presets, chapter/poster/gif export, Ken Burns, normalization (`@fig:themes`, `@fig:frame_title`, `@fig:typing_filmstrip`) |
| `06_research_paper_demos.md` | The `paper/` subsystem, real abstract/caption/section extraction, the actinf worked example (`@fig:frame_paper`, `@fig:paper_flow`) |
| `07_evaluation.md` | Measured benchmarks (`@fig:latency`), testability (677 collected tests, ≥90% gate), the content verifier, tamper-evident provenance + 4K geometry, two real videos (re-rendered in noir) with stills (`@fig:video_stills`) |
| `08_reproducibility.md` | uv, editable install, test gate, `render`/`paper`/`verify` |
| `09_scope_and_related_work.md` | Honest comparison with prior art |
| `10_provenance_and_distribution.md` | Three-carrier provenance (overlay bars, container tags, signed steganographic sidecars), the content digest, resolution tiers + crf (`@fig:provenance`) |
| `99_references.md` | Reference list anchor |
| `references.bib` | BibTeX for every cited work |
| `config.yaml` | Pandoc/build manifest |
| `preamble.md` | LaTeX packages (`listings`, `siunitx`) |
| `figures/` | Generated figures + `make_figures.py` |
| `SYNTAX.md` | Authoring conventions |
| `AGENTS.md` | Machine-readable chapter/figure index and invariants |

## Figures

Figures are produced by calling the real `democreate` APIs (and, for
`video_stills.png`, by montaging real frames extracted from the produced demo
videos). Regenerate from the project root:

```bash
.venv/bin/python manuscript/figures/make_figures.py
```

The generated figures are:

| Figure | Contents |
|--------|----------|
| `graphical_abstract.png` (`@fig:graphical_abstract`) | The cover figure: a codebase or paper compiling through the deterministic pipeline into a verified, provenance-signed video (generated by `graphical_abstract.py`) |
| `architecture.png` (`@fig:architecture`) | The canonical four-stage pipeline diagram |
| `frame_code.png` (`@fig:frame_code`) | A CODEBASE editor frame (pygments + fonts) |
| `frame_title.png` (`@fig:frame_title`) | A SLIDE title card |
| `frame_paper.png` (`@fig:frame_paper`) | A SLIDE over a real paper figure (paper theme) |
| `waveform.png` (`@fig:waveform`) | A speech-waveform scrubber strip |
| `themes.png` (`@fig:themes`) | One code frame under five themes (noir is the default) |
| `typing_filmstrip.png` (`@fig:typing_filmstrip`) | One editor frame typed to 25/55/100% |
| `latency.png` (`@fig:latency`) | Measured latency bars from `benchmarks.json` |
| `paper_flow.png` (`@fig:paper_flow`) | The paper-pipeline flow diagram |
| `provenance.png` (`@fig:provenance`) | The three provenance carriers from one `MetadataConfig` |
| `video_stills.png` (`@fig:video_stills`) | A 2×2 montage of real stills from the two produced demo videos |

## Building

The manuscript follows the docxology `template_code_project` conventions:
numbered level-one headers with `{#sec:...}` identifiers, Pandoc citations,
`![...](figures/x.png){#fig:x}` figure insertions, and no manual section
numbers. Render with the project's Pandoc + XeLaTeX pipeline using `config.yaml`
as the manifest; citations resolve against `references.bib` with
`fail_on_missing: true`.
