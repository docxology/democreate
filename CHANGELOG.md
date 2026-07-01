# Changelog

All notable changes to DemoCreate are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/). The **concept DOI**
[`10.5281/zenodo.20693216`](https://doi.org/10.5281/zenodo.20693216) always
resolves to the latest archived release.

## [Unreleased]

### Added
- **ElevenLabs cloud TTS backend** (`democreate.narration.tts.ElevenLabsTTSBackend`,
  the `elevenlabs` extra, `--tts elevenlabs`): a wired highest-fidelity hosted voice
  that transcodes to the pipeline's canonical 16-bit mono PCM WAV; requires the
  `elevenlabs` package and an `ELEVENLABS_API_KEY` and fails with a clear, typed
  error (never a silent WAV) when either is missing.

### Fixed
- `ElevenLabsTTSBackend.synthesize` forwarded the schema's cross-backend
  `voice="default"` sentinel straight to the ElevenLabs API as a literal
  voice_id, 404ing (`voice_not_found`) on any real `democreate render`/`tour
  --render` call with `--tts elevenlabs`. Now resolved to `self.voice_id`
  like every other unset-voice case, matching how System/Kokoro/Silent
  already treat the sentinel.

## [0.7.0] - 2026-06-25

### Added
- **Localized videos — audio and subtitles in different languages** (new
  `democreate.translation` subsystem + `democreate localize`): translate narration
  with a local, configurable `ollama` server (deterministic no-op default) so a
  render carries audio in one language and subtitles in another (e.g. English audio
  + Russian subtitles), in lock-step, with the languages encoded in the filename.
  Single pair or a `--pairs` batch.
- **Project-summary generator** (`democreate.narration.project_summary.generate_project_summary_demo`):
  a deterministic, README + AST-driven generator that *describes* a codebase via
  a fixed seven-beat arc — title card → what-it-is bullets (from the real README)
  → architecture diagram (real packages) → by-the-numbers stat card → two or
  three load-bearing modules shown as real source narrated from their **real
  docstrings** → how-to-run terminal → outro. Selection + extraction, not
  enumeration; no model, no network, byte-deterministic.
- **`democreate portfolio DIR`** — batch-render a timestamped, content-verified
  summary video for every project under a directory: one `output/<name>/`
  subfolder each (`<name>-summary-<UTC>.mp4`), a `portfolio_index.json` +
  `portfolio_index.html` gallery, and per-project failure isolation (one bad repo
  never aborts the batch). New orchestration module `democreate.portfolio`.
- **`democreate tour REPO --render`** — render a single codebase tour straight to
  a verified MP4 (previously `tour` only built the HTML player).
- **Wired Kokoro neural TTS** (`KokoroTTSBackend`) — a high-quality, fully-local
  voice via `kokoro-onnx` (previously a no-op adapter slot). Model-file
  resolution via `KOKORO_MODEL_PATH` / `KOKORO_VOICES_PATH` or
  `~/.cache/democreate/kokoro`, with graceful fallback when a demo carries an
  unknown (system) voice name.
- **`democreate fetch-voice`** — one-step download of the Kokoro model files
  (~340 MB) into the cache.
- `scripts/generate_portfolio.py` thin orchestrator.
- Richer project summaries: a **"built with" beat** (top external runtime
  dependencies, excluding stdlib / intra-repo / dev-test tooling), a **test count**
  in the stat card when discoverable, a representative (largest-symbol) code
  excerpt, and better module selection (public-over-private, deduped by name).
- **Longer, denser project summaries (~3–5 min):** a **per-package tour** (one
  slide per substantial area — date/`__init__`/test-only dirs filtered out), module
  narration now drawn from the docstring's first two sentences plus the module's
  real named classes/functions and counts, and up to **6 key modules** by default.
- The test suite mirrors `src/democreate/` (one `tests/<subsystem>/` per package);
  pytest runs with `--import-mode=importlib`.

### Repo / CI
- The repository tracks exactly one self-describing output bundle — the showcase —
  enforced by `tests/test_output_public_allowlist.py`; research-paper demos and
  per-project renders stay gitignored/regeneratable.
- GitHub Actions CI (`.github/workflows/ci.yml`): ruff + mypy + the full
  coverage-gated suite on every push/PR.

### Fixed
- `KokoroTTSBackend` now handles arbitrarily long / phoneme-dense narration: text
  is split into sub-limit segments and a segment that still overflows Kokoro's
  ~510-token cap is recursively halved and concatenated (was a hard
  `index 510 out of bounds` crash on a dense docstring).
- Project-summary narration skips symbol-dense docstrings (bitmask/formula tables,
  arrow lists) that read as gibberish aloud, falling back to the clean first
  sentence plus the factual class/function summary.
- `KokoroTTSBackend` availability check probed the wrong module name (`kokoro`
  instead of the `kokoro_onnx` the `tts` extra installs); synthesis was a no-op
  raise even when installed.
- README extraction skips badge/image rows and strips inline markdown so
  generated taglines read as real prose.

### Changed
- mypy skips following the heavy optional libs (`numpy` / `soundfile` /
  `kokoro_onnx`) so their 3.12+ stubs don't break the 3.10-targeted check.
- Docs (README, `docs/backends.md`, `docs/cli.md`, `docs/audio.md`,
  `narration/README.md`) updated for the wired neural voice and the new
  `portfolio` / `tour --render` / `fetch-voice` surfaces.

## [0.6.2] - 2026-06-04

- Archived release on Zenodo. See the manuscript and git history for the 0.6.2
  feature set (declarative spine, deterministic backends, system-voice render,
  4K animated video + content verification, research-paper demos, provenance).
