# Changelog

All notable changes to DemoCreate are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/). The **concept DOI**
[`10.5281/zenodo.20693216`](https://doi.org/10.5281/zenodo.20693216) always
resolves to the latest archived release.

## [Unreleased]

### Added
- **`.humos/` sidecar contract** — DemoCreate now carries a HumOS sidecar
  (`sidecar.toml`, `bridges.toml`, `conformance.toml`) declaring standalone
  coupling and a `data` bridge to `hum-dashboard` for versioned demo video
  integration.

### Fixed

- **`AudioConfig.rate_wpm` is now wired** — `get_tts_backend` gained a
  `rate_wpm` keyword, threaded from the render config in `render`, `tour`,
  `portfolio`, `paper`, and `localize`, so the documented speaking-rate
  override actually reaches `SystemTTSBackend` (`say -r` / `espeak -s`).
  Previously the knob existed only in the config and was silently ignored.
- **`export_video` now builds a real image2 pattern** — the printf glob and
  `-start_number` are derived from the first frame's zero-padded stem
  (matching `encode_frame_sequence`) instead of a hardcoded `%05d` that
  matched nothing for the compositor's `frame_%04d.png` names.
  `build_ffmpeg_command` accepts an optional `start_number`.
- **`compute_zoom_path` lead-in eases in** — the zoomed-out lead-in keyframe
  now sits `hold_ms` before the first cursor event (clamped at 0) instead of
  sharing its timestamp, which made the camera jump fully zoomed-in one frame
  after appearing zoomed-out.
- **`background_image` relativizes** — `_PATH_KEYS` includes the key, so the
  resolved demo JSON and the render manifest rewrite full-frame
  background-image paths relative to the workspace root like every other path
  field.
- `Demo.filter_scenes(ids=[])` / `(kinds=[])` select nothing (previously an
  empty list was treated as "no filter", returning every scene).
- `democreate portfolio` validates the projects directory up front (a clean
  error instead of a raw `FileNotFoundError`) and exits non-zero when zero
  projects render.
- `ChatterboxTTSBackend.synthesize` / `WhisperTranscriber.transcribe` raise
  `NotImplementedError` when their dependency is installed (the repo's
  unwired-slot convention) instead of an unconditional
  `BackendUnavailableError`.
- `democreate backends` lists the `elevenlabs` extra; the `paper --theme`
  help includes `noir`; `config` / `thumbnail` / `gif` default to the
  package theme `noir` (previously `dark`).
- The `narration` package re-exports `ElevenLabsTTSBackend`
  (`from democreate.narration import ElevenLabsTTSBackend`).
- Removed dead code: a stray duplicate `@app.command()` that
  double-registered `paper`, an unused `RenderConfig` re-export in
  `democreate.portfolio`, the no-op `"·"` math-fold entry, a dead
  `length < 0` check in `stego.extract` (the header is unsigned),
  `AudioClip.to_dict` (no `from_dict` counterpart; its sole caller was its
  own test), and a click-ripple "fade" alpha that Pillow silently drops on
  RGB frames.
- Animation `diagram` / `waveform` import PIL lazily per the subsystem
  contract; overlay / chapters / interactive / paper-script docstrings now
  match measured behavior.
- Docs drift: `docs/translation.md` documents `IdentityTranslator` (the
  documented `NoopTranslator` never existed), real `translate` signatures,
  the `localize` CLI flags instead of a nonexistent `translation:` YAML
  block, and sidecar subtitles (burn-in is `--burn`); `docs/cli.md` `--tts`
  choices include `elevenlabs` and `--max-modules` defaults to `6`;
  `docs/backends.md` gains the ElevenLabs row; `docs/README.md` states
  Kokoro is wired and points the paper demo at `output/paper_showcase/`;
  `docs/videos.md` chapter count corrected to 15; `examples/README.md`
  intro description matches the nine-scene artifact.

- **`Demo.from_dict` refuses foreign `schema_version`** — loading an artifact
  stamped with any other version used to succeed silently while unknown future
  fields were dropped; it now raises `SchemaValidationError` naming both
  versions. The current `SCHEMA_VERSION` (`"1.0"`) round-trips unchanged.
- **`AsciicastRecording.from_json` raises `CaptureError`** on empty,
  malformed-header, or malformed-event recordings (previously a raw
  `ValueError`/`JSONDecodeError`), wiring the exported-but-never-raised
  `CaptureError` into a real terminal-capture failure path.
- **LLM narration errors no longer point at a phantom extra** — `LLMNarrator` /
  `LLMScriptGenerator` raised `BackendUnavailableError(..., extra="llm")`, but no
  `llm` extra exists (the module is stdlib-only). The module is now documented as
  a deliberate library-only surface: the CLI never calls an LLM, because polished
  narration can drop a chunk's `trigger_word` and degrade TTS→STT anchoring.
- **`docs/manuscript/figures/graphical_abstract.py` runs again** — the
  `manuscript/` → `docs/manuscript/` migration left its repo-root anchor one
  level short (it resolved `docs/docs/_videoframes`), so the cover was not
  regenerable; the committed cover and the showcase stat-card still are
  re-rendered at the current test count (753).


### Changed

- **`scripts/` enforces the thin-orchestrator contract** — the two scripts that
  carried business logic now delegate to importable, tested library modules:
  `scripts/build_manuscript.py` → `democreate.manuscript.build_manuscript`
  (config load, citation/figure gates, Pandoc invocation, engine discovery) and
  `scripts/generate_api_docs.py` → `democreate.api_docs.generate` (module
  inventory + Markdown rendering; deterministic output unchanged). Pure code
  motion, behavior preserved; both modules are covered by the new
  `tests/test_manuscript.py` / `tests/test_api_docs.py` (test-count literals
  synced to the new collection total). `scripts/README.md` / `scripts/AGENTS.md`
  carry the refreshed inventory (script | purpose | delegates to | command).

### Removed

- **The `pdf` extra (`pymupdf`)** — declared since 0.7.1 and advertised in the
  README extras table, but no code path ever imported pymupdf: the `paper/`
  subsystem deliberately reads PDFs through the poppler CLI only. The extra and
  all of its references are gone; missing poppler now raises
  `BackendUnavailableError("poppler")` with the OS-package remedy documented,
  instead of a `uv sync --extra pdf` hint that pointed at nothing.

## [0.7.1] - 2026-07-20

### Added
- **`Demo.merge`** — compose a demo from multiple fragments. Scene/chunk ID
  collisions are auto-resolved with unique suffixes, and metadata is
  shallow-merged. Enables assembling a demo from separate declarative files.
- **`Demo.filter_scenes`** — extract a sub-demo by scene IDs, kinds, and/or
  slice range. Supports partial renders ("only the code scenes", "scenes 3-7").
- **`Demo.to_file` / `Demo.from_file`** — one-liner I/O. Format (JSON/YAML) is
  inferred from the file extension, replacing manual `path.write_text(...)`.
- **`Demo.scene_by_id` / `Demo.chunk_by_id`** — O(n) lookup helpers replacing
  manual iteration in every caller.
- **`Demo.__repr__`** — compact, introspectable representation for debugging:
  `Demo(title='Tour', scenes=15, chunks=15, actions=11, 3840x2160@30fps)`.
- **`Demo.validate` now checks action params** — `OPEN_FILE` must have `path`,
  `CREATE_FILE` must have `code`, etc. `WAIT` and `SPEAK` are exempt.
- **`generate_codebase_demo` `max_scenes` parameter** — bounds the number of
  module scenes generated from a large repo (default 0 = all).
- **`to_markdown` `format` parameter** — three output shapes: `"full"`
  (default, readable transcript with action bullets), `"compact"` (one line
  per scene), and `"outline"` (nested bullet outline).
- **`Pipeline.dry_run`** — validate a demo without running TTS, sync, or
  rendering. Returns the problem list (or raises in strict mode). No files
  are created.
- **`export_pdf` styled HTML** — the PDF transcript is now a proper typeset
  document with headings, paragraphs, and inline code formatting, not a
  `<pre>` text dump.
- **`democreate inspect --json`** — machine-readable JSON output for the
  `inspect` command (scenes, chunks, actions, estimated duration, validity,
  problems), consistent with every other CLI command's `--json` flag.
- **`docs` optional extra** (`weasyprint>=62.0`) — `export_pdf` in
  `democreate.export.formats` now has a matching pyproject extra, so
  `BackendUnavailableError("pdf", extra="docs")` points at a real install
  target. `uv sync --extra docs` installs WeasyPrint for PDF transcript export.
- **`absolute_word_timestamps` silence-model parity** — the function now
  accepts `lead_ms` and `gap_ms` keyword arguments (defaulting to 0) so
  word-level caption timestamps mirror `sync_demo`'s assembled-voiceover
  timeline. Previously it ignored lead/gap silence, causing word-level
  captions to drift ahead of the spoken audio by `lead_ms` at the start and a
  further `gap_ms` per chunk.
- `democreate backends` now lists the WeasyPrint PDF-export capability.

### Fixed
- `export_pdf` raised `BackendUnavailableError("pdf", extra="docs")` but no
  `docs` extra existed in `pyproject.toml` — the install hint pointed at a
  phantom extra. The `docs` extra is now declared.
- `absolute_word_timestamps` did not account for `lead_ms`/`gap_ms` in the
  cumulative timeline, so its flat word stream drifted from the real audio
  timeline and from `sync_demo`'s action timestamps.
- `SyntheticRenderer._highlight`'s nested `color_for` returned an untyped
  bare `tuple`; now `tuple[int, int, int]` for stricter mypy checking.
- ElevenLabsTTSBackend.synthesize forwarded the schema's cross-backend
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
