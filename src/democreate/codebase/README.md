# `democreate.codebase`: Python AST facts and import graphs

Codebase analysis for DemoCreate codebase scenes. Turns a Python repository into
structured, JSON-able summaries and visualizations that a scene can narrate —
all with **pure standard-library `ast`**, no heavy dependencies.

## Modules

| Module | Purpose |
|--------|---------|
| `walker.py` | Parse source with `ast` into `ModuleSummary` (functions, classes, methods, imports, LOC). |
| `ast_viz.py` | Render summaries as an indented text tree or a Graphviz DOT graph (pure strings). |
| `dependency.py` | `DependencyGraph` value type + `build_import_graph` for intra-package import edges. |

## Public API

### `walker`
- `FunctionInfo(name, lineno, end_lineno, args, docstring, is_method=False)` — `.to_dict()`.
- `ClassInfo(name, lineno, end_lineno, docstring, methods)` — `.to_dict()`.
- `ModuleSummary(path, name, docstring, functions, classes, imports, loc)` —
  `.symbol_count` property, `.to_dict()`.
- `summarize_source(source, *, path="<string>", name=None) -> ModuleSummary`
- `summarize_module(path: Path) -> ModuleSummary` — raises `DemoCreateError` on a
  read or syntax error.
- `walk_repository(root, *, pattern="**/*.py", exclude=(...)) -> list[ModuleSummary]` —
  deterministic sorted order; excluded directories are relative to `root`, not
  its ancestors; returned paths retain the caller's spelling. Unparsable files
  are logged and skipped.

### `ast_viz`
- `module_to_tree(summary) -> str` — indented `module > class > method`, then functions.
- `repository_to_dot(summaries) -> str` — Graphviz DOT with one cluster per module.

### `dependency`
- `DependencyGraph(nodes, edges)` — `add_node`, `add_edge`, `neighbors`,
  `topological_order()` (dependencies before dependents; raises `DemoCreateError`
  on a cycle), `find_cycles()`, `to_dot()`.
- `build_import_graph(root, *, package=None) -> DependencyGraph` — edges only
  between modules discovered under `root`; external imports ignored. Deterministic.

`topological_order()` treats an edge `(a, b)` as "`a` depends on `b`", so `b`
precedes `a` in the result.

Relative imports in a package's `__init__.py` resolve from that package, while
ordinary modules resolve from their containing package. Graph node keys remain
root-relative dotted names (`sub` for `sub/__init__.py`, `sub.leaf` for
`sub/leaf.py`).

## Optional packages do not change the walker

The implemented source walker is Python stdlib `ast`. The published `codebase`
extra installs tree-sitter packages, but no current analysis function selects
them; it is not an implemented multi-language backend. Non-Python project
portfolio summaries can use README/stat facts without Python code scenes.
See [backend boundaries](../../../docs/backends.md).

## Tests

`tests/codebase/test_walker.py`, `tests/codebase/test_ast_viz.py`,
`tests/codebase/test_dependency.py` — real computation on temp files and on the
live `src/democreate` tree. No mocks.
