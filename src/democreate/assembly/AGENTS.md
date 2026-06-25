# AGENTS — `democreate.assembly`

Guidance for agents modifying this subsystem. Read before editing.

## Scope

This directory owns: timeline construction, compositor backends, caption/subtitle
formatting, and image effects. Do **not** edit files outside this directory
(`schema.py`, `media.py`, `errors.py`, `_logging.py`, `project_paths.py`,
`__init__.py`, `pyproject.toml`, `conftest.py`, or sibling subsystems).

## Invariants (do not break)

- **The timeline is pure.** `build_timeline` must do no I/O and depend only on
  core deps. It produces gap-free, non-overlapping, index-ordered entries —
  `entries[i].start_ms == entries[i-1].end_ms`, and a synced `start_ms` that
  would move backwards is clamped forward, never overlapping.
- **`entry_at_ms` uses a half-open window** `[start, end)`. The boundary `end_ms`
  belongs to the next entry; `total_ms` and negatives return `None`.
- **`frame_count() == round(total_ms / 1000 * fps)`** exactly.
- **Deterministic default principle.** Only `MoviePyCompositor.compose` may
  require a heavy dep; it must detect via `importlib.util.find_spec("moviepy")`
  and raise `BackendUnavailableError("moviepy", extra="video")` when absent. It
  is a guarded legacy adapter slot and still raises `NotImplementedError` when
  MoviePy is present until real assembly is wired. It is marked
  `# pragma: no cover`. Never import `moviepy` at module top level.
- **`ManifestCompositor` must stay core-only.** It imports
  `democreate.capture.screen.render_frame` *lazily* (inside `compose`) and falls
  back to a built-in Pillow renderer if capture is unavailable, so build order
  with the parallel `capture` subsystem never matters. `render_frame(state,
  size)` returns a `PIL.Image.Image`; the compositor saves it to the frame path.
- **Effects are size-preserving and never mutate the input image** (`.copy()` /
  `Image.blend` produce new images).
- **Captions** carry one cue per chunk for `to_srt`/`to_vtt`/`to_ass`; cue timing
  mirrors `build_timeline`'s synced-vs-estimate rule.

## Code style

- `from __future__ import annotations`; full type hints; Google-style docstrings;
  `__all__` per module; `pathlib`, no `os.path`; chain exceptions with `from`;
  ruff line-length 88.
- Heavy/optional deps detected with `importlib.util.find_spec`, never imported at
  module top level. Genuinely-unrunnable code marked `# pragma: no cover`.

## Tests

No mocks. Real computation on real temp files via the `tmp_workspace`,
`sample_demo` fixtures from `conftest.py`. Deterministic only (no RNG/network/
sleep). Cover happy paths, empty inputs, serialization round-trips, and error
branches (assert the exception type). For `MoviePyCompositor`, assert that
calling it without `moviepy` raises `BackendUnavailableError`; do not document it
as implemented assembly until the present-dependency path has a real test.

Run:

```sh
.venv/bin/python -m pytest tests/test_assembly_compositor.py \
  tests/test_assembly_compositor_extra.py tests/test_assembly_captions.py \
  tests/test_assembly_effects.py tests/test_assembly_audio.py -q
```

This subsystem owns: `compositor.py`, `captions.py`, `effects.py`, `animator.py`,
`audio.py` (plus `__init__.py`, `README.md`, `AGENTS.md`).
