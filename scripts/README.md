# Scripts: standalone front doors and source-bound measurement tooling

Run these from the repository root with the selected project interpreter
(`.venv/bin/python scripts/<name>.py …`). Generation/manuscript wrappers delegate
to package modules; `benchmark.py` additionally owns timing/provenance collection.
They are not all CLI aliases or single-call wrappers. Core pin is Python 3.15;
optional Kokoro measurement needs a compatible voice environment (recorded as
Python 3.14) plus models. See [backend prerequisites](../docs/backends.md).

| Script | Purpose | Delegates to | Command |
|--------|---------|--------------|---------|
| `00_preflight.py` | Import core modules and report optional dependency presence; this does not certify backend readiness. | direct `democreate` imports + `importlib.util.find_spec` | `.venv/bin/python scripts/00_preflight.py` |
| `generate_demo.py` | Build one demo artifact end-to-end from a `.json`/`.yaml` demo into an output workspace. | `democreate.pipeline.build_demo` | `.venv/bin/python scripts/generate_demo.py demo.json --output output` |
| `generate_portfolio.py` | Render a timestamped summary video per project under a directory — the batch front door for `democreate portfolio`. | `democreate.portfolio.render_portfolio` | `.venv/bin/python scripts/generate_portfolio.py <projects_dir>` |
| `generate_api_docs.py` | Regenerate `docs/api.md` from the live package (a curated module list → public classes/functions). Re-run after the public API changes. | `democreate.api_docs.generate` | `.venv/bin/python scripts/generate_api_docs.py` |
| `build_manuscript.py` | Build the manuscript artifacts under `docs/manuscript/` (citation + figure gates, Pandoc → XeLaTeX-class engine). | `democreate.manuscript.build_manuscript` | `.venv/bin/python scripts/build_manuscript.py [--check]` |
| `benchmark.py` | Measure wall-clock build/render timing with raw samples and source/input/runtime/tool identities; `--output` selects the report destination. | `democreate.pipeline` / `narration` backends | `.venv/bin/python scripts/benchmark.py --output output/wfz/benchmarks-0.8.0.json` |

`tests/test_scripts_smoke.py` checks paper-showcase containment and benchmark
provenance. Native CI/release smokes exercise preflight and the CLI; these are not
claims that every script is imported or executed.
Portfolio defaults to `--max-modules 6`, rejects nonexistent/non-directory inputs,
and exits nonzero when no project renders (including empty/all-failed batches).
Benchmark `--output` defaults to `data/benchmarks.json` for compatibility. Governed
test runs must select an ignored `output/` destination to preserve tracked data;
the integration owner can subsequently add the identified measurement as distinct
`data/benchmarks-0.8.0.json`. Missing ffmpeg is recorded, not a successful render.
Encoded render throughput uses ffprobe's video-stream duration, measured outside
the timer; the planned timeline duration is retained as a separate field.

The benchmark identity hashes the complete runtime package tree (including
`export/templates/player.html.j2`, excluding bytecode caches), `pyproject.toml`,
`uv.lock`, this benchmark script and the generated starter input bytes. Its
`source_manifest` retains each included relative name, byte count and SHA-256;
no absolute user paths are stored in that manifest. A template-only change
therefore changes `source_sha256`, as does a change to the measured input.

API output is generated, not hand-edited. Its curated inventory/facade exports
must track the public source surface; a generated signature does not establish
adapter readiness. Existing benchmark/release records remain immutable observed
history, not verification of subsequent edits. The [documentation hub](../docs/README.md)
separates recipes, references and the [0.8.0 historical receipt](../docs/release-0.8.0.md).
