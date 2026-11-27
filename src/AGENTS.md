# AGENTS.md — src/

- [`democreate/`](democreate/AGENTS.md) is the package. Its subsystem guides
  describe their respective responsibilities and implementation contracts.
- `democreate.egg-info/` — generated packaging metadata from `uv pip install
  -e .`; regenerate, never edit.
- Import heavy optional dependencies inside the functions that use them. See
  the [project-wide agent guide](../AGENTS.md) for the full import contract.
