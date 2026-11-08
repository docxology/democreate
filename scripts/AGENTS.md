# AGENTS.md — scripts/

Thin, runnable front doors over the `democreate` library. The full inventory
with commands lives in [`README.md`](README.md) here; this file is the
contract agents must keep when touching the tree.

## Script inventory

| Script | Delegates to | Notes |
|--------|--------------|-------|
| `00_preflight.py` | direct `democreate` imports + `importlib.util.find_spec` | Diagnostic entry point: imports core modules and probes optional dependency presence, not backend readiness. |
| `generate_demo.py` | `democreate.pipeline.build_demo` | |
| `generate_portfolio.py` | `democreate.portfolio.render_portfolio` | |
| `generate_api_docs.py` | `democreate.api_docs.generate` | Regenerates `docs/api.md`; deterministic, checked in. |
| `build_manuscript.py` | `democreate.manuscript.build_manuscript` | Citation + figure gates; writes `docs/manuscript/output/`. |
| `benchmark.py` | `democreate.pipeline` / `narration` backends | Writes `data/benchmarks.json` — the source the manuscript's evaluation prose is bound to; treat changes to that file as claim-affecting. |

## Design contract

- **No business logic in scripts.** Each script parses args, bootstraps repo
  paths, and makes a single delegated call into `src/democreate/`; behavior
  stays testable in the library and identical to the CLI. New capability goes
  in a `src/democreate/` module first, then gets a thin front door here.
- Run through the project venv: `.venv/bin/python scripts/<name>.py …` — a bare
  `python` may resolve to a shim outside the project env.
- `tests/test_scripts_smoke.py` exercises paper-showcase containment and
  benchmark provenance. CI/release smokes exercise preflight and CLI behavior;
  no inventory claims every script is imported or executed.
