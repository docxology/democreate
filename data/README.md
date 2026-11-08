# Data and claim evidence — candidate 0.8.0

`claim_ledger.yaml` registers structured claims, values and evidence references.
Statuses distinguish assertions, estimates, planned studies and historical
reports; only a specific current passing run receipt can support `verified`.
Structured tests validate required fields and gate/metric/condition references;
they do not execute the studies or authenticate media.

`benchmarks.json` remains a historical aggregate record. Its original source,
runtime, tool identity and raw samples are absent; it is not current performance
evidence. Preserve it; the integration owner records fresh measurements separately:

```bash
.venv/bin/python scripts/benchmark.py --output output/wfz/benchmarks-0.8.0.json
```

The observed 2026-11-08 run is integrated as `benchmarks-0.8.0.json`, distinct
from the historical aggregate. No direct comparison is implied. The default
output remains `data/benchmarks.json`; pass `--output` explicitly to avoid
changing tracked data during governed test runs.

The harness records raw build timing samples, source/input SHA-256 identities,
geometry, runtime/package/tool identities, and accurate wall-clock boundaries.
SHA-256 identifies recorded bytes for comparison, not an authenticated author.
Build excludes starter construction and includes validation/TTS/sync/frames/exports.
Render covers the full `render_video(..., verify=False)` call, not isolated
compositing compute. Silent-audio timestamp sanity is not acoustic accuracy.

The ≥30-demo independently annotated corpus, ≤120 ms median-error hypothesis,
condition comparisons, baselines and ablations remain **PLANNED**, separate from
engineering release checks in `domain_profile.yaml`.

`release-0.8.0.json` records exercised engineering gates, source bindings, the
actual Kokoro candidate MP4 identity, decoded-frame hashes, toolchain, core-only
byte comparison, coverage exclusions and explicit publication blockers. It is
not an authenticated signature, a passing acoustic study or a release record.
Decoded frame times are requested ffmpeg seek offsets, not independently
annotated presentation/event onsets.
