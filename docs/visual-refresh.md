# Visual refresh: corrected contracts, native proof and publication limits

Candidate **0.8.0**, schema **1.1**; no tag or release is asserted here.
This continuation starts at `a16aab0917da1c4f165b6db4905d10d14b507444`.
The [structured observation](../data/visual-refresh-2026-11-08.json) records
implementation epoch `f62af4e48ffc2d1be7057e53ee2d218c7b30be60` plus its actual
dirty snapshot, rather than pretending a later documentation commit was already
executed. Its 66-file Python-package fingerprint permits exact byte comparison
without treating a Git version string as proof. It excludes dependency, asset and
configuration identity; those require their separate records. Hashes are unsigned.

## Verified defects and consumer-visible corrections

| Boundary | Confirmed failure | Correction and regression |
|---|---|---|
| Localized captions | Authored 5000/9000 ms windows survived measured audio and pacing | Both sidecars use `PipelineResult.demo`; real WAV/FFmpeg regression expects 125–525 and 800–2000 ms |
| Borrowed input | Same-language caption generation mutated the caller's authored Demo | Copy only the aliased input before synchronization; serialized authored and timing inputs remain unchanged |
| API reference | CommonMark fragment links broke; classmethod factories were omitted | Plain module headings, bound-classmethod discovery, 49-module inventory and parsed-link/public-factory regressions |
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
.venv/bin/python -m pytest -q --cov=democreate --cov-report=term-missing
.venv/bin/python -m democreate.cli init output/visual-refresh/starter-current.json
.venv/bin/python -m democreate.cli inspect output/visual-refresh/starter-current.json
.venv/bin/python -m democreate.cli build output/visual-refresh/starter-current.json \
  -o output/visual-refresh/core-current --tts silent
```

Observed Python 3.15.2: **932 passed, 12 skipped; 90.87% configured combined
line/branch coverage**. Designated heavy paths remain excluded. Ruff passed;
mypy reported no issues in 66 source files and retained its existing
`annotation-unchecked` note. Core preflight imported successfully with optional
voice/browser/heavy packages absent. Hosted Python 3.11–3.15 jobs at
[f62af4e](https://github.com/docxology/democreate/actions/runs/42521703843)
passed; that run correctly failed the separate generated-file freshness gate
before its five regenerated files were integrated.

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
234d3d282f015a2cfa4de24eb7729ce19076c1147652ae8bf5693fff0c18efd4
```

This fresh output and six decoded cue-midpoint frames are byte-identical to the
[earlier identified run](release-0.8.0.md). Original committed frames were retained,
not duplicated or relabeled as synthetic output. Their digest-checked montage
uses the fresh receipt. This demonstrates the two recorded outputs' equality in
the available environment, **not general neural-model or cross-host determinism**.
Raw/normalized/faded WAVs retained mono 22050 Hz 16-bit PCM geometry and duration.
Decoded audio amplitude and representative frames were inspected; no listening,
intelligibility assessment or independent acoustic-onset annotation was performed.
Requested seek offsets are not exact decoded PTS. Six samples do not prove every
frame's quality. The 325 MB model was hash-checked before/after, not kernel-seed
protected or supplier-authenticated. The MP4 remains local/unpublished.

## Defensive review, non-runs and release blockers

Independent implementation/refutation lenses covered runtime ownership/timing,
API navigation, manuscript layout/evidence and publication/pruning custody.
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
not satisfy it. On the recorded configuration revision, GitHub release and
repository-metadata write classes are disabled; the live About text therefore
remains an explicit metadata drift, not silently bypassed. Only **v0.6.2** is an
observed published release. No new tag, release DOI, publication readiness or
release asset is claimed. Main/CI and safe-pruning outcomes are independently
checked at publication and retained in repository-local completion receipts.
