# AGENTS.md — DemoCreate (project-level)

Operating rules for any agent modifying this repository. These are project-wide
invariants; each subsystem directory under `src/democreate/` (`capture/`,
`narration/`, `animation/`, `codebase/`, `assembly/`, `export/`, `paper/`) also
carries its own `AGENTS.md` with subsystem-specific scope and backend maps — read
the local pair (`AGENTS.md` + `README.md`) before touching a subsystem.

## The non-negotiables

1. **Thin orchestrators.** `cli.py` and `pipeline.py` carry no business logic.
   Every command and every pipeline stage resolves to a few calls into the
   subsystems and the spine. If you find yourself adding domain logic to the CLI
   or the pipeline, it belongs in a subsystem module instead.

2. **No mocking framework in tests.** Tests use real temp files (`tmp_path`), the
   real deterministic backends, and real serialization round-trips — no
   `unittest.mock`/`MagicMock`, and never a faked deterministic-backend value. The
   only sanctioned patching is `monkeypatch` to simulate an *absent* optional
   binary or force the core-only fallback branch; if a core behavior cannot be
   tested without faking its output, the design is wrong — make the deterministic
   default do the real thing on core deps.

3. **≥90% coverage on the pure-Python core.** `fail_under = 90` is enforced in
   `pyproject.toml` (`[tool.coverage.report]`). Thin adapters to heavy backends
   are excluded with `# pragma: no cover`; everything else must be exercised.

4. **Deterministic defaults.** Every subsystem's default backend must produce
   byte-for-byte stable output for the same input: no RNG, no wall-clock, no
   network, no external fonts beyond `ImageFont.load_default()`. Tests assert
   determinism; keep them green.

5. **Never import a heavy/optional dependency at module top level.** Heavy deps
   (`kokoro`, `chatterbox`, `whisper`, `mss`, `playwright`, `manim`, `moviepy`,
   `pynput`, `pyautogui`, `tree_sitter`, `numpy`, `soundfile`, `ffmpeg`) must be
   imported lazily inside the function that needs them. Detect availability with
   `importlib.util.find_spec("name")`. The package `__init__` and every public
   module must import cleanly with only the core deps installed.

## Backend contract

- A real backend that is invoked without its dependency raises
  `BackendUnavailableError(backend, extra=...)`, which carries the pyproject
  optional-dependency extra so the message tells the user exactly what to install
  (`uv sync --extra <extra>`). Verify availability in the constructor so the
  failure is early.
- Real-binary / heavy-backend code paths carry `# pragma: no cover`. The default
  backends and all pure logic stay import-safe and fully testable on core deps.

## Code style (matches the spine)

- `from __future__ import annotations` at the top of every module.
- Full type hints and Google-style docstrings on every public symbol; module
  docstrings everywhere; `__all__` per module.
- `pathlib.Path` only — never hardcode machine paths; route output through a
  `Workspace`. No bare `except`; chain exceptions with `from`.
- ruff-clean at line length 88 (`ruff check`), mypy-clean (`mypy`).
- Import shared value types from `..schema` / `..media`; never copy or redefine
  the spine types (`Demo`, `Scene`, `Chunk`, `Action`, `ActionType`,
  `SceneKind`, `WordTimestamp`, `AudioClip`, `FrameState`).

## Scope discipline

- The spine (`schema.py`, `media.py`, `errors.py`, `project_paths.py`,
  `_logging.py`) is load-bearing for every subsystem. Change it only when the
  contract genuinely needs to evolve, and bump `SCHEMA_VERSION` if the on-disk
  representation changes.
- Tools (`bun`/`bunx` are not used here — this is a Python package) run through
  the project venv. Use `.venv/bin/python -m pytest …`; a bare `python` may be a
  pyenv shim that fakes a green suite.
- Run a subsystem's tests scoped (`-q`, no `--cov`) to avoid `.coverage` races
  with parallel agents; run the full suite with coverage only as a final gate.

## Verification before claiming done

- `ruff check` clean, `mypy` clean.
- `.venv/bin/python -m pytest -q` green.
- `.venv/bin/python -m pytest --cov` reports ≥90% on the core.
- The package imports with only core deps: `python -c "import democreate"`.
