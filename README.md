# DemoCreate

**Declarative, deterministic audio-visual demo generation for software packages
and research papers.**

DemoCreate (`democreate`) turns a single declarative `Demo` artifact — a
virtual-IDE action stream with narration chunks — into a narrated HD video:
a codebase tour, a website walkthrough, a terminal session, or a **research-paper
overview** (the PDF's figures and pages plus its associated codebase). Every heavy
backend (TTS, transcription, capture, animation, video assembly, PDF) sits behind
an abstract interface with a **pure-Python / system-binary deterministic default**,
so the package produces a real, inspectable demo with only light dependencies.
Optional extras and system binaries upgrade specific media surfaces; a wired
**Kokoro neural voice** (fully local) is available, while Whisper and Manim remain
guarded adapter slots. The look (themes, fonts, motion) and sound (voice, pacing,
normalization) are fully **configurable**.

- **Status:** alpha, Python ≥ 3.11.5, MIT licensed. Version is canonical in [`pyproject.toml`](pyproject.toml).
- **CI:** [![CI](https://github.com/docxology/democreate/actions/workflows/ci.yml/badge.svg)](https://github.com/docxology/democreate/actions/workflows/ci.yml) — ruff + mypy + the full ≥90% coverage-gated suite on pushes and pull requests targeting `main`.
- **DOI (concept, resolves to latest):** [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20693216.svg)](https://doi.org/10.5281/zenodo.20693216)
- **Docs hub:** [`docs/`](docs/README.md) — architecture, schema, CLI, backends,
  testing, troubleshooting.

![Candidate capability diagram: core frames, captions and HTML; optional voiced MP4; unsigned digest association is not authentication.](docs/manuscript/figures/graphical_abstract.png)

## Watch and regenerate the demos

Candidate **0.8.0** is pending publication. The canonical package showcase is
`examples/democreate_showcase.json`, rendered with **Kokoro `af_heart`, 2160p**.
It contains slide, codebase and illustrative terminal scenes, not a browser
capture or all four scene kinds. Kokoro packages/model files and ffmpeg are
prerequisites. The 2026-11-08 candidate run verified 3840×2160 H.264/AAC,
159.867 seconds of video and non-silent audio; see the source-bound
[engineering record](data/release-0.8.0.json). Acoustic accuracy and release
readiness remain unproved.

```bash
.venv/bin/python examples/make_showcase.py
democreate render examples/democreate_showcase.json -o output \
  --tts kokoro --voice af_heart --resolution 2160p
```

All Demo background paths are relative to the Demo file's directory. Generators
stage their assets alongside their JSON under `examples/assets/`. Library users
may choose `Pipeline(asset_root=...)`; the default asset root is the current
working directory. Only that root or generated workspace assets may be read.
Resolved output references workspace-relative staged copies. Explicit output
paths are caller authority, not implicit asset access.

![Decoded candidate showcase frames](docs/manuscript/figures/video_stills.png)
*Six decoded frames from the identified Kokoro `af_heart` candidate render.
These samples establish neither intelligibility nor acoustic synchronization.*

![Historical paper scene](docs/_videoframes/paper_figure.png)
*Historical paper illustration, reviewed 2026-11-07; no current source-video
identity or render receipt is asserted. Curated-paper inputs are an optional
external prerequisite, not bundled paper results.*

See [`docs/videos.md`](docs/videos.md) for separate historical media identities,
prerequisites and regeneration commands. `output/` is generated and gitignored;
the output allowlist test checks allowed paths, not confidential-content or media
identity guarantees.

## Three load-bearing ideas

1. **Declarative spine.** All content is one `Demo` — an ordered stream of typed
   `Action`s plus narration `Chunk`s. Rendering is a pure function of it, so you
   edit the artifact and re-render rather than re-record. It combines
   [CodeVideo's](https://docs.codevideo.io/overview/) event-sourced virtual IDE
   with narration organized into chunks and word triggers.
2. **Backends behind interfaces.** TTS, transcription, capture, animation, and
   assembly each sit behind an abstract base with a deterministic default. The
   adapter-backed media path uses a system voice when its availability probe succeeds, mss/Playwright,
   poppler, and ffmpeg when present; a wired Kokoro neural voice is an optional
   local upgrade, while Whisper / Manim surfaces remain guarded adapter slots. No
   heavy binaries (ffmpeg, torch, chrome) are required for the default
   HTML/transcript/manifest result.
3. **Duration-based synchronization.** Clip durations are measured from generated
   WAVs. The default transcriber interpolates known text by character length;
   word timestamps are estimates, not acoustic onsets. Whisper is unimplemented,
   even when its dependency is installed. The ≥30-demo/≤120 ms study is planned.

## Install

Requires [uv](https://github.com/astral-sh/uv) and Python ≥ 3.11.5.

```bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"          # core + dev toolchain
```

Core dependencies are deliberately light: `pyyaml`, `typer`, `rich`, `jinja2`,
`pillow` (≥13). Python ≥3.11.5 is required. Schema 1.1 intentionally rejects
1.0; narration WAVs now use numbered names, independent of chunk IDs. Optional extras upgrade individual subsystems (see the
[extras table](#extras)).

## Quickstart

```bash
democreate init demo.json           # write a starter demo artifact
democreate inspect demo.json        # validate + summarize it
democreate build demo.json -o output
open output/web/player.html         # the interactive HTML player
```

Tour a real repository:

```bash
democreate tour /path/to/repo --title "My Project Tour" -o output
```

As a library:

```python
from democreate import Demo
from democreate.pipeline import build_demo
from democreate.project_paths import Workspace

demo = Demo.from_json(open("demo.json").read())
result = build_demo(demo, Workspace("output"))
print(result.summary())             # scenes, chunks, actions, duration, player
```

Full walkthrough: [`docs/quickstart.md`](docs/quickstart.md).

## Make a real HD video (with voiceover)

The deterministic default build produces silent audio + synthetic frames + an HTML
player. To produce an actual **1080p MP4 with a real spoken voiceover**, use
`render` — which adds a **system voice**, subject to a successful availability probe (macOS `say` / Linux
`espeak`, **zero pip installs**) and assembles the frames + voiceover into
H.264/AAC with `ffmpeg`:

```bash
democreate render demo.json -o output --voice Samantha   # → output/video/demo.mp4
democreate verify output/video/demo.mp4 --width 1920 --height 1080
```

**Want a better, fully-local AI voice?** Install the `tts` extra and fetch the
open-weight **Kokoro** neural model once, then render with it — locally, without an API key after model acquisition:

```bash
uv pip install -e ".[tts]" && democreate fetch-voice   # ~340 MB, one time
democreate render demo.json --tts kokoro --voice af_heart
```

`render` honours **audio as ground truth**: each frame is held on screen for the
*measured* duration of its narration clip, so video and voiceover share one
timebase by construction — no drift. The build then **content-verifies** the
result: it asserts a real video stream of the expected size, an audio stream
covering it, that the audio is **not silent** (mean volume above a floor), and that
a sampled frame is **not black** (pixel variance) — existence is never mistaken for
content.

By default the render is **animated** (`--animation-fps`, default 15): large
Pillow-bundled type scaled to the resolution, a **moving speech waveform** with a sweeping
playhead locked to the audio, a progress bar, and scene chrome with section
labels. A scene can use a full-frame **background image** — a generated
architecture diagram (`animation.diagram`) or a **real browser screenshot** of the
HTML player — so the video can show genuine dashboards, not just synthetic panels.
Use `--no-animate` for a faster slideshow render.

Code scenes **type in character-by-character** with live pygments highlighting, an
**animated cursor** with click ripples brings UI scenes to life, and the MP4 gets
**embedded chapter markers** (plus a YouTube chapter file). Renders are
**themeable** across five presets (`--theme noir|dark|light|midnight|paper`, noir
is the default — near-black with a single red accent), come in any **aspect ratio**
(`--aspect 16:9|9:16|1:1`) and **resolution tier** (`--resolution 720p|1080p|1440p|2160p`,
up to 4K — everything scales to frame height), encode near-visually-lossless
(`crf 18`), and are fully configurable from a YAML file (`--config theme.yaml`):
colors, font scale, voice, pacing, loudness normalization, transitions, Ken Burns,
typing, and metadata. `democreate config` writes a fully-commented config to edit.
There are also `democreate thumbnail` (poster) and `democreate gif` (preview)
commands. See [`docs/config.md`](docs/config.md), [`docs/video.md`](docs/video.md),
and [`docs/recipes.md`](docs/recipes.md).

### Provenance, metadata & steganography

Every render can carry its own provenance three ways (`--author`, `--watermark`,
or the `metadata:` block in a config): **on-screen** top/bottom metadata bars
(author · source · running clock · watermark); **MP4 container tags**
(`title`/`artist`/`comment`, readable by players and `ffprobe`); and a
**unsigned steganographic** JSON in a lossless poster. Its content digest checks
consistency against a Demo; it is not a signature, authorship authentication,
image/video identity check or adversarial tamper resistance. The pipeline emits
`poster.png`, `poster_signed.png` (a historical filename), and `provenance.json`,
not transmission-bookend PNGs. Check against the resolved Demo:

```bash
democreate stego output/provenance/poster_signed.png --demo output/demos/demo.json
```

(Honest note: LSB survives in the lossless PNG sidecars only; the H.264 video
carries the container tags instead.) See [`docs/provenance.md`](docs/provenance.md).

**Dogfooded:** DemoCreate's own intro video is itself a DemoCreate demo —
[`examples/make_assets.py`](examples/make_assets.py) generates the architecture
diagram + a real player screenshot, [`examples/make_intro_demo.py`](examples/make_intro_demo.py)
builds the artifact, then `democreate render examples/democreate_intro.json` produces a
1080p narrated walkthrough (duration depends on voice and configuration) with pygments code, a moving waveform, scene
crossfades; Ken Burns is optional and off by default. See [`examples/README.md`](examples/README.md).

## Summarize a whole folder of projects

`democreate portfolio` turns a directory of repositories into a shelf of narrated
**software-describing** videos — one timestamped, content-verified MP4 per project:

```bash
democreate portfolio ~/code -o output --voice Samantha
# → output/<project>/video/<project>-summary-<UTC>.mp4  (one folder per project)
# → output/project_videos/<project>-summary-<UTC>.mp4    (every video, flat, one place)
# → output/portfolio_index.json  +  output/portfolio_index.html  (a gallery)
```

Each project keeps its own `output/<project>/` workspace **and** a copy of its
summary video is gathered into a flat `output/project_videos/` folder, so all the
videos — for any number of projects — sit in one browsable place. Both are
gitignored (regeneratable).

Each summary is *describing*, not enumerating. From a first-principles read of what
makes a viewer understand software, it builds a fixed seven-beat arc regardless of
repo size: a **title** card, a **what-it-is** bullet slide pulled from the real
README, an **architecture** diagram of the project's real packages, a
**by-the-numbers** stat card (modules · lines · classes · functions), two or three
of the most **load-bearing modules** shown as real typed source narrated from their
**real docstrings**, a **how-to-run** terminal scene, and an **outro**. Selection
and extraction — not a model and not a one-scene-per-module list — carry the
description, so the default needs no network and the generated demo is
byte-deterministic. A project that fails to render is recorded in the index and the
batch continues; one bad repo never aborts the run. Discovery is Python-AST +
README based; a non-Python repo still gets a README/stat summary (without code
scenes).

Because the narration is *extracted* from the repository, a summary is only as
informative as the project's own README and docstrings: content verification
asserts the video is **real** (non-silent, non-black streams at the expected
size), not that the narration is good. A repo with a thin README or undocumented
modules still renders a valid, verified video — just a thinner one.

For a single repository, `democreate tour REPO --render` closes the same loop —
generate the tour demo and render it straight to a verified MP4. See
[`docs/cli.md`](docs/cli.md).

## Localized videos — audio and subtitles in different languages

`democreate localize` renders a demo with **audio in one language and subtitles in
another** — English audio with Russian subtitles, or vice-versa — using a **local,
configurable** translator (an [`ollama`](https://ollama.com) server; no cloud, no
API key). The narration is translated to the audio language and synthesized (that
drives the timing); the subtitle track is translated separately against the same
timing, so the two languages stay in lock-step. The filename makes both explicit:

```bash
# English audio (Kokoro) + Russian subtitles (ollama)
democreate localize demo.json --audio-lang en --subtitle-lang ru --model lfm2.5
# → output/video/<stem>-audio_en-subs_ru.mp4  + a Russian .srt/.vtt sidecar

# a batch of language combinations in one run
democreate localize demo.json --pairs "en:ru,ru:en,en:es" --model lfm2.5
```

The library-level default translator is a deterministic no-op, so the path is
import-safe and offline-testable; the `localize` command itself defaults to
`--translator ollama` and exits with an actionable error when no server is
reachable (pass `--translator identity` to render without translation).
Subtitles work for any language (text only); *audio* in a language needs a
TTS voice for it — Kokoro's languages or an installed system voice (so Russian
*audio* needs a Russian voice present). See [`docs/cli.md`](docs/cli.md).

**Five localized cuts** demonstrate it on the showcase itself (rendered on demand
into `output/video/`, each with a matching `audio_X-subs_Y.srt`/`.vtt` under
`output/captions/`; both are gitignored, so regenerate them with the commands
above): `…-audio_en-subs_en.mp4` (baseline), `…-audio_en-subs_ru.mp4`
(English audio, Russian subtitles), `…-audio_en-subs_es.mp4` (English audio,
Spanish subtitles), `…-audio_es-subs_en.mp4` (**Spanish audio**, English subtitles
— the reverse), and `…-audio_ru-subs_ru.mp4` (**Russian audio + Russian subtitles**,
spoken by a system Russian voice since Kokoro has no Russian).

## Demo a research paper (PDF + codebase)

Point `democreate paper` at a PDF and (optionally) its codebase to get a narrated
overview — the title and abstract, the paper's figures and rendered pages, and an
architecture diagram of the code:

```bash
democreate paper paper.pdf --repo ./src --figures ./figures --theme paper -o output
```

The narration is built from the paper's **real content**: a correct abstract
(the extractor skips the table of contents), the **actual figure captions**
(`Figure N: …` parsed from the text), and the paper's **section structure**. PDF
ingestion uses the **poppler** command-line tools (`pdfinfo`/`pdftotext`/
`pdftoppm`) with **no pip dependency**. Worked example — the 170-page
*Policy Entanglement in Active Inference* paper (47 figures, 145-module
codebase) renders to a verified 1080p video narrating its real abstract,
figure captions, and 6 sections.
Details: [`docs/paper.md`](docs/paper.md).

## Architecture

A `Demo` (the declarative spine) threads through eight subsystems. The deterministic
defaults carry the core pipeline; system binaries and guarded adapter slots
upgrade specific media surfaces without changing the orchestration.

```mermaid
flowchart TB
    Demo["Demo (declarative spine)<br/>scenes · chunks · actions"]
    TTS["narration.tts<br/>synthesize → AudioClips"]
    Sync["narration.sync<br/>transcribe → WordTimestamps<br/>anchor actions to trigger_words"]
    Timeline["assembly.compositor<br/>build_timeline (fps, wpm)"]
    Compositor["assembly.compositor<br/>compose → frames + manifest"]
    Captions["assembly.captions<br/>SRT / VTT"]
    Export["export<br/>HTML player · transcript · demo.json · chapters"]
    Video["export.video + render_video<br/>concat voiceover · ffmpeg HD MP4"]
    Verify["export.verify<br/>assert real streams · not silent · not black"]

    Demo --> TTS
    TTS --> Sync
    Sync --> Timeline
    Timeline --> Compositor
    Compositor --> Captions
    Captions --> Export
    Compositor --> Video
    TTS --> Video
    Video --> Verify
```

The spine (`schema.py`, `media.py`, `errors.py`, `project_paths.py`) is pure
Python with no I/O or heavy deps; `pipeline.py` and `cli.py` are thin
orchestrators. Details: [`docs/architecture.md`](docs/architecture.md).

## Subsystems

Each subsystem directory under `src/democreate/` carries its own `README.md`
(what it does) and `AGENTS.md` (rules for changing it).

| Subsystem | Owns | Deterministic default | Upgrade extra |
|-----------|------|-----------------------|---------------|
| `capture/` | Frame rendering; terminal/browser/input recording. | `SyntheticRenderer`, asciinema model, `NullBrowserDriver`, pure event log. | `capture`, `browser`, `replay` |
| `narration/` | Script generation, TTS, measured-duration word estimates. | `TemplateScriptGenerator`, `SilentTTSBackend`, `HeuristicTranscriber`. `SystemTTSBackend` adds OS voice when available. | `tts`, `whisper` |
| `animation/` | Syntax-highlight frames, cursor-zoom math, manim specs. | `rich` highlighting, pure zoom math, JSON manim spec. | `animation` |
| `codebase/` | AST traversal, visualization, import graphs. | stdlib `ast`. | `codebase` |
| `assembly/` | Timeline, compositing, captions, effects. | `ManifestCompositor`, pure SRT/VTT/ASS, Pillow effects. | `video` |
| `export/` | Spine + frames + audio → deliverables. | Jinja2 HTML player, Pillow GIF, Markdown/JSON/chapters, pure WAV concat. Real HD MP4 assembly + content verifier when `ffmpeg` is present. | `video` |
| `paper/` | Research-paper ingestion (PDF + figures → demo). | poppler CLI (`pdfinfo`/`pdftotext`/`pdftoppm`), `build_paper_demo`. | — (poppler on `PATH`) |
| `translation/` | Localize: audio in one language, subtitles in another. | `IdentityTranslator` (no-op). `OllamaTranslator` adds local translation (a running `ollama` server, no pip dep). | — (local `ollama`) |

Spine modules: `schema.py` (the model), `media.py` (`AudioClip` / `FrameState`),
`config.py` (`Theme` / `AudioConfig` / `VideoConfig` / `RenderConfig`),
`pipeline.py` (orchestrator), `cli.py` (the `democreate` command). The renderer
(`capture/screen.py`) uses scaled TrueType fonts + **pygments** highlighting +
themes; the animator (`assembly/animator.py`) adds the moving waveform, scene
transitions, and Ken Burns.

## Testing

No mocking framework (no `unittest.mock`/`MagicMock`), fully deterministic, real
temp files, ≥90% coverage on the pure core (enforced via `fail_under = 90`).
`monkeypatch` is used only to simulate an absent optional binary or force the
core-only fallback path — never to fake a deterministic backend's output (see
[`docs/testing_philosophy.md`](docs/testing_philosophy.md)). Heavy backends carry a `backend` pytest marker
and skip when absent; the default path asserts the `BackendUnavailableError`
contract instead.

```bash
.venv/bin/python -m pytest -q        # full suite
.venv/bin/python -m pytest --cov     # the ≥90% gate
ruff check . && mypy src             # lint + types
```

Details: [`docs/testing_philosophy.md`](docs/testing_philosophy.md).

## Extras

Each extra upgrades one subsystem from its deterministic default to a real
backend. Install only what you need.

| Extra | Upgrades | Dependencies | Install |
|-------|----------|--------------|---------|
| `tts` | Real narration | `kokoro-onnx`, `soundfile`, `numpy` | `uv pip install -e ".[tts]"` |
| `elevenlabs` | Cloud narration (ElevenLabs API key) | `elevenlabs` | `uv pip install -e ".[elevenlabs]"` |
| `whisper` | Unimplemented transcription slot; installing it does not enable recognition | `openai-whisper` | `uv pip install -e ".[whisper]"` |
| `capture` | Real screen capture | `mss`, `numpy` | `uv pip install -e ".[capture]"` |
| `browser` | Website driving | `playwright` | `uv pip install -e ".[browser]"` |
| `animation` | Code animations | `manim` | `uv pip install -e ".[animation]"` |
| `replay` | Input record/replay | `pynput`, `pyautogui` | `uv pip install -e ".[replay]"` |
| `video` | Video assembly helpers (real MP4 still needs `ffmpeg` on `PATH`) | `moviepy`, `ffmpeg-python` | `uv pip install -e ".[video]"` |
| `codebase` | Multi-language analysis | `tree-sitter`, `tree-sitter-languages` | `uv pip install -e ".[codebase]"` |
| `docs` | PDF export of the demo transcript | `weasyprint` | `uv pip install -e ".[docs]"` |
| `all` | Everything | (all of the above) | `uv pip install -e ".[all]"` |
| `dev` | Test + lint toolchain | `pytest`, `pytest-cov`, `ruff`, `mypy` | `uv pip install -e ".[dev]"` |

Check what is active with `democreate backends`. Full table:
[`docs/backends.md`](docs/backends.md).

## Prior art

Relevant prior art includes [CodeVideo](https://docs.codevideo.io/overview/),
[asciinema](https://asciinema.org/), termtosvg,
[code-video-generator](https://code-video-generator.readthedocs.io/en/latest/),
[Code2Video](https://arxiv.org/abs/2510.01174) and
[Paper2Video](https://arxiv.org/abs/2510.05096). The manuscript distinguishes
documented construction models from unmeasured comparative outcomes.

## Citation

Cite via the **concept DOI** (always resolves to the latest archived release):
[`10.5281/zenodo.20693216`](https://doi.org/10.5281/zenodo.20693216). The
concept DOI currently resolves to archived `0.6.2` (2026-06-04). Candidate
`0.8.0` has no asserted version-specific archive DOI or publication date.

```bibtex
@software{democreate,
  author  = {Friedman, Daniel Ari},
  title   = {DemoCreate: Declarative, Deterministic Audio-Visual Demo Generation},
  year    = {2026},
  url     = {https://github.com/docxology/democreate},
  version = {0.8.0},
  doi     = {10.5281/zenodo.20693216},
  license = {MIT}
}
```

## License

MIT — see [`LICENSE`](LICENSE).
