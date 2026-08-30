# AGENTS.md — tests/

- **Mirroring rule (load-bearing):** `src/democreate/<x>/` is tested by
  `tests/<x>/test_*.py`; spine modules by `tests/test_<x>.py`. Keep the mirror
  intact when adding subsystems.
- **No mock framework** (`unittest.mock`, `MagicMock`, `mocker.patch`).
  Real temp files, deterministic backends, real round-trips. The only
  sanctioned patching is `monkeypatch` to simulate an absent binary or force
  the core-only fallback — never to fake a deterministic backend's output.
- **Do not import `democreate` at the top level** of a subsystem test file
  unless the test needs the live registry (keeps suites side-effect-tolerant
  under `--import-mode=importlib`).
- Scope subsystem runs (`tests/<x>/`, `-q`, no `--cov`) to avoid `.coverage`
  races with parallel agents.
- `test_scripts_smoke.py` imports each `scripts/*.py` — a new script must be
  importable or this test fails.
- See `docs/testing_philosophy.md` for the full philosophy.
