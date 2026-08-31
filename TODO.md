# TODO.md — DemoCreate backlog

Single source of truth for open work in this repo. The task/Gantt history lives
in `tasks.yaml` (managed by the taskboard server); this file tracks *open*
agent-facing work items. When an item closes, mark it `[x]` with the date —
do not delete it.

## Minor

- [ ] `docs/README.md` states "(744 collected, ≥90% coverage)" as a bare number.
      Verified 2026-08-31 via `.venv/bin/python -m pytest --collect-only -q`
      (744 collected). Numbers rot — consider "verify with
      `.venv/bin/python -m pytest --collect-only -q | tail -1`" instead of a count.
- [ ] Version string is stated in three places (`pyproject.toml`,
      `src/democreate/__init__.py`, README badge/text). `pyproject.toml` is
      canonical; README prose could link to it instead of restating `0.7.1`.
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

- [ ] Finish the `manuscript/` → `docs/manuscript/` migration at the repo level:
      the tree move itself was done pre-2026-08-31 (deletions staged in the
      working tree), and the script constant is now fixed, but a repo-wide grep
      for stale `manuscript/` references should be run after the migration
      commits land: `grep -rn 'manuscript/' --include='*.md' . | grep -v docs/manuscript`
