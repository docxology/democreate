# AGENTS.md — tests/export/

- Mirrors `src/democreate/export/`; a new module there needs a `test_*.py` here.
- No mock framework; deterministic backends and real files only
  (`monkeypatch` allowed only for absent-binary / core-only-fallback paths).
- No top-level `import democreate` unless the live registry is needed.
- Run scoped: `.venv/bin/python -m pytest -q tests/export/` (no `--cov`).
