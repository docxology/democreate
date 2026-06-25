# AGENTS — democreate.animation

Guidance for agents editing this subsystem.

## Boundaries
- Owns exactly: `__init__.py`, `highlights.py`, `zoom.py`, `manim_scenes.py`,
  `fonts.py`, `waveform.py`, `diagram.py`, `README.md`, `AGENTS.md` in this
  directory, plus the matching `tests/animation/test_*.py` files
  (`highlights`, `zoom`, `manim`, `fonts`, `waveform`, `diagram`).
- Do **not** modify the spine: `schema.py`, `media.py`, `errors.py`,
  `_logging.py`, `project_paths.py`, `__init__.py` (package root), `pyproject.toml`,
  `conftest.py`, or any sibling subsystem.

## Deterministic-default rule
- Never import a heavy/optional dep at module top level. The only optional dep
  here is `manim`; detect it with `importlib.util.find_spec("manim")` and raise
  `BackendUnavailableError("manim", extra="animation")` when absent.
- `render_manim_scene` is the single heavy path and is marked `# pragma: no cover`.
- `rich` and `PIL` are core deps. `PIL` is still imported lazily inside the
  functions that use it (mirrors the spine's "import-light module" style) so the
  module imports cleanly and fast.

## Conventions to match
- `from __future__ import annotations`; full type hints; Google-style docstrings;
  module docstring; `__all__`; `pathlib.Path`; exception chaining with `from`;
  `get_logger(__name__)`.
- ruff line-length 88 (E501 ignored).

## Determinism invariants (do not break)
- `render_code_image` must stay byte-stable across machines: keep the fixed cell
  size and fixed colors; do not switch to host-font metrics or theme-dependent
  raster colors.
- `compute_zoom_path` output must remain time-sorted with every `scale >= 1`.
- `interpolate` must clamp outside the track and never divide by zero on a
  zero-span segment.
- `apply_zoom` must return a new image of the exact input size.

## Tests
No mocks. Real `rich`/`PIL` computation on in-memory data. The manim render path
is covered only by an unavailable-backend assertion (skipped if manim is present)
plus an `importorskip` smoke test.

Run:
```
.venv/bin/python -m pytest tests/animation/test_highlights.py \
  tests/animation/test_zoom.py tests/animation/test_manim.py -p no:cacheprovider -q
```
