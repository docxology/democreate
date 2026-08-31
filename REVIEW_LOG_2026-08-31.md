# Review Log — 2026-08-31 (agent-ergonomics deep pass)

Fleet lane: democreate. Branch: `main`. Dirty files at dispatch: 42 (all treated
as pre-existing; they are the in-progress `manuscript/` -> `docs/manuscript/`
migration: 25 deletions of the old top-level tree, the new `docs/manuscript/`
tree, plus path-string edits in README.md, domain_profile.yaml, scripts/README.md,
scripts/build_manuscript.py, examples/make_showcase.py).

## Phase 0 — preflight

- `git fetch origin` OK; branch `main` per brief; remote
  `https://github.com/docxology/democreate.git`.
- Inventory: entry docs README.md + AGENTS.md; docs hub docs/README.md +
  docs/AGENTS.md; status/tasks file `tasks.yaml`; no backlog file (created
  TODO.md per brief); no review log existed (created this one); no `output/`
  dir at dispatch (gitignored, regeneratable); `.humos/` sidecar present
  (matches the CHANGELOG [Unreleased] entry).

## Phase 1 — cold-start audit

Read README.md and AGENTS.md cold, then attempted the three orientation tasks:

- (a) Current status — PASS. README states version 0.7.1 / alpha; verified
  against `pyproject.toml` (`version = "0.7.1"`) and
  `src/democreate/__init__.py:48`. CHANGELOG [Unreleased] names the `.humos/`
  sidecar work, which is present on disk.
- (b) What to do next — FAIL before changes. No backlog file existed;
  `tasks.yaml` (the task source of truth) is not referenced from README.md or
  AGENTS.md. Fixed: TODO.md created and signposted from AGENTS.md.
- (c) How to run primary verification — PASS. README "Testing" + AGENTS.md
  "Verification before claiming done" give `.venv/bin/python -m pytest -q`,
  `pytest --cov`, `ruff check . && mypy src`. Verified collect-only this
  session: 744 tests collected. Full suite not run in this pass (external-drive
  I/O; this pass is docs-scoped).

Mechanical sweep:

- Link check over `*.md`, `docs/*.md`, `docs/*/*.md`: 171 relative links
  checked, 0 broken. Two initial hits (`figures/x.png` in
  docs/manuscript/README.md + AGENTS.md) are inline-code syntax examples, not
  links — false positives.
- Stale-claim check: README's "744 tests" re-verified against
  `pytest --collect-only -q` (744). Version strings consistent across
  pyproject / `__init__` / README.
- Real defect found: `scripts/build_manuscript.py` docstring (updated in the
  pre-existing migration edits) says `docs/manuscript/config.yaml`, but
  `_MANUSCRIPT = _REPO / "manuscript"` still pointed at the deleted top-level
  tree, so the script's own documented default invocation was broken. Fixed
  (Phase 3).
- Dead weight: none found — no stale audit reports or scratch files in active
  navigation.

## Phase 2 — scope (TODO.md)

All findings entered in TODO.md (Minor x3, Medium x1 done, Major x1 deferred).

## Phase 3 — implemented

1. `scripts/build_manuscript.py`: `_MANUSCRIPT = _REPO / "docs" / "manuscript"`
   — makes the documented command work. (Minimal source change, allowed by the
   shared frame's "trivially required to make a documented command actually
   work" carve-out.)
2. `docs/manuscript/MANUSCRIPT_STATUS.md`: fixed the self-referential Location
   line (canonical `docs/manuscript/`, legacy top-level `manuscript/` fallback).
3. `TODO.md` created (backlog, per brief).
4. `AGENTS.md`: added "Current state & where to look next" orientation-ladder
   section pointing to tasks.yaml (status), TODO.md (next actions), and the
   verification commands.

## Phase 4 — verify & close

- Link checker re-run over touched docs: 0 broken.
- Fast gate: not run (full pytest suite is multi-minute on the external drive;
  ruff/mypy deferred to CI — recorded as not-run, not claimed green).
- Commits: path-scoped adds only; pre-existing migration files NOT committed
  (they belong to the migration lane, not this pass).
