# `scripts/`

Thin, runnable front doors over the `democreate` library. Each script carries no
business logic of its own — it parses arguments and calls into the package — so
the behavior stays testable in the library and identical to the CLI. Run them
through the project venv (`.venv/bin/python scripts/<name>.py …`).

| Script | Purpose |
|--------|---------|
| `00_preflight.py` | Environment preflight — checks the venv, core imports, and which optional backends/binaries (ffmpeg, poppler, system voice) are available. |
| `generate_demo.py` | Build one demo artifact end-to-end (`build_demo`) from a `.json`/`.yaml` demo into an output workspace. |
| `generate_portfolio.py` | Render a timestamped summary video per project under a directory (`democreate.portfolio.render_portfolio`) — the batch front door for `democreate portfolio`. |
| `generate_api_docs.py` | Regenerate `docs/api.md` from the live package (a curated module list → public classes/functions). Re-run after the public API changes. |
| `build_manuscript.py` | Build the manuscript artifacts under `manuscript/`. |
| `benchmark.py` | Measure pipeline latency / render compute and write `data/benchmarks.json` (the source the evaluation prose is bound to). |

`__init__.py` makes `scripts/` importable for the scripts-smoke test
(`tests/test_scripts_smoke.py`), which imports each script to guard against syntax
or import drift.
