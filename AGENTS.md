# AGENTS.md — DemoCreate

Operating rules for any agent working in this repository. This root file is the
canonical, project-wide contract. The detailed agent guidance lives in
[`docs/AGENTS.md`](docs/AGENTS.md), and **every subsystem directory** under
`src/democreate/` carries its own `AGENTS.md` (scope + backend map) and
`README.md` (what it does). Before touching a subsystem, read its local
`AGENTS.md` + `README.md` pair.

## What this package is

`democreate` generates audio-visual demos of software from a single declarative
`Demo` artifact (a virtual-IDE action stream + narration chunks). Rendering is a
pure function of the artifact. Read [`README.md`](README.md) and
[`docs/architecture.md`](docs/architecture.md) for the full picture.

## The non-negotiables

1. **Thin orchestrators.** `cli.py` and `pipeline.py` carry no business logic —
   each command and pipeline stage is a few calls into the subsystems and the
   spine. Domain logic belongs in a subsystem module.
2. **No mocking framework in tests.** Real temp files (`tmp_path`), real
   deterministic backends, real round-trips — no `unittest.mock`/`MagicMock`. The
   only sanctioned patching is `monkeypatch` to simulate an absent binary or force
   the core-only fallback path; never to fake a deterministic backend's output.
3. **≥90% coverage on the pure core.** Enforced by `fail_under = 90` in
   `pyproject.toml`. Heavy adapters are excluded with `# pragma: no cover`.
4. **Deterministic defaults.** Every default backend yields byte-for-byte stable
   output for the same input: no RNG, no wall-clock, no network, no external
   fonts beyond `ImageFont.load_default()`.
5. **Never import a heavy/optional dependency at module top level.** Heavy deps
   (`kokoro`, `chatterbox`, `whisper`, `mss`, `playwright`, `manim`, `moviepy`,
   `pynput`, `pyautogui`, `tree_sitter`, `numpy`, `soundfile`) are imported
   lazily inside the function that needs them, gated by
   `importlib.util.find_spec`. The package must `import democreate` cleanly on
   core deps alone.

## Backend contract

- Invoking a real backend without its dependency raises
  `BackendUnavailableError(backend, extra=...)`, carrying the pyproject extra so
  the message tells the user exactly what to install. Verify in the constructor so
  the failure is early.
- Real-backend / heavy code paths carry `# pragma: no cover`.

## Code style (matches the spine)

- `from __future__ import annotations` atop every module.
- Full type hints + Google-style docstrings on every public symbol; module
  docstrings everywhere; `__all__` per module.
- `pathlib.Path` only; never hardcode machine paths — route output through a
  `Workspace`. No bare `except`; chain with `from`.
- ruff-clean at line length 88; mypy-clean.
- Import the spine value types from `..schema` / `..media`; never copy or
  redefine `Demo`, `Scene`, `Chunk`, `Action`, `ActionType`, `SceneKind`,
  `WordTimestamp`, `AudioClip`, `FrameState`.

## Scope discipline

- The spine (`schema.py`, `media.py`, `errors.py`, `project_paths.py`,
  `_logging.py`) is load-bearing for every subsystem. Change it only when the
  contract must evolve; bump `SCHEMA_VERSION` if the on-disk representation
  changes.
- This is a Python package: run tooling through the project venv. Use
  `.venv/bin/python -m pytest …` — a bare `python` may be a shim that fakes a
  green suite.
- Run subsystem tests scoped (`-q`, no `--cov`) to avoid `.coverage` races with
  parallel agents; run the full coverage gate as a final step.
- **Tests mirror the source tree:** a subsystem `src/democreate/<x>/` is tested by
  `tests/<x>/test_*.py`; root spine modules (`schema`, `pipeline`, `portfolio`, …)
  by `tests/test_<x>.py`; integration/meta tests stay at the `tests/` root. Scope a
  subsystem run with `tests/<x>/`. See [`docs/testing_philosophy.md`](docs/testing_philosophy.md).

## Verification before claiming done

- `ruff check .` clean and `mypy src` clean.
- `.venv/bin/python -m pytest -q` green.
- `.venv/bin/python -m pytest --cov` reports ≥90% on the core.
- `python -c "import democreate"` succeeds on a core-only install.

See [`docs/testing_philosophy.md`](docs/testing_philosophy.md) for the full
testing contract and [`docs/`](docs/README.md) for the documentation hub.
