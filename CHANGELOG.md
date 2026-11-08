# Changelog

All notable changes to DemoCreate are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and the project adheres to
[Semantic Versioning](https://semver.org/). The **concept DOI**
[`10.5281/zenodo.20693216`](https://doi.org/10.5281/zenodo.20693216) always
resolves to the latest archived release.

## [Unreleased]

Candidate **0.8.0** — pending publication.

The pre-existing blocking ≤120 ms acoustic-sync criterion remains pending/unmet;
no annotated corpus/oracle or passing research receipt is available. Candidate
release/manuscript readiness is not established.

No release date or new version archive DOI is asserted. The concept DOI currently
resolves to archived 0.6.2, not this candidate.

### Compatibility

- Schema 1.1 intentionally rejects schema 1.0 (no shim). Optional measured
  chunk duration drives playback after sync; narration WAVs use numbered
  `chunk_NNNN.wav` names rather than chunk-ID filenames.
  Action timing origin is persisted: authored absolute times survive re-sync,
  while derived times refresh after narration edits. WAIT and recorded discrete
  inputs retain their timing through the complete pipeline.
- Python floor is 3.11.5 and Pillow floor is 13. Host font discovery APIs are
  removed; rendering uses Pillow’s bundled font. The unused `pdf` extra is
  removed; PDF ingestion needs poppler OS binaries.
  String enums now use Python 3.11 `StrEnum`; `str(member)` yields its on-disk
  value rather than the former qualified enum name.
- Example backgrounds are relative to the Demo file directory and staged into
  the selected workspace; only the chosen asset root/generated assets may be read.
  CLI `--asset-root` supports replaying a resolved bundle without widening
  authority implicitly. Generated backgrounds are atomically staged.
- `Pipeline.run` / `build_demo` now leave authored input unchanged; callers read
  resolved audio/timing/assets from `PipelineResult.demo`. This permits reuse in
  another workspace without leaking authority to the first workspace.
- Explicit compositor rasters survive animation instead of being discarded.
  Only default composition uses scheduled synthetic frame regeneration.
- Config loaders reject unknown fields. Removed high-level
  `video.typing_fraction`; author `Action.duration_ms` instead. The direct,
  snapshot-only animator API retains its separate fraction control.
- Unsupported acoustic-onset/authentication claims corrected. Corpus/120 ms
  hypotheses remain planned; historical figures/results are not current receipts.
- Figure generation uses committed local paper input and root-relative outputs.
  Portfolio script now rejects invalid directories and zero-success batches;
  benchmark output records raw wall-clock samples and source/input/runtime identity.
- Prose/test-count/default-copy consistency tests removed in favor of structured
  ledger/evidence-reference validation. No current suite count is embedded in
  generated stat cards.


### Changed

- Rebuilt the graphical abstract and explanatory figures with bounded layout,
  larger cover labels, complete source panels and explicit synthetic/observed
  evidence classes. Gallery examples use real public APIs and no invented paper
  identity; manuscript titles state mechanisms, responsibilities and limitations.
- Modularized workflow/reference/evidence guidance; retained immutable historical
  receipts and added `docs/visual-refresh.md` with current native package/media
  provenance. A new Kokoro `af_heart` 2160p run reproduced the identified MP4 bytes;
  this is not acoustic validation or a general neural-determinism guarantee.
- Public API reference now inventories 49 modules, includes classmethod factories
  and uses working CommonMark navigation. CI checks local file/fragment links,
  real localized MP4 output, full manuscript rendering and generated-file freshness.

- **CI currency** — `actions/checkout@v7`, `actions/setup-python@v7`,
  `astral-sh/setup-uv@v10`, and the test matrix now covers Python 3.11–3.15.
- **Legacy WAV compatibility** — normalization and fades retain PCM sample rate
  and channel count and write standard 16-bit PCM headers. This avoids FFmpeg's
  implicit 192 kHz/WAVE_FORMAT_EXTENSIBLE output, which broke Python 3.11 renders.
  Processing uses bounded-memory PCM copying and atomically publishes the WAV.
- CI installs a SHA-256-checked, matched Pandoc 3.13/pandoc-crossref 0.3.26a pair,
  so manuscript figure/citation checks execute instead of silently skipping.
- Malformed WAV reads in normalization/fades now raise `RenderError` while
  preserving source and prior output. An absent `ffprobe` leaves an explicit
  partial benchmark report instead of discarding completed observations.
- Docs drift: the README subsystem table no longer claims a `pdf` extra for
  `paper/` (poppler on `PATH`, no pip extra — as `docs/backends.md` already
  said), the localized showcase cuts are described as rendered-on-demand rather
  than committed (`output/` is gitignored), `docs/translation.md` is linked from
  the docs hub again, and `docs/README.md` carries the re-verified collected-test
  gate description rather than a current collection count.

### Added
- **`.humos/` sidecar contract** — DemoCreate now carries a HumOS sidecar
  (`sidecar.toml`, `bridges.toml`, `conformance.toml`) declaring standalone
  coupling and a `data` bridge to `hum-dashboard` for versioned demo video
  integration.

### Fixed
- Localized SRT/VTT use measured, padded `PipelineResult.demo` timings, not stale
  authored windows. Same-language caption generation copies borrowed input before
  synchronization; caller-owned authored/timing artifacts remain unchanged.
- Synthetic typing renders one active caret across row boundaries and saturated
  character counts. Pixel-level regressions cover zero, boundary and partial states.
- Manuscript output paths resolve against caller CWD before Pandoc changes directory;
  long shell recipes are split at real continuations instead of clipping at page trim.
- `LocalizedResult` documentation distinguishes render success from requested
  verification and retains produced paths when subsequent verification fails.
- Scheduled replay preserves scene/file state, partial typing and terminal
  completion; animated typing toggles do not change unrelated event durations.
  Captions clear in lead/gap/trail silence and use measured clip windows.
- Output namespaces reject symlinks, chunk IDs cannot escape audio paths,
  stale frame files are excluded, and repository excerpts cannot follow external links.
- Exact frame sequences and real subtitle burning are enforced; provenance
  binds additional authored content but remains unsigned and does not authenticate carriers.
- Scholarly claims distinguish heuristic timing, historical results and actual
  evidence. Unverified VSpeak attribution and unsupported peer-superiority
  claims are removed; moved code-video-generator provenance is corrected.
- Corrupt backgrounds now fail instead of silently producing a blank illustration.
  Player/static base PNGs no longer bake narration text; the video caption flag
  controls actual SRT burning. Removed the obsolete core-renderer placeholder path.
- Interrupted model transfers cannot occupy the final cache name or replace a
  concurrent publisher. Transport completion is not model authentication.
- Native PDF tests now create controlled two-page files instead of depending on
  an unavailable hardcoded private-machine paper.
- Static subtitle evaluation now occurs at output-frame times, so short cues
  inside held images appear and clear correctly. The paused HTML preview shows
  its first frame during leading silence instead of a broken image.
- Build metadata requires setuptools ≥84.2.1. The Python patch floor removes
  legacy lock partitions carrying setuptools 81 / optional Torch 2.12 advisories;
  no Demo/PDF input route to those advisory mechanisms was established.
- Current engineering observations retain raw source-bound starter timings and
  digest-checked decoded stills from the real Kokoro `af_heart` 2160p render.
  Timing cards no longer compare incompatible units on a common bar scale;
  throughput uses measured encoded-video duration rather than planned timeline.
- Preflight reports dependency presence, not optional-backend readiness. Modern
  SPDX license metadata removes deprecated build declarations without hiding warnings.

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
  versions. The candidate schema is now 1.1; prior 1.0 inputs require migration.
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
  regenerable. Earlier re-render notes reported a suite-count refresh; those
  images are now explicitly historical and not current run evidence.


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
