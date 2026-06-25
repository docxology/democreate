# AGENTS — `democreate.codebase`

Guidance for agents working inside this subsystem.

## What this subsystem is

AST traversal, visualization, and dependency-graph tooling for Python
repositories. The deterministic default is pure stdlib `ast`. Consumers
(codebase scenes) get `ModuleSummary` objects, text/DOT visualizations, and an
intra-package import `DependencyGraph`.

## Invariants (do not break)

- **Pure default, no heavy imports at top level.** Only stdlib + the package's
  own `errors`/`_logging`. `tree-sitter` is an optional upgrade (extra:
  `codebase`); if a future real backend is added, detect with
  `importlib.util.find_spec("tree_sitter")` and raise
  `BackendUnavailableError("tree-sitter", extra="codebase")` when missing. Mark
  any path that needs a heavy binary with `# pragma: no cover`.
- **Import the spine types, never redefine.** Use `democreate.errors.DemoCreateError`
  and `democreate._logging.get_logger`. Do not touch `schema.py`, `media.py`,
  `errors.py`, `_logging.py`, `project_paths.py`, `__init__.py`, `pyproject.toml`,
  or `conftest.py`.
- **Determinism.** `walk_repository` sorts by path; `topological_order` and
  `find_cycles` break ties alphabetically; DOT output is order-stable. Keep it so.
- **Syntax errors raise `DemoCreateError`** chained with `from`; `walk_repository`
  logs-and-skips unparsable files rather than aborting.

## Edge semantics

`build_import_graph` / `DependencyGraph`: edge `(a, b)` means `a` imports
(depends on) `b`. `topological_order()` emits dependencies before dependents
(so `b` before `a`). Only edges between modules discovered under the walked root
are kept; stdlib/third-party imports are dropped.

## Files owned

- `walker.py`, `ast_viz.py`, `dependency.py`, `__init__.py`
- `README.md`, `AGENTS.md`
- Tests: `tests/codebase/test_walker.py`, `tests/codebase/test_ast_viz.py`,
  `tests/codebase/test_dependency.py`

## Verify

```
cd <repo> && .venv/bin/python -m pytest \
  tests/codebase/test_walker.py tests/codebase/test_ast_viz.py \
  tests/codebase/test_dependency.py -p no:cacheprovider -q
```

Keep ruff clean at line length 88 and maintain the configured ≥90% coverage gate.
