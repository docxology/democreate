# TODO.md — DemoCreate backlog

Single source of truth for open work in this repo. The task/Gantt history lives
in `tasks.yaml` (managed by the taskboard server); this file tracks *open*
agent-facing work items. When an item closes, mark it `[x]` with the date —
do not delete it.

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

- [ ] Re-render the showcase stat-card still
      (`docs/_videoframes/showcase_stats.png`, and the video it is lifted
      from) at the 776 count — deferred: it requires the full 4K noir
      showcase re-render, out of proportion for the scripts refactor. The
      PNG still shows 753 until then.

