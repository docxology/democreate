# AGENTS.md — `democreate.capture`

Guidance for agents modifying this subsystem.

## What this subsystem owns
Rendering frames and recording terminal/browser/input sessions. It consumes the
spine value types (`FrameState`, `Demo`, `Scene`, `Action`, `ActionType`,
`SceneKind`) and never redefines them.

## Hard rules (match the spine)
- `from __future__ import annotations` at the top of every module.
- Full type hints + Google-style docstrings on every public symbol; module
  docstrings everywhere; `__all__` per module.
- `pathlib.Path` only; no bare `except`; chain exceptions with `from`.
- Import the shared types from `..media` / `..schema`; never copy them.
- ruff-clean at line length 88.

## The deterministic-default principle (do not break)
- NEVER import a heavy/optional dep at module top level. Detect with
  `importlib.util.find_spec("name")` via the local `_have(dep)` helper.
- If a real backend is invoked without its dep, raise
  `BackendUnavailableError("<dep>", extra="<extra>")`. Verify in the constructor
  so the failure is early.
- Real-binary code paths carry `# pragma: no cover`. The default backends and all
  pure logic stay import-safe and fully testable on core deps only.

## Backend map
| Module | Default (pure) | Real backend (guarded) | Extra |
|--------|----------------|------------------------|-------|
| `screen.py` | `SyntheticRenderer` | `MssScreenCapture` (`mss`) | `capture` |
| `terminal.py` | all of it (pure) | — | — |
| `browser.py` | `NullBrowserDriver` | `PlaywrightBrowserDriver` (`playwright`) | `browser` |
| `replay.py` | event model (pure) | `record_session`/`replay_session` (`pynput`/`pyautogui`) | `replay` |

## Determinism contract
`SyntheticRenderer` output must be byte-for-byte stable for a given
`(FrameState, size)` — no RNG, no clocks, no font files beyond
`ImageFont.load_default()`. `record_commands` uses a fixed synthetic timing
model. Tests assert these invariants; keep them green.

## Tests
No mocks. Real temp files via `tmp_path` / `sample_demo`. Heavy backends are only
checked for the `BackendUnavailableError` path (the deps are absent in CI).
Run: `.venv/bin/python -m pytest tests/capture/test_*.py -q` (no `--cov` to avoid
`.coverage` races with parallel agents).

## Scope
Touch only files under `src/democreate/capture/` and the four
`tests/capture/test_*.py`. Do not edit the spine, `__init__.py` of the package
root, `pyproject.toml`, or `conftest.py`.
