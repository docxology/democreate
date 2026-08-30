# AGENTS.md — src/

- `democreate/` — the package (each subsystem dir has its own `AGENTS.md` +
  `README.md`; see `democreate/AGENTS.md` at the project root for the contract).
- `democreate.egg-info/` — generated packaging metadata from `uv pip install
  -e .`; regenerate, never edit.
- Import rule: heavy optional deps are imported lazily inside functions
  (see root `AGENTS.md` non-negotiables).
