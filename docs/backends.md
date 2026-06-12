# Backends and extras

Every heavy capability in DemoCreate sits behind an abstract interface with a
**pure-Python deterministic default**. The package produces a real, inspectable
demo end-to-end with only the light core dependencies installed. Optional extras
and system binaries upgrade individual subsystems without changing the pipeline
or the schema; neural TTS, Whisper, and Manim currently exist as guarded adapter
slots rather than fully wired render paths.

## Core dependencies (always installed)

`pyyaml`, `typer`, `rich`, `jinja2`, `pillow`. These are enough for the entire
default path: silent-but-correctly-timed narration, synthetic frames, a render
manifest, captions, and the interactive HTML player.

## Subsystem → default → upgrade

| Subsystem | Capability | Deterministic default | Real backend | Extra | Dependency | Install |
|-----------|-----------|-----------------------|--------------|-------|------------|---------|
| `narration/` | Text-to-speech | `SilentTTSBackend` (silent clips sized to narration) | **`SystemTTSBackend`** (smoke-tested OS voice, zero pip); `KokoroTTSBackend` / `ChatterboxTTSBackend` are guarded adapter slots | `tts` | usable `say`/`espeak` plus `ffmpeg` or `afconvert` for transcode (OS, no pip); `kokoro-onnx`, `soundfile`, `numpy` | usable OS voice, or `uv pip install -e ".[tts]"` |
| `narration/` | Transcription (TTS→STT) | `HeuristicTranscriber` (even word spacing) | `WhisperTranscriber` adapter slot | `whisper` | `openai-whisper` | `uv pip install -e ".[whisper]"` |
| `narration/` | Narration text | **template generator** (deterministic, default) | `LLMNarrator` (OpenAI-compatible, **stdlib `urllib`, zero pip**) | — | OpenAI-compatible API + `OPENAI_API_KEY` | env var only (no install) |
| `capture/` | Screen pixels | `SyntheticRenderer` (scaled TrueType fonts + pygments + themes) | `MssScreenCapture` | `capture` | `mss`, `numpy` | `uv pip install -e ".[capture]"` |
| `capture/` | Website driving | `NullBrowserDriver` (records calls, synthetic screenshots) | `PlaywrightBrowserDriver` | `browser` | `playwright` | `uv pip install -e ".[browser]"` |
| `capture/` | Input record/replay | pure event model (`EventLog`) | `record_session` / `replay_session` | `replay` | `pynput`, `pyautogui` | `uv pip install -e ".[replay]"` |
| `animation/` | Waveform / diagrams / animation | `waveform.py`, `diagram.py`, scaled fonts, JSON manim spec | `render_manim_scene` adapter slot | `animation` | `manim` | `uv pip install -e ".[animation]"` |
| `codebase/` | Code analysis | stdlib `ast` walker | tree-sitter multi-language | `codebase` | `tree-sitter`, `tree-sitter-languages` | `uv pip install -e ".[codebase]"` |
| `assembly/` | Audio assembly + animation | `audio.py` (stdlib `wave` concat), `animator.py` (timed frames) | `normalize_audio` / `apply_fade` via **`ffmpeg`** | `video` | `ffmpeg` on `PATH` (no pip needed) | OS binary |
| `export/` | Video encode + verify | ffmpeg-argv/concat builders + Jinja2 HTML player | `assemble_video` / `encode_frame_sequence` (real HD MP4) + `verify_video` (content assertions) via **`ffmpeg`/`ffprobe`** | `video` | `ffmpeg`/`ffprobe` on `PATH` (no pip needed); Python helpers in the `video` extra | OS binary, plus `uv pip install -e ".[video]"` if using helper libraries |
| `paper/` | Read research-paper PDF | — | **poppler CLI** (`pdfinfo` / `pdftotext` / `pdftoppm`, zero pip) | `pdf` | poppler binaries on `PATH` | OS binary (`brew install poppler` / `apt-get install poppler-utils`) |

Install everything at once with the aggregate extra:

```bash
uv pip install -e ".[all]"
```

## How the fallback works

- Availability is detected at call time with `importlib.util.find_spec("name")`,
  never by importing the heavy dependency at module top level. The package and all
  public modules import cleanly on core deps alone.
- Asking for a guarded backend whose dependency is absent raises
  `BackendUnavailableError(backend, extra=...)`. The message includes the exact
  remedy, e.g. `backend 'kokoro' is unavailable — install it with
  \`uv sync --extra tts\``.
- Real-backend adapters carry `# pragma: no cover` so they never dilute the
  ≥90% coverage gate on the pure core.

## Inspecting backend state

```bash
democreate backends
```

The system TTS row reports `available` only after a short synthesis/transcode
smoke test, so a host that exposes `say` or `espeak` but emits empty audio is
treated as absent.

prints a table of each capability with status `installed` (extra present) or
`default` (deterministic fallback in use) plus the `uv sync --extra <extra>`
command to upgrade it. The CLI also reminds you: *all capabilities have a working
deterministic default backend.*

## Zero-pip real backends (system binaries)

The highest-value upgrades need **no `pip`/`uv` install at all** — only usable OS
binaries:

- **Real voiceover** — `SystemTTSBackend` uses macOS `say` or Linux
  `espeak`/`espeak-ng`, then transcodes to canonical WAV via `ffmpeg` or
  `afconvert`. Selected with `democreate render --tts system --voice <name>`.
  This is a *platform* backend (not portable), so it is never the `auto` default,
  but it turns the silent default into genuine spoken narration for free. See
  [audio.md](audio.md).
- **Real HD video + verification** — `democreate render` / `paper` / `verify`
  shell out to `ffmpeg`/`ffprobe`. The animator holds each frame for its
  *measured* narration duration (audio is ground truth) and overlays the waveform,
  the top-edge progress line, transitions, and the typing/cursor animation (Ken
  Burns is available but off by default); `encode_frame_sequence` encodes it;
  `verify_video` asserts the result is a real, non-silent, non-black video of the
  expected size. ffmpeg also powers audio `loudnorm` + fades. See [video.md](video.md)
  and [audio.md](audio.md).
- **Research-paper PDF reading** — the `paper/` subsystem shells out to the
  poppler utilities `pdfinfo` / `pdftotext` / `pdftoppm` to read metadata, extract
  text, and rasterize pages — **no pip PDF dependency**. Missing poppler raises
  `BackendUnavailableError(backend="poppler", extra="pdf")`. See [paper.md](paper.md).

`democreate backends` shows the TTS and ffmpeg rows as `available` / `absent`
based on the smoke-tested synthesis/transcode path and the OS binaries.

## Optional LLM narration

The deterministic template generator (`narration/script.py`) is **always the
default** and is never changed by the LLM module. When an OpenAI-compatible API is
configured via environment variables, `LLMNarrator` (`narration/llm.py`) can
generate richer narration or polish the template's output through a
`/chat/completions` endpoint. It is **import-safe and dependency-free** — it uses
only the standard library `urllib`, so there is **no pip extra** — and its
network-touching methods are guarded: they raise `BackendUnavailableError` when no
key is configured, so an unconfigured environment simply uses the template.

Environment variables consulted:

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` / `DEMOCREATE_LLM_API_KEY` | Bearer key (presence = enabled) | unset → template used |
| `DEMOCREATE_LLM_BASE_URL` | API base URL | `https://api.openai.com/v1` |

The pure `build_chat_payload()` helper builds the request body and is fully
testable without any network access. See the [recipes](recipes.md#optional-llm-narration-env-gated).

## Chapters, metadata, and poster/GIF exports

Several presentation- and provenance-layer exports ship in the core (Pillow +
ffmpeg only, no extras):

- **Chapters** (`export/chapters.py`). Every `render`/`paper` writes a YouTube
  chapter file (`M:SS Title` per scene, first line forced to `0:00`) and embeds
  chapter markers into the MP4 via an ffmpeg `FFMETADATA1` document (one
  `[CHAPTER]` per scene). The embed is a guarded best-effort step; verify with
  `ffprobe -show_chapters`.
- **Container metadata tags** (`export/metadata.py`). ffmpeg also carries
  standard container tags: `build_tags()` is a pure `dict[str, str]` of
  `title`/`artist`/`comment`/`date`, and `embed_tags()` muxes them into the MP4 by
  **stream-copy** (`-codec copy`, no re-encode). Read them with
  `ffprobe -show_entries format_tags=…`. See [provenance.md](provenance.md).
- **On-screen overlay bars** (`export/overlay.py`) and **steganography**
  (`export/stego.py`) are **pure Pillow** — no ffmpeg, no extras. The overlay
  draws the header/footer provenance bars per frame (burned into the pixels, so
  they survive the encode); the stego module LSB-embeds a signed provenance
  payload into lossless poster/bookend PNGs (which an H.264 re-encode would
  destroy — hence PNG, not the video pixels). See [provenance.md](provenance.md).
- **Poster + GIF** (`export/poster.py`). `render_poster()` paints a designed
  title still (`democreate thumbnail`); `demo_to_gif()` evenly down-samples a
  frame sequence into an animated GIF preview (`democreate gif`). Both are pure,
  deterministic, and import no optional dependencies at module top level.

## Notes on heavy extras

- **`video` needs `ffmpeg` on `PATH`** in addition to (or instead of) the Python
  packages — the argv is built purely, but actually encoding shells out. See
  [troubleshooting.md](troubleshooting.md).
- **`browser`** requires a one-time `playwright install` of browser binaries
  after the pip extra.
- **`whisper`** pulls in `torch` transitively and is the heaviest extra; the
  `HeuristicTranscriber` default keeps the sync mechanism fully exercised without
  it.
