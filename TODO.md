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
