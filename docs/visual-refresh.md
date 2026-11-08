# Visual refresh: corrected contracts, native proof and publication limits

Candidate **0.8.0**, schema **1.1**; no tag or release is asserted here.
This continuation starts at `a16aab0917da1c4f165b6db4905d10d14b507444`.
The [structured observation](../data/visual-refresh-2026-11-08.json) records
implementation epoch `e04e2d01868a6a03ec7a530702632ec5f0855839` plus the actual
dirty final native snapshot, including the callable-default correction. Later
documentation commits are not represented as already executed. Its 66-file
package fingerprint permits byte comparison without treating a Git version as
proof; dependencies, assets and configuration require separate records.
Hashes are unsigned. Earlier core/media epochs remain explicitly identified.

## Verified defects and consumer-visible corrections

| Boundary | Confirmed failure | Correction and regression |
|---|---|---|
| Localized captions | Authored 5000/9000 ms windows survived measured audio and pacing | Both sidecars use `PipelineResult.demo`; real WAV/FFmpeg regression expects 125–525 and 800–2000 ms |
| Borrowed input | Same-language caption generation mutated the caller's authored Demo | Copy only the aliased input before synchronization; serialized authored and timing inputs remain unchanged |
| API reference | CommonMark fragment links broke; classmethod factories were omitted | Plain module headings, bound-classmethod discovery, 49-module inventory and parsed-link/public-factory regressions |
| API determinism | Callable defaults serialized process addresses, so separate runs changed the reference | Qualified function symbols; retained old source reproduces the difference, fresh-process regression verifies equality after correction |
| Synthetic typing | Multiple revealed/unreached rows received carets | One active caret; real pixel-difference checks cover zero, row boundary, partial and saturated character counts |
| Manuscript output | Relative PDF path was resolved after Pandoc changed directory | Resolve caller-relative input/output before launching Pandoc; real relative-output CI build |
| Page trim | Long paper-render shell command clipped at the page boundary | Real shell continuations; informative, shorter related-work title |

`LocalizedResult.ok` means rendering succeeded and verification passed **when
requested**. A produced path can remain after verification fails; unverified
results report no verifier duration. No schema, result fields or compatibility
shim were added for that documentation correction.

## Graphical and documentation changes

- Bounded shared figure layout rejects overflowing text instead of dropping it.
  Cover labels are larger; architecture, extraction and unsigned-attribution
  diagrams distinguish mechanisms from empirical findings.
- Complete current timing-method source accompanies synthetic character-count
  previews. Historical throughput/build observations retain their original
  source, units and limitations; no improvement claim is inferred.
- The gallery no longer invents a specific 170-page paper or shows nonexistent
  public APIs. Its title, diagram and typing states identify synthetic provenance.
- The showcase now stages the refreshed cover/theme PNGs and names its schematic
  code panels `illustrative_*.py`; source-looking filenames no longer imply a
  captured repository excerpt. Its new MP4 has a distinct input/output identity.
- [Workflow/reference/evidence navigation](README.md), subsystem README/AGENTS
  pairs and [manuscript chapter ownership](manuscript/README.md) have distinct
  responsibilities. Stable manuscript section/figure identifiers are preserved.
- CI retains source/hash/runtime-bound graphical and full-manuscript outputs,
  including failed-stage outcomes. Its generated-file gate rejects stale PNG/API
  output; an artifact inventory alone is not regeneration proof.

## Exercised native commands and source binding

The operator used the inherited **qualified bounded offline test runner**, not a
checkpoint exception or an unknown-duration canonical lease. Source before/after
matched; the successful integrated run had a 1500-second hard bound and no
remaining descendants. Initial maintenance and stale-configuration refusals
launched no tests; they remain in local evidence, not disguised as code failures.

The successful current-code run exercised:

```bash
.venv/bin/python scripts/00_preflight.py
.venv/bin/ruff check .
.venv/bin/mypy src
.venv/bin/python -m pytest -q --cov=democreate --cov-report=term-missing \
  --cov-report=json:output/visual-refresh/coverage-policy-final.json
.venv/bin/python -m democreate.cli init output/visual-refresh/starter-final.json
.venv/bin/python -m democreate.cli inspect output/visual-refresh/starter-final.json
.venv/bin/python -m democreate.cli build output/visual-refresh/starter-final.json \
  -o output/visual-refresh/core-final --tts silent
```

Final native Python 3.15.2 core proof: **931 passed, 11 skipped; 90.88% configured
combined line/branch coverage**. The obsolete tracked-video positive control was
removed; the publication guard now rejects both generated-workspace trees and
fails on unavailable Git reads. The structured receipt retains the earlier
12-skip epoch separately. Two skips are inapplicable missing-FFmpeg guards;
the remaining nine are absent optional browser, Manim or voice prerequisites.
Kokoro was exercised separately in the identified compatible voice environment.
Designated heavy paths remain excluded. Ruff passed; mypy found no issues in
66 source files, retaining its existing `annotation-unchecked` note.
Core preflight passed without optional voice/browser/heavy packages.
The preceding `init`/`inspect`/silent `build` and refreshed voiced render remain
bound to their own receipt and the same package-Python file inventory.
Hosted Python 3.11–3.15 jobs at
[e04e2d0](https://github.com/docxology/democreate/actions/runs/42526969203)
passed. Its visual generation/localization/full PDF stages passed; freshness
correctly failed on native/hosted PNG bytes and the process-address API bug.
That failed run is not a passing final publication gate.

The retained pre-fix source produced different API files in two fresh native
interpreters. After correction, the independent-process regression passed.
Two sampled PNGs (cover and synthetic waveform) had equal decoded pixels but
different encoded bytes; no encoder cause or general cross-host guarantee is
inferred. Canonical hosted visual bytes were inspected, hash-checked and used as
the final voiced render's inputs.

## Fresh canonical speech, captions, frames and audio signal

The existing repository-local Python **3.14.10** voice environment and local
Kokoro assets were reused, without changing the 3.15 core pin or reinstalling
packages. Process-local source selection and an import assertion proved that
this render loaded this repository's current `src/democreate`, not an old
editable checkout. The actual CLI render selected `--tts kokoro --voice af_heart
--resolution 2160p`, followed by `verify --width 3840 --height 2160`.

Observed H.264/AAC: **3840×2160**, 15 fps, 159.867-second video and
159.905-second audio, 15 chapters and 15 agreeing SRT/VTT cues. MP4 SHA-256:

```text
61fbcb84681f5cf20678c905c12004e59af8d20edcf9153b85f2598801ca16d4
```

The refreshed showcase uses the new cover/theme images and illustrative code
labels. Four changed decoded samples have new retained paths; two unchanged
samples reuse their earlier files. The six-frame montage includes the encoded
cover, theme comparison and illustrative timing panel. Its record binds authored
Demo, background PNGs, current package bytes, models, cues and MP4.

An earlier source epoch reproduced the [original identified MP4](release-0.8.0.md)
before those inputs changed. That observation remains under
`canonical_before_showcase_refresh`; it is not transferred to the new video or
generalized to neural-model determinism. Raw/normalized/faded WAVs retained mono
22050 Hz 16-bit PCM geometry and duration. Decoded amplitude and representative
frames were inspected; no listening, intelligibility assessment or independent
acoustic-onset annotation occurred. Requested seeks are not exact decoded PTS;
six samples do not prove every frame's quality. The 325 MB model was manually
hash-checked before/after, not kernel-seed protected or supplier-authenticated.
The MP4 remains local/unpublished.

## Defensive review, non-runs and release blockers

Separate agent implementation/refutation lenses covered ownership/timing, API
navigation, manuscript layout/evidence and publication/pruning custody. All 26
pages of the frozen staged PDF were inspected independently; that verdict does
not approve unseen later pages or media.
The adversary is an ordinary Demo author/library consumer or skeptical reader,
not a host administrator. Source-backed findings were reproduced or linked to
actual failures; rejected findings were not converted into speculative fixes.
Publication helpers require fresh green branch checks, exact reviewed commit and
an ordinary fast-forward. Pruning first preserves and verifies all local refs,
including unique removed-upstream history; unrelated work is not expendable.

No optional Whisper/Chatterbox/Manim/MoviePy implementation, external curated
paper video, exhaustive frame review, new performance benchmark, listening study
or acoustic evaluator was run. Local Markdown file/fragment checks are separate
from live external-HTTP link checks. Immutable older receipts and old benchmark
observations were intentionally not repinned.

The pre-existing **≥30 independently annotated voiced demos, ≥10 per eligible
mode**, with both required error medians ≤120 ms, remains unavailable/unmet.
`experiment_plan.yaml` is prospective; engineering tests and non-silent audio do
not satisfy it. Operator-controlled write classes changed during this work:
release enablement was observed on revision
`a12de23f5d4bc3f4278fbd2b583aa645dc4f1ef1dbcfcd91ce4c6fa40f3522eb`,
then release and repository-metadata classes were absent on the later recorded
policy observation. These observations never grant permission or waive the study
and exact frozen-plan confirmation. Inaccurate live About text is explicit drift,
not silently bypassed. Only **v0.6.2** is an observed published release. No new
tag, release DOI, publication readiness or release asset is claimed. Final
main/CI and safe-pruning outcomes are independently checked and retained in
repository-local completion receipts.
