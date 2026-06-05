# Quickstart

From a clean clone to a rendered demo. Requires Python ≥ 3.10 and
[uv](https://github.com/astral-sh/uv). No heavy binaries (ffmpeg, torch, chrome)
are needed for the default path — the deterministic backends carry the whole
pipeline.

## 1. Create the environment and install

```bash
uv venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

This installs the light core dependencies (pyyaml, typer, rich, jinja2, pillow)
plus the dev toolchain (pytest, pytest-cov, ruff, mypy).

Verify the install imports cleanly on core deps and the CLI is on `PATH`:

```bash
python -c "import democreate; print(democreate.__version__)"
democreate version
```

## 2. Write a starter demo and inspect it

`init` writes a small, valid `Demo` artifact you can edit. `inspect` validates it
and prints a structural summary.

```bash
democreate init demo.json           # or: --format yaml
democreate inspect demo.json
```

`inspect` reports scene/chunk/action counts, an estimated duration, and whether
the demo is valid (exit code 1 if not).

## 3. Build a demo from JSON

`build` runs the full pipeline — TTS, TTS→STT sync, timeline, frames + manifest,
captions, and an interactive HTML player — into an output workspace.

```bash
democreate build demo.json --output output
open output/web/player.html         # Linux: xdg-open
```

The workspace layout (created lazily) is:

```
output/
  demos/        demo.json · transcript.md (paper: paper.json)
  audio/        rendered narration + voiceover (.wav)
  frames/       rendered still frames (.png); frames/anim/ animated frames
  captions/     captions.srt · captions.vtt
  web/          player.html  ← open this
  manifests/    deterministic render manifest (.json)
  video/        demo.mp4 (after render)
  pages/        rasterized PDF pages (paper)
  assets/       architecture.png (paper)
```

With only core deps, the audio is deterministic silence sized to the narration,
and the frames are synthetic (Pillow) renders — a real, inspectable demo.

## 4. Tour a real codebase

Point `tour` at a repository to auto-generate a codebase-walkthrough demo from its
AST and (by default) render it:

```bash
democreate tour /path/to/repo --title "My Project Tour" --output output
```

## 5. Render a real HD video with a spoken voiceover

`render` goes past the player: it speaks the narration with a real OS voice,
**animates** the frames (character-by-character typing, animated cursor, moving
waveform, a top-edge progress line, scene transitions), encodes an HD MP4 with
`ffmpeg`, and content-verifies it. The default theme is **noir** and figures are
fit *whole* (no crop). Needs a system TTS (`say` on macOS, `espeak` on Linux) and
`ffmpeg` on `PATH`.

```bash
democreate render demo.json -o output --tts system --voice Samantha
democreate render demo.json --theme midnight              # a theme preset
democreate render demo.json --config my_theme.yaml        # full RenderConfig
open output/video/demo.mp4
```

Pick a theme preset (`noir` — the default — `dark`/`light`/`midnight`/`paper`)
with `--theme`, or pin everything in a YAML config with `--config` (see
[config.md](config.md), [video.md](video.md), [audio.md](audio.md)).

## 6. Make a demo of a research paper

Point `paper` at a PDF — optionally with the paper's codebase and a directory of
exported figures — to generate and render a narrated paper walkthrough. Needs
poppler (`pdfinfo`/`pdftotext`/`pdftoppm`) on `PATH`, plus a system TTS and
`ffmpeg` to render. See [paper.md](paper.md).

```bash
democreate paper paper.pdf --repo /path/to/code --figures /path/to/figs --theme paper
open output/video/demo.mp4
```

## 7. Use it as a library

```python
from democreate import Demo
from democreate.pipeline import build_demo
from democreate.project_paths import Workspace

demo = Demo.from_json(open("demo.json").read())
result = build_demo(demo, Workspace("output"))
print(result.summary())             # scenes, chunks, actions, duration, player path
```

## 8. Install extras for high fidelity

Each extra upgrades one subsystem from its deterministic default to a real
backend. Install only what you need (see [backends.md](backends.md)):

```bash
uv pip install -e ".[tts]"          # Kokoro/Chatterbox real narration
uv pip install -e ".[whisper]"      # Whisper word-timestamp transcription
uv pip install -e ".[capture]"      # mss real screen capture
uv pip install -e ".[browser]"      # Playwright website driving
uv pip install -e ".[animation]"    # Manim code animations
uv pip install -e ".[video]"        # MoviePy/ffmpeg video assembly
uv pip install -e ".[codebase]"     # tree-sitter multi-language analysis
uv pip install -e ".[all]"          # everything
```

Check what is active at any time:

```bash
democreate backends
```

Each capability shows `installed` (extra present) or `default` (deterministic
fallback in use). Invoking a real backend without its extra raises
`BackendUnavailableError` with the exact `uv sync --extra <extra>` hint.

## 9. Run the tests

```bash
.venv/bin/python -m pytest -q                 # full suite (no mocks)
.venv/bin/python -m pytest --cov              # coverage gate (≥90% core)
ruff check . && mypy src
```
