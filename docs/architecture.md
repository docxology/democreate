# Architecture

DemoCreate has one organizing idea: **a `Demo` is the single declarative source
of truth, and rendering is a pure function of it.** Everything else is a backend
that consumes the spine and writes artifacts into a `Workspace`.

## The spine

The spine is pure Python — no I/O, no heavy dependencies — and lives in a handful
of modules at the package root:

| Module | Role |
|--------|------|
| `schema.py` | The declarative model: `Demo` → `Scene` → `Chunk` → `Action`, the `ActionType` / `SceneKind` enums, and `WordTimestamp`. Lossless `dict`/JSON/YAML round-trip and `Demo.validate()`. |
| `media.py` | Shared media value types exchanged between subsystems: `AudioClip` (a rendered narration clip) and `FrameState` (a renderable snapshot of the virtual environment). |
| `errors.py` | The `DemoCreateError` hierarchy, including `BackendUnavailableError` (carries the extra to install), `SchemaValidationError`, `RenderError`, `SyncError`, `CaptureError`. |
| `project_paths.py` | `Workspace` — centralizes every output location (`demos/`, `audio/`, `frames/`, `video/`, `captions/`, `web/`, `manifests/`) so no module hardcodes a path. |
| `config.py` | `RenderConfig` (`Theme` + `AudioConfig` + `VideoConfig`) — the look/sound/motion settings, YAML-loadable, threaded through the pipeline. See [config.md](config.md). |
| `pipeline.py` | `Pipeline` / `build_demo` / `render_video` — the thin orchestrator that wires the subsystems in canonical order. |
| `portfolio.py` | `render_portfolio` / `render_project` / `collect_project_facts` / `discover_projects` — a thin orchestration sibling of `pipeline.py` that turns a directory of repositories into one timestamped, content-verified summary video per project. Builds each demo via `narration.project_summary.generate_project_summary_demo` (a deterministic README + AST "describing" generator) and renders it through `pipeline`. |
| `cli.py` | The `democreate` Typer app — a thin layer over `pipeline`, `portfolio`, and the subsystems. |

### The declarative model

- **CodeVideo's event-sourced virtual-IDE model.** A `Demo`'s content is an
  ordered stream of typed `Action`s mutating a virtual environment (editor,
  terminal, browser, camera). The same stream re-renders to any output format.
- **Chunk/trigger narration.** Narration is grouped into `Chunk`s. Each `Action`
  may name a `trigger_word`; the default engine estimates its time from text and
  measured clip duration. It does not detect spoken-word onsets.

Explicit authored absolute times survive sync. Derived times carry
`timestamp_source="sync"` and refresh when narration changes.

## The subsystems

Each subsystem directory carries its own `README.md` and `AGENTS.md`. The core
defaults need no model/browser/media binaries. Native speech, MP4 and PDF
ingestion have separate prerequisites (see [backends.md](backends.md)).

| Subsystem | Owns | Default backend(s) | Upgrade |
|-----------|------|--------------------|---------|
| `capture/` | Frame rendering and recording terminal/browser/input sessions. | `SyntheticRenderer` (scaled TrueType fonts + pygments highlighting + themes), `NullBrowserDriver`, pure event model. | `capture`, `browser`, `replay` |
| `narration/` | Script generation, TTS, duration-based word estimates. | `TemplateScriptGenerator`, `SilentTTSBackend`, `HeuristicTranscriber`; optional native `SystemTTSBackend`. | `say`/`espeak` (OS), `tts`, `whisper` |
| `animation/` | Scaled fonts, speech waveform, architecture diagrams, manim specs. | `fonts.py`, `waveform.py`, `diagram.py`, JSON manim spec. | `animation` |
| `codebase/` | AST traversal, visualization, and import-dependency graphs. | stdlib `ast`. | `codebase` |
| `assembly/` | Timeline build, compositing, captions, audio assembly, timed-frame animation. | `ManifestCompositor`, pure SRT/VTT/ASS, `audio.py` (stdlib `wave` concat), `animator.py`. | ffmpeg (audio/video), `video` |
| `export/` | Turn the spine + frames + audio into deliverables, then verify. | Jinja2 HTML player, Markdown/JSON/chapters, ffmpeg-argv builder. | ffmpeg/ffprobe (`video`) |
| `paper/` | PDF ingestion and paper demos. | poppler CLI (`pdfinfo`, `pdftotext`, `pdftoppm`). | OS binaries; no `pdf` pip extra |

The look (`Theme`), sound (`AudioConfig`), and motion (`VideoConfig`) of a render
are governed by a single `RenderConfig` (`config.py`), threaded through the
pipeline, renderer, and animator — see [config.md](config.md).

## Data flow

A build enriches an isolated copy of the authored `Demo`; the caller's value
remains reusable. Read measured timing and staged asset references from
`PipelineResult.demo`. Artifacts land in the selected `Workspace`. Explicit
compositors retain their raster content during animated export; default
composition supports scheduled per-action re-rendering. `build` stops at the
HTML preview; `render` continues through encoding and basic verification.

```
script? -> validate -> stage assets -> TTS -> duration-based sync -> timeline
        -> compose (frames + manifest) -> captions -> player/transcript/json
render: -> voiceover (gaps/normalize/fade) -> animate (waveform/transitions/kenburns)
        -> encode (ffmpeg) -> verify (real/non-silent/non-black)
```

The full pipeline, from the declarative spine to a verified video (`pipeline.py`,
`assembly/`, `export/`), plus the research-paper branch (`paper/`):

```mermaid
flowchart TB
    Demo["Demo (declarative spine)<br/>scenes · chunks · actions"]
    TTS["narration.tts<br/>synthesize_demo → AudioClips"]
    Sync["narration.sync<br/>transcribe → WordTimestamps<br/>anchor actions to trigger_words"]
    Timeline["assembly.compositor<br/>build_timeline (fps, wpm)"]
    Compose["capture.screen + assembly.compositor<br/>compose → still frames (one per chunk) + manifest"]
    Captions["assembly.captions<br/>SRT / VTT / ASS"]
    Player["export.interactive<br/>HTML player · transcript · demo.json"]
    Voiceover["assembly.audio<br/>concat_with_gaps (lead/gap/trail)<br/>normalize (loudnorm) + fade"]
    Animate["assembly.animator<br/>resample @ animation_fps<br/>+ typing + cursor + waveform + top-edge progress + transitions"]
    Encode["export.video<br/>encode_frame_sequence (ffmpeg)"]
    Verify["export.verify<br/>real streams · non-silent · non-black"]
    Video(["demo.mp4 (verified HD)"])

    Demo --> TTS --> Sync --> Timeline --> Compose --> Captions --> Player
    Compose --> Animate
    TTS --> Voiceover --> Animate
    Voiceover --> Encode
    Animate --> Encode --> Verify --> Video

    subgraph Paper["paper/ branch — research papers"]
        PDF["paper.pdf"] --> PdfMod["paper.pdf (poppler)<br/>pdfinfo · pdftotext · pdftoppm"]
        PdfMod --> Extract["paper.extract<br/>PaperSummary (title/abstract/figures/pages)"]
        Figs["--figures/*"] --> Extract
        Repo["--repo (codebase)"] --> Arch["animation.diagram<br/>architecture image"]
        Extract --> Script["paper.script.build_paper_demo<br/>title · abstract · figures · pages · arch · outro"]
        Arch --> Script
        PdfMod -. page images .-> Script
    end
    Script --> Demo
```

The paper branch produces a normal `Demo`, so it flows through the very same
TTS → sync → animate → encode → verify pipeline as a software demo — see
[paper.md](paper.md).

## Measured clip durations, heuristic word timing

`SilentTTSBackend` writes actual WAVs; speech backends measure their generated
clips. `HeuristicTranscriber` interpolates known words by character length over
that duration. This is not acoustic recognition, and trigger timing does not
necessarily coincide with speech. Installing Whisper does not provide a working
recognizer: its adapter remains unimplemented. The annotated ≥30-demo/≤120 ms
study is planned, separate from structural timestamp tests.

## Determinism as a design constraint

The default path has no RNG, no wall-clock, and no network. A given `Demo`
renders byte-for-byte identically on every machine. That is what makes the demos
reproducible and what makes the test suite able to assert exact output rather than
loose tolerances. Guarded media backends may trade that exactness for fidelity,
and live behind `# pragma: no cover` adapters so they never compromise the core's
guarantees.
