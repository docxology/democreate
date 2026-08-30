# AGENTS.md — scripts/

Thin, runnable front doors over the `democreate` library (see `README.md`
here for the script table).

- **No business logic in scripts.** Each script parses args and calls into the
  package; behavior stays testable in the library and identical to the CLI.
- Run through the project venv: `.venv/bin/python scripts/<name>.py …` — a bare
  `python` may resolve to a shim outside the project env.
- `__init__.py` makes `scripts/` importable for `tests/test_scripts_smoke.py`,
  which imports every script to guard against syntax/import drift. A new
  script must import cleanly (and ideally be pure-argparse over library calls)
  or that test fails.
- `00_preflight.py` is the diagnostic entry point: it reports which optional
  backend extras (kokoro, whisper, mss, playwright, manim, moviepy,
  tree-sitter, pynput) are installed. Use it before debugging a backend path.
- `benchmark.py` writes `data/benchmarks.json` — the source the manuscript's
  evaluation prose is bound to; treat changes to that file as claim-affecting.

This tree is LOCAL-ONLY (under `projects/ongoing/…` — never commit; see the
template root `AGENTS.md` and `projects/ongoing/AGENTS.md`).
