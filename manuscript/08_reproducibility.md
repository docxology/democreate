# Reproducibility and Use {#sec:reproducibility}

This section records the concrete steps to install DemoCreate, run its test gate, and produce a demo — of either software or a research paper — so that the claims of [@sec:evaluation] are independently checkable.

## Environment and Installation

The package targets Python 3.10 and later and is managed with uv [@astral2024uv] for reproducible, lockfile-driven environments. The core dependencies are deliberately light — `pyyaml`, `typer`, `rich`, `jinja2`, and `pillow` — so an editable install pulls no heavy binaries:

```bash
uv venv
uv pip install -e ".[dev]"
```

Optional heavy backends are installed only as needed, each named for the subsystem it upgrades:

```bash
uv pip install -e ".[tts]"        # Kokoro / Chatterbox neural TTS
uv pip install -e ".[whisper]"    # Whisper word-level transcription
uv pip install -e ".[capture]"    # mss real-pixel screen capture
uv pip install -e ".[browser]"    # Playwright website driving
uv pip install -e ".[animation]"  # Manim animation
uv pip install -e ".[video]"      # video helper packages; ffmpeg binary still required
uv pip install -e ".[all]"        # everything
```

Several upgrade paths need no pip extra at all, only usable system binaries: real spoken narration via the operating system's `say`/`espeak` after a synthesis/transcode smoke test (the `SystemTTSBackend`, [@sec:architecture]), and research-paper ingestion via the poppler utilities [@poppler2024] ([@sec:paper]). The final video encode and the EBU R128 loudness pass ([@sec:composition]) use `ffmpeg`. The `democreate backends` command reports, at runtime, which extras and binaries are present and which capabilities are running on their deterministic default — confirming that every capability has a working default backend.

## The Test Gate

The test gate is the primary reproducibility check. It runs the full 666-test suite against real artifacts and enforces the ≥90% coverage threshold configured in `pyproject.toml`, which the current suite clears at 92.93%:

```bash
uv run pytest --cov=src/democreate --cov-report=term-missing
```

Because the suite is pure-Python and uses no mocks, it requires only the core and `dev` dependencies; it does not need any heavy backend installed. Tests that would exercise an optional heavy backend skip cleanly when the extra is absent. Static checks — `ruff` for linting and import ordering, `mypy` for typing against the shipped `py.typed` marker — complete the gate.

## Producing a Software Demo

The CLI is a thin orchestration layer over the library; every command resolves to a few calls into the pipeline and subsystems. Its commands are `init`, `inspect`, `build`, `tour`, `captions`, `render`, `verify`, `paper`, `backends`, and `version`. The quickest path from nothing to an inspectable artifact is:

```bash
democreate init demo.json          # write an editable starter demo
democreate inspect demo.json       # validate and summarize it
democreate build demo.json -o out  # run the full pipeline
```

`build` runs validation, TTS, TTS→STT synchronization, timeline resolution, compositing, caption emission, and export, writing audio, frames, a render manifest, SRT/VTT captions, a Markdown transcript, the serialized demo JSON, and a self-contained interactive HTML player under `out/`. To produce and *content-verify* an HD MP4 with a real voiceover and a chosen theme:

```bash
democreate render demo.json -o out --tts system --voice Samantha --theme midnight
democreate verify out/<video>.mp4 --width 1920 --height 1080
```

A complete codebase tour can be generated and rendered directly from a repository:

```bash
democreate tour /path/to/repo -o out --title "My Project Tour"
```

This walks the repository's Python sources with the stdlib `ast`-based summarizer, generates a declarative `Demo` via `generate_codebase_demo`, writes it to `out/demos/tour.json`, and renders it.

## Producing a Research-Paper Demo

The paper path ([@sec:paper]) is a single command from a PDF (and optionally its figures and codebase) to a verified video:

```bash
democreate paper paper.pdf --repo ./code --figures ./figures --theme paper
```

This reads the PDF through poppler, extracts the title, authors, the real abstract, figure captions, and sections, collects the figure images, walks the codebase for an architecture diagram, composes a `Demo`, renders it, and runs `verify_video`. The *Policy Entanglement* worked example of [@sec:evaluation] is reproduced by exactly this invocation.

Subtitles for any demo can be emitted to standard output in SRT, VTT, or ASS form via `democreate captions demo.json --format vtt`. Worked examples accompany the package under `examples/`, and because a demo is a plain JSON or YAML value, every example — and every figure in this manuscript — is itself a reproducible input that re-renders identically ([@sec:evaluation]).
