# Changelog

All notable changes to DemoCreate are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/). The **concept DOI**
[`10.5281/zenodo.20693216`](https://doi.org/10.5281/zenodo.20693216) always
resolves to the latest archived release.

## [0.7.0] - 2026-06-25

### Added
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

### Fixed
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
