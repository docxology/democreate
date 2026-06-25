# DemoCreate — Documentation Hub

`democreate` generates **narrated HD video demos** of both **software packages**
(codebase tours, website walkthroughs, terminal/CLI sessions) and **research
papers** (PDF + figures + codebase). It is built on a **declarative,
deterministic spine** — a `Demo` is scenes → chunks → actions, and rendering is a
pure function of it — and every heavy backend (TTS, transcription, capture,
animation, video assembly, PDF) sits behind an abstract interface with a
pure-Python deterministic default. The package produces a real demo with only its
light core dependencies. Optional extras and zero-pip system binaries upgrade
specific media surfaces; neural TTS, Whisper, and Manim remain guarded adapter
slots.

This `docs/` directory is the project's documentation hub. Each file is focused
and self-contained.

## Map of the docs

| Doc | What it covers |
|-----|----------------|
| [architecture.md](architecture.md) | The spine, the subsystems, the full data flow (`Demo → tts → sync → timeline → compose → animate → encode → verify`), the paper branch, and the pipeline mermaid diagram. |
| [quickstart.md](quickstart.md) | Clean clone to a rendered demo: `uv` install, `build`, `render --theme`, `paper <pdf> --repo`. |
| [recipes.md](recipes.md) | A cookbook of runnable commands: software demo, paper demo, vertical `9:16` cut, themed render, GIF + thumbnail, chapters, typing animation, optional LLM narration. |
| [gallery.md](gallery.md) | **Real rendered frames** — a typing editor frame, a paper figure, a title slide, the architecture diagram, and a theme strip — produced by [`_gallery/make_gallery.py`](_gallery/make_gallery.py). |
| [videos.md](videos.md) | **The two produced videos** — the package demo (`output/video/demo.mp4`) and the research-paper demo (`output/paper_demo/video/demo.mp4`): exact paths, sizes/durations, one-line regenerate commands, what each shows, companion artifacts, and real embedded stills. |
| [schema.md](schema.md) | Full reference of `Demo` / `Scene` / `Chunk` / `Action` / `ActionType` / `SceneKind`, with a JSON example. |
| [cli.md](cli.md) | Every `democreate` command — `init`, `inspect`, `build`, `tour`, `captions`, `render`, `verify`, `paper`, `thumbnail`, `gif`, `config`, `stego`, `backends`, `version` — with all options. |
| [config.md](config.md) | `Theme` / `AudioConfig` / `VideoConfig` / `MetadataConfig` / `RenderConfig`, the **five theme presets** (default **noir**), **resolution tiers**, aspect presets, a sample YAML, and `democreate config` / `--config` / `--theme` / `--resolution` / `--aspect`. |
| [video.md](video.md) | The animated render: typing animation, animated cursor, waveform, progress bar, scene transitions, Ken Burns, `animation_fps`, **resolution & quality (`crf`/`preset`)**, **on-screen metadata bars**, encode, and content verification. |
| [audio.md](audio.md) | Voiceover assembly: the system voice, lead/gap/trail silence, `loudnorm` normalization, and fades. |
| [paper.md](paper.md) | The research-paper workflow end-to-end: real abstract / figure captions / sections, PDF pages, figures, and a codebase become narrated scenes. |
| [provenance.md](provenance.md) | The provenance/metadata story: on-screen top/bottom metadata bars, MP4 container tags (`ffprobe`), and the signed steganographic provenance in lossless PNG sidecars (`democreate stego` to verify). |
| [backends.md](backends.md) | Every subsystem mapped to its deterministic default, the optional extra (or zero-pip system binary) that upgrades it, plus optional LLM narration and the chapters / metadata / poster exports. |
| [api.md](api.md) | **Generated** API reference (public classes + functions per module) — regenerate with [`scripts/generate_api_docs.py`](../scripts/generate_api_docs.py). |
| [AGENTS.md](AGENTS.md) | Operating rules for agents in this repo: thin orchestrators, no-mock tests, ≥90% core coverage, deterministic defaults, no top-level heavy imports. |
| [testing_philosophy.md](testing_philosophy.md) | No mocks, deterministic, pure-core coverage gate, and the `backend` skip marker. |
| [troubleshooting.md](troubleshooting.md) | Common failures: missing extras → `BackendUnavailableError`, headless rendering, `ffmpeg`/poppler on `PATH`. |

## Where else to look

- **Subsystem docs** live next to the code. Subsystem directories under
  `src/democreate/` carry their own `README.md` (what it does) and `AGENTS.md`
  (rules for changing it): `capture/`, `narration/`, `animation/`, `codebase/`,
  `assembly/`, `export/`, `paper/`. Read the local pair before touching a
  subsystem.
- **Source of truth for behavior** is the code and its tests under `tests/`. The
  docs here describe intent and contracts; the tests (664 collected, ≥90% coverage)
  enforce them.

## The three load-bearing ideas (one paragraph each)

1. **Declarative spine.** All content is a single `Demo` artifact — scenes →
   chunks → actions (typed `Action`s plus narration `Chunk`s). Rendering is a
   pure function of the artifact, so you edit the `Demo` and re-render rather than
   re-record. This merges CodeVideo's event-sourced virtual-IDE model with
   VSpeak's chunk/trigger narration model.

2. **Backends behind interfaces.** Every heavy capability — TTS, transcription,
   screen capture, browser drive, animation, video assembly, PDF reading — sits
   behind an abstract base class with a pure-Python deterministic default. The
   default carries the whole pipeline to a real, inspectable result with no heavy
   binaries required; the highest-value upgrades (real voice, real video, PDF)
   are **zero-pip system binaries** (`say`/`espeak`, `ffmpeg`, poppler).

3. **TTS → STT synchronization.** Narration audio is generated, then transcribed
   back to word-level timestamps; each on-screen `Action` anchors to a spoken
   `trigger_word`, and each frame is held for its clip's *measured* duration.
   Real audio is the single source of timing truth.

## Prior art

DemoCreate stands on a line of demo-generation and recording tools:
[CodeVideo](https://github.com/codevideo), VSpeak, asciinema, termtosvg,
Recordly, [code-video-generator](https://github.com/sleuth-io/code-video-generator),
Code2Video, and Paper2Video. See [architecture.md](architecture.md) for how the
spine reconciles the event-sourced and chunk/trigger lineages, and
[paper.md](paper.md) for the research-paper branch.
