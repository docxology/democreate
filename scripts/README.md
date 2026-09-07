# `scripts/`

Thin, runnable front doors over the `democreate` library. Each script carries no
business logic of its own — it parses arguments, bootstraps repo paths, and
makes a single delegated call into a `src/democreate/` module — so the behavior
stays testable in the library and identical to the CLI. Run them through the
project venv (`.venv/bin/python scripts/<name>.py …`).

| Script | Purpose | Delegates to | Command |
|--------|---------|--------------|---------|
| `00_preflight.py` | Environment preflight — checks the core imports and which optional backend extras (kokoro, whisper, mss, playwright, manim, moviepy, tree-sitter, pynput) are installed. | direct `democreate` imports + `importlib.util.find_spec` | `.venv/bin/python scripts/00_preflight.py` |
| `generate_demo.py` | Build one demo artifact end-to-end from a `.json`/`.yaml` demo into an output workspace. | `democreate.pipeline.build_demo` | `.venv/bin/python scripts/generate_demo.py demo.json --output output` |
| `generate_portfolio.py` | Render a timestamped summary video per project under a directory — the batch front door for `democreate portfolio`. | `democreate.portfolio.render_portfolio` | `.venv/bin/python scripts/generate_portfolio.py <projects_dir>` |
| `generate_api_docs.py` | Regenerate `docs/api.md` from the live package (a curated module list → public classes/functions). Re-run after the public API changes. | `democreate.api_docs.generate` | `.venv/bin/python scripts/generate_api_docs.py` |
| `build_manuscript.py` | Build the manuscript artifacts under `docs/manuscript/` (citation + figure gates, Pandoc → XeLaTeX-class engine). | `democreate.manuscript.build_manuscript` | `.venv/bin/python scripts/build_manuscript.py [--check]` |
| `benchmark.py` | Measure pipeline latency / render compute and write `data/benchmarks.json` (the source the evaluation prose is bound to). | `democreate.pipeline` / `narration` backends (bench harness in `democreate` calls) | `.venv/bin/python scripts/benchmark.py` |

`__init__.py` makes `scripts/` importable for the scripts-smoke test
(`tests/test_scripts_smoke.py`), which imports each script to guard against syntax
or import drift.
