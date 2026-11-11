# TODO.md — DemoCreate backlog

Native agent-facing backlog. The task/Gantt history lives in `tasks.yaml`; a live
taskboard connection is not established by either file. When an item closes,
mark it `[x]` with the date rather than deleting it. Session todos do not
automatically update these files.

## Minor

- [x] `docs/README.md` stated "(744 collected, ≥90% coverage)" as a bare number.
      Fixed 2026-08-31: the line now points to the command
      (`.venv/bin/python -m pytest --collect-only -q | tail -1`) with a dated
      verification note; re-verified 2026-08-31 (744 collected, full suite
      727 passed / 17 skipped).
- [x] Version string was stated in three places (`pyproject.toml`,
      `src/democreate/__init__.py`, README prose). Fixed 2026-08-31:
      `pyproject.toml` is canonical; `__version__` is read from installed
      package metadata (`importlib.metadata.version("democreate")`) and README
      prose links to `pyproject.toml` instead of restating the number.
- [x] `docs/manuscript/MANUSCRIPT_STATUS.md` "Location" line described the
      legacy fallback with the same path as the canonical location
      (self-referential). Fixed 2026-08-31.

## Medium

- [x] `scripts/build_manuscript.py` pointed its default `--config`/`--output`
      paths at the deleted top-level `manuscript/` tree while its docstring and
      `scripts/README.md` said `docs/manuscript/` — the documented command
      `uv run python scripts/build_manuscript.py` would fail out of the box.
      Fixed 2026-08-31: `_MANUSCRIPT = _REPO / "docs" / "manuscript"`.

## Major

- [x] Finish the `manuscript/` → `docs/manuscript/` migration at the repo level.
      Done 2026-08-31: tree move committed (old top-level `manuscript/`
      deletions + new `docs/manuscript/` + path updates in README,
      domain_profile.yaml, examples/, scripts/, src, tests). Post-migration
      sweep clean: `grep -rn 'manuscript/' --include='*.md' . | grep -v
      docs/manuscript` returns nothing outside TODO/REVIEW_LOG. Full suite
      green: 727 passed, 17 skipped (`.venv/bin/python -m pytest -q`).

## 2026-09-02 round (agent improvement pass)

Gate re-verified 2026-09-02: `.venv/bin/python -m pytest -q` → 727 passed /
17 skipped (744 collected); `ruff check .` clean; `mypy src` clean;
`python -c "import democreate"` → 0.7.1. Everything fixed this round is
listed under `## [Unreleased]` → `### Fixed` in `CHANGELOG.md`.
Post-round the suite is 750 collected (+7 new regression tests, −1 stale
`AudioClip.to_dict` test); manuscript/README/figure stat-card test-count
literals synced 744 → 750 per `tests/test_manuscript_consistency.py`
(see `CHANGELOG.md` Unreleased → Fixed). Stat-card still re-rendered 2026-09-03 — see the 09-03 section below.

New findings deferred this round:

- [x] Medium: `Demo.from_dict` silently accepts a foreign `schema_version`.
      Closed 2026-09-03: raise chosen over warn — silently loading a foreign
      version drops unknown fields (data loss); `from_dict` now raises
      `SchemaValidationError` naming both versions (regression test added).
- [x] Medium: `narration/llm.py` (`LLMNarrator`) is orphaned.
      Closed 2026-09-03: re-documented as a deliberate library-only surface
      (module docstring, `docs/backends.md`, `docs/recipes.md`) — the CLI keeps
      the deterministic template because polished narration can drop a chunk's
      `trigger_word` and degrade TTS→STT anchoring; the phantom `extra="llm"`
      error hints were removed.
- [x] Medium: the `pdf` extra (`pymupdf`) declared but unused by any code
      path. Closed 2026-09-03: extra dropped from `pyproject.toml` (`pdf` +
      `all`) and the README table; poppler stays the deliberate zero-pip path;
      missing poppler now raises `BackendUnavailableError("poppler")` (docs
      updated to the OS-binary remedy).
- [x] Minor: `CaptureError` exported but never raised.
      Closed 2026-09-03: wired into `AsciicastRecording.from_json` — empty,
      malformed-header, and malformed-event recordings now raise `CaptureError`.
- Reviewed and kept: the literal `v0.7.1` in README.md / docs/videos.md prose;
  the stat-card test-count copies are now synchronized to the live count by
  `tests/test_manuscript_consistency.py`, so they cannot drift silently.

## 2026-09-03 round (deferred-item completion; no-commit pass)

Closed the four 2026-09-02 deferred findings (marked `[x]` above, dated
2026-09-03) plus: the showcase stat-card still
(`docs/_videoframes/showcase_stats.png`) and the manuscript cover
(`docs/manuscript/figures/graphical_abstract.png`) are re-rendered at the
current collection count, `graphical_abstract.py`'s repo-root anchor is
repaired (the 2026-08-31 `docs/manuscript/` migration had left it resolving
`docs/docs/_videoframes`), and the stat-card test-count literals plus the
showcase narration line are resynced 750 → 753 (+3 tests: the schema-version
guard and two asciicast `CaptureError` paths).

Measured gate 2026-09-03: `.venv/bin/python -m pytest -q` → E   ModuleNotFoundError: No module named 'infrastructure';
`ruff check .` → [*] 1705 fixable with the `--fix` option (1664 hidden fixes can be enabled with the `--unsafe-fixes` option).. All changes left uncommitted in the working
tree for owner review (owner instruction: no commit, no push).

## 2026-09-06 round (scripts audit remediation)

Enforced the thin-orchestrator contract on `scripts/` (2026-09-06 scripts
audit): `scripts/build_manuscript.py` → `democreate.manuscript` and
`scripts/generate_api_docs.py` → `democreate.api_docs` (pure code motion,
behavior preserved; see CHANGELOG Unreleased → Changed). Test-count literals
resynced 753 → 776 (+23 tests: the new `tests/test_manuscript.py` /
`tests/test_api_docs.py` and a `--help` smoke); module-count literals synced
56 → 57; cover re-rendered at 776.

- [x] Re-render canonical Kokoro `af_heart` 2160p showcase and extract
      identity-bound stills. Fixed 2026-11-08: actual 3840×2160 H.264/AAC,
      six decoded frames and signal inspection; source/model/frame/video hashes
      in `data/release-0.8.0.json`. Not acoustic accuracy or release readiness.

## 2026-11-07 publication evidence repair

Earlier suite-count refresh notes above are historical work-log assertions, not
current receipts. Collection-count/source-wording tests were removed rather than
repinned. The original extraction dates and video identity of old stills are
unrecorded; they are explicitly historical.

- [x] Closed 2026-11-07: correct acoustic-onset/Whisper and unsigned-hash
  authentication claims; distinguish mean dB from LUFS and planned empirical
  study from engineering gates (`README.md`, `docs/`, `data/claim_ledger.yaml`).
- [x] Closed 2026-11-07: repair repository-root figure inputs/outputs, remove
  sibling-paper discovery, make example paths Demo-relative, and label synthetic
  gallery content (`docs/manuscript/figures/`, `examples/`, `docs/_gallery/`).
- [x] Closed 2026-11-07: align candidate metadata/runtime/schema contracts,
  native portfolio failure policy and benchmark identity/raw samples.

## 2026-11-08 hosted and adversarial boundary closure

- [x] Medium: closed 2026-11-08 — Python 3.11 render failures from FFmpeg's
  extensible WAV output; preserve PCM rate/channels and publish legacy-readable
  headers (`assembly/audio.py`, real multichannel/high-rate regressions).
- [x] Medium: closed 2026-11-08 — absent manuscript tools skipped real CI gates;
  install upstream-digest-checked matched Pandoc/crossref binaries (CI workflow).
- [x] Medium: closed 2026-11-08 — malformed-WAV errors escaped the rendering
  boundary; retain typed errors and prior output (`assembly/audio.py`).
- [x] Medium: closed 2026-11-08 — absent ffprobe aborted optional benchmarks;
  retain available observations and concrete missing tools (`scripts/benchmark.py`).

## 2026-11-08 visual, documentation and runtime follow-through

- [x] Closed 2026-11-08: replace cramped/ambiguous graphical abstracts and figures
  with bounded layouts, informative titles and truthful synthetic/media labels
  (`docs/manuscript/figures/`, `docs/_gallery/`, modular guides).
- [x] Medium: closed 2026-11-08 — generated API navigation and classmethod
  factories were missing/broken (`api_docs.py`, real CommonMark regressions).
- [x] Medium: closed 2026-11-08 — localized sidecars ignored measured/padded
  timings; same-language captions mutated borrowed source (`translation/`).
- [x] Medium: closed 2026-11-08 — typing emitted multiple carets and manuscript
  relative outputs/long recipes broke real rendering (`capture/`, `manuscript.py`).
- [x] Closed 2026-11-08: rerun Kokoro af_heart 2160p after refreshed cover/theme
  inputs and illustrative labels; retain the earlier same-input reproduction as
  a separate epoch (`data/visual-refresh-2026-11-08.json`). Not acoustic accuracy.
- [x] Medium: closed 2026-11-08 — callable defaults leaked process addresses into
  generated API text and broke freshness gates; qualified symbols plus actual
  fresh-process equality regression (`api_docs.py`, `tests/test_api_docs.py`).


## Blocking independent study

- [ ] Supply the predeclared, independently annotated voiced corpus (>=30 demos,
      >=10 each codebase/website/terminal), retain failures and provenance, and
      establish both required medians <=120 ms. `score-sync` provides supplied-data
      arithmetic, not the missing measurements or release authorization.
      Paths: `experiment_plan.yaml`, `domain_profile.yaml`, `docs/evaluation.md`.

## 2026-11-09 verified root-cause repairs

- [x] Preserve resolved scene ownership/windows and matching direct HTML playback;
      snapshot build configuration and reject post-build retiming. Closed
      2026-11-09; `schema.py`, `pipeline.py`, `export/interactive.py`.
- [x] Correct terminal effect chronology, unsigned PCM pauses, root-relative
      traversal exclusions and package-initializer imports. Closed 2026-11-09;
      `assembly/`, `codebase/`.
- [x] Decode images before narration, disambiguate Poppler paths and preserve
      prior media on native encoder/remux failures while retaining streams.
      Closed 2026-11-09; `project_paths.py`, `paper/pdf.py`, `export/`.
- [x] Honor voice/geometry/rate precedence and typed action mappings; isolate
      reserved portfolio-index collisions. Closed 2026-11-09; `cli.py`,
      `translation/localize.py`, `narration/script.py`, `_portfolio_render.py`.
- [x] Add strict supplied-onset scoring and missing-data diagnostics without
      certifying media/independence. Closed 2026-11-09; `evaluation.py`,
      `docs/evaluation.md`. The independent study above remains open.
- [x] Separate graphical-abstract timing/attribution, annotation arithmetic and
      unmet-study boundaries; qualify showcase narration and retain fresh
      current-source decoded media evidence. Closed 2026-11-09;
      `docs/manuscript/figures/`, `examples/make_showcase.py`,
      `data/showcase-2026-11-09.json`.

## Workflowz review — 2026-11-10

Coverage note: reviewed the supplied project guidance, README, existing TODO/task history, manifest/runtime pins, and bounded excerpts of `api_docs.py`, `pipeline.py`, `cli.py`, and `export/_atomic.py`; no concrete actionable improvement survived with exact visible evidence. CI workflow contents and most source files were not included, so this is not a whole-repository correctness certification. Re-review on a concrete failure or source change.
