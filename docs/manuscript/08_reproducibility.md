# Reproducing Core Builds and Optional Voiced Renders {#sec:reproducibility}

This section provides the manuscript's installation, gate and rendering recipes. They are instructions for obtaining evidence, not commands executed for this chapter or current passing receipts. Independent reproduction requires fixed source, inputs/assets, configuration and runtime versions. The blocking voiced-acoustic study and both required error medians are defined in [@sec:evaluation]; none of the commands below substitutes for that independent evaluation.

## Locked Core Environment and Backend-Specific Prerequisites

Candidate 0.8.0 requires Python ≥3.11.5 and Pillow ≥13; the build backend requires setuptools ≥84.2.1. The patch floor excludes legacy locked dependency partitions with known advisories. The checkout's core development pin remains Python 3.15; that support statement does not establish that every optional dependency has a compatible wheel. uv [@astral2024uv] and the lockfile can record an environment, but an editable pip install by itself does not enforce it. Core dependencies are `pyyaml`, `typer`, `rich`, `jinja2` and `pillow`; Pillow includes native components although a silent core build needs no external media executable.

```bash
uv sync --locked
```

Optional heavy backends are installed only as needed, each named for the subsystem it upgrades:

```bash
uv sync --locked --extra tts        # implemented Kokoro; needs compatible runtime/model files
uv sync --locked --extra whisper    # dependency only; transcription adapter unwired
uv sync --locked --extra capture    # mss; needs a usable display/session
uv sync --locked --extra browser    # also needs installed Playwright browser binaries
uv sync --locked --extra animation  # Manim dependency only; render adapter unwired
uv sync --locked --extra video      # helper packages; ffmpeg binary still required
```

Kokoro additionally needs model/voice files (`democreate fetch-voice` downloads them), phonemization prerequisites and a compatible ONNX runtime. The locked ONNX distribution has no CPython 3.15 wheel. The fresh 2026-11-08 run reused the repository-local Python 3.14.10 voice environment without changing the 3.15 core pin or reinstalling dependencies. A process-local source path and import assertion selected current repository code. Package/model identities and limits are in `data/visual-refresh-2026-11-08.json`; the earlier `data/release-0.8.0.json` remains immutable history. Before/after model hashes are not supplier authentication or kernel-enforced immutability of the large asset. Installing `[all]`, or selecting a backend name, is not evidence of usable speech.

System narration needs a usable `say` or `espeak` voice and the required transcode path. Paper ingestion needs poppler [@poppler2024]; encoding, loudness processing and media inspection need usable ffmpeg/ffprobe binaries. The backend table is an availability aid, not a capability test: dependency presence does not wire the Whisper, Chatterbox, Manim or legacy MoviePy slots. Core defaults produce silent audio and synthetic visuals, not real speech, browser activity or optional-adapter evidence.

## Obtaining a Source-Identified Core Coverage Receipt

The engineering gate runs the real-filesystem suite and enforces the ≥90% configured core coverage floor. Results and counts require a fresh receipt, not a current percentage copied into prose:

```bash
uv run --locked python -m pytest --cov=src/democreate --cov-report=term-missing
```

The core suite is designed around real temporary files and deterministic backends rather than a mocking framework; optional integration surfaces have separate prerequisites and may skip when unavailable. Core coverage excludes designated heavy adapters, so even a passing ≥90% core floor would not establish optional-backend correctness. Static lint/type gates use ruff and mypy against the shipped `py.typed` package. Fresh results must identify their source revision and environment; no current test count, coverage percentage or passing gate is asserted here.

## Silent Software Build, Image Preview, and Optional MP4

The CLI delegates to the library's pipeline and subsystems. It includes authoring/inspection, build/render, tours/portfolios, paper ingestion, captions, configuration, localization, metadata/media exports and backend discovery. An illustrative starter workflow is:

```bash
democreate init demo.json          # write an editable starter demo
democreate inspect demo.json       # validate and summarize it
democreate build demo.json -o out --asset-root .  # silent core build
```

`build` validates, stages allowed image inputs, synthesizes silent WAVs by default, measures clip durations, interpolates known-text word timing, resolves the timeline, composites representative stills, and emits captions/transcript/JSON/HTML. It does not perform STT. `out/web/player.html` is a timed image preview without audio playback; it embeds interface code and caption/chapter data but references sibling `out/frames` images. Keep that bundle together. Animated MP4 with a voiceover is a separate render path. For an optional system-voice MP4, first supply an actually available voice and the binary prerequisites; the following macOS voice name is an example, not a portable guarantee:

```bash
democreate render demo.json -o out --asset-root . --tts system --voice Samantha --theme midnight
democreate verify out/video/demo.mp4 --width 1920 --height 1080
```

The content verifier checks geometry/duration, sampled image variation and audio energy; it does not prove intelligible narration, acoustic trigger accuracy, authorship or publication readiness. Silent output cannot pass as voiced evidence merely because its clip durations are known. Voiced/encoded output is not guaranteed byte-identical across hosts.

A complete codebase tour can be generated and rendered directly from a repository:

```bash
democreate tour /path/to/repo -o out --title "My Project Tour" --render
```

This walks Python sources using the stdlib `ast` summarizer, generates a `Demo` via `generate_codebase_demo`, writes `out/demos/tour.json` and requests rendering. A voiced render still needs its backend and binaries. Repository-summary/portfolio commands shown in a synthetic terminal are illustrative strings, never executed by DemoCreate; their sample output and discovered test-function counts are not successful execution or test receipts.

## Review Paper Extraction Before Rendering with an Asset Root

The paper path ([@sec:paper]) needs a real readable PDF, poppler, and any requested source/figure inputs. For explicit control of external image inputs, generate the authored Demo first, then render with an image allow-root:

```bash
democreate paper ./inputs/paper.pdf --repo ./code \
  --figures ./inputs/figures -o out/paper --no-render
democreate render out/paper/demos/paper.json -o out/paper \
  --asset-root ./inputs --tts system --theme paper
```

The first command reads PDF metadata/text and requested pages, heuristically extracts abstract/captions/headings, collects supplied figure images and optionally summarizes code. Review those outputs: extraction is best-effort, not semantic verification. The `paper` command's direct render path derives its asset root from the figure directory or PDF directory rather than exposing `--asset-root`; the separate `render` command above makes the external image boundary explicit. The pipeline stages accepted images and writes a resolved `out/paper/demos/demo.json` with workspace-relative paths. Use that emitted artifact with the corresponding workspace when checking the poster digest, not an assumption that pre-render geometry/paths are unchanged. The historical *Policy Entanglement* example requires its unshipped PDF, figures and source; a generic paper command is not an identity-matched reproduction.

Subtitles for any demo can be emitted to standard output in SRT, VTT, or ASS form via `democreate captions demo.json --format vtt`. Worked examples accompany the package under `examples/`, and because a demo is a plain JSON or YAML value, default examples can be rebuilt with fixed inputs and environment. Optional curated paper assets and voiced media need their stated external prerequisites; historical images are not current render receipts.
