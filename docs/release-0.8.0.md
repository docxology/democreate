# 0.8.0 candidate — engineering receipt, publication blocked

Observed 2026-11-08 UTC. Base: `b85cefab7564d88090ef51039b889f3e9d35a723` plus the identified working-tree changes. Runtime/source hashes and bounded execution generations are retained in [the structured receipt](../data/release-0.8.0.json). The final Git SHA belongs to the publication receipt, not a self-referential hash embedded in this commit.

## Sharpened outcomes and acceptance

- Preserve authored inputs, authored timing and explicit compositor authority; resolve measured audio durations and scheduled visual state consistently.
- Confine generated files and staged assets; treat imported Demo/PDF/repository text as data, not shell/HTML authority.
- Prove actual core CLI, built-wheel, browser, PDF and voiced-video paths; distinguish unavailable adapters, synthetic controls and historical records.
- Synchronize candidate **0.8.0**, schema **1.1**, publication metadata and manuscript. No tag/release without the unchanged research gate and authorized release workflow.

Only this standalone repository and its owned `output/wfz/` development lane were changed. Existing external tools/interpreters were read or used without modifying them. No HumOS runtime dependency, sibling write, global configuration change, registry publication, user stash/reset/clean, or additional Herdr workspace was introduced.

## Confirmed fixes and changed contracts

- `schema.py`, `narration/sync.py`, `assembly/compositor.py`: measured chunk durations, authored versus derived timestamps, WAIT sequencing and zero-duration captured events survive synthesis/re-sync. Default word boundaries remain character-weighted estimates, not recognized acoustic onsets.
- `assembly/animator.py`, `pipeline.py`: scheduled replay preserves files, partial typing, terminal completion and motion; explicit compositor rasters survive animation. `Pipeline.run` clones input; consumers use `PipelineResult.demo`. Reusing an authored Demo in another workspace no longer leaks staged paths.
- `project_paths.py`, narration/audio and `codebase/walker.py`: opaque chunk IDs no longer become filenames; workspace/asset links and escaped repository reads are refused; assets are independently content-staged; missing/corrupt required images fail before rendering. Only current frame sequences are encoded.
- `export/video.py`: static subtitles are evaluated at output-frame cadence. Literal subtitle filenames survive both FFmpeg filter parsers. Animated/static caption enablement and clearing are exercised with decoded pixels.
- `export/interactive.py` and its template: hostile title/chapter/caption text remains inert; the initial paused image loads before the first cue; captions clear during silence/end. The HTML surface is a timed preview, not speech playback.
- Capture/browser/replay/asciicast conversion retains supported event parameters and validates input boundaries. PDF multi-dot names and abstract-heading extraction are repaired; portable controlled PDF fixtures replace private-machine dependencies. Invalid model responses raise instead of masquerading as successful translation.
- Model downloads publish completed files atomically without replacing a peer. Dependency presence is not adapter/model readiness; unwired backends do not advertise misleading install remedies. Unsigned poster hashes associate selected content, not authorship, cover pixels or video identity.
- Config loaders reject unknown fields. Removed high-level `video.typing_fraction`; author action durations instead. Schema 1.0 is rejected without a shim. Python floor is 3.11.5, Pillow floor 13; default fonts use Pillow's bundled resource. SDK metadata uses SPDX MIT and setuptools >=84.2.1.
- Manuscript/source claims, moved/incorrect references, historical evidence labels, version metadata and CI drift are corrected. Current timing uses probed encoded duration, not planned duration; distinct units no longer share a bar scale. Obsolete wording/default/wiring tests were removed rather than repinned.
- Hosted CI exposed legacy-reader incompatibility in FFmpeg's automatic WAV output. Normalization/fades now preserve PCM WAV sample rate/channels, stream raw PCM through bounded-memory copying, and atomically publish standard 16-bit WAV headers. Real tone regressions include 96 kHz and three-channel inputs; input bytes, duration, nonzero signal and fade attenuation are checked.

The named Workflowz audit and separate refutation pools covered all eight subsystems, the spine/config/CLI, data, dependencies/build/release, tests, documentation and manuscript. Defensive review assumed attacker-controlled artifacts/text/paths, not host credentials or privileged configuration. Generic shell/RCE/authentication accusations without a reproducible route were rejected. High-risk judgments were peer-checked and exercised; no independent external penetration test is claimed.

## Exercised verification

All subprocess gates used the inherited qualified bounded offline runner, with real repository/common-store admission, source-after checks and process-tree completion. Source edits and native Git publication use short repository leases. A declaration is not a passing receipt.

| Surface | Actual exercise and result |
|---|---|
| Full core gate | `.venv/bin/python -m pytest -q --cov=democreate --cov-report=term-missing --cov-report=json:output/wfz/coverage.json --cov-report=xml:output/wfz/coverage.xml`: **926 passed, 12 skipped**, configured line/branch total **90.47%** after the final refutation fixes. 1,166 designated lines excluded; this is not all-adapter coverage. |
| Lint/types | `.venv/bin/ruff check .`; `.venv/bin/mypy src`: passed, 66 source files. Mypy retains one existing untyped-constructor-body note; no stronger type-coverage claim. |
| Core-only distribution | Offline `uv build --no-build-isolation` from independent staging; wheel/sdist paths, metadata, template and archive containment inspected. A fresh Python 3.15.2 prefix installed locked core dependencies plus the wheel, outside the source checkout import path. Core preflight loaded no optional heavy modules. |
| Real consumers | Installed `init`, `inspect`, two `build --tts silent` runs, `thumbnail`, `gif`, and `stego --demo` against the emitted resolved bundle; script `generate_demo.py` and manuscript help. Every generated core file compared byte-for-byte: ten files, zero differences. |
| Video/captions | Real static/animated exports with/without subtitles; decoded cue/gap pixels and literal quote/comma/bracket/semicolon filename. Silent media correctly fails voiced-content verification. Real corrupt media data with valid container declarations fails closed. |
| Browser | Owned Chrome/CDP instance: initial frame, next/previous, gap/end caption clearing, hostile `</script><img ... onerror=...>` title. Literal text, no injected handler; actual screenshots retained. |
| PDF | Actual `paper ... --no-render --pages 1,2` over a controlled two-page synthetic PDF and real PNG inputs; exact abstract and staged backgrounds checked. Not an empirical research-paper result. |
| Manuscript | Native figure regeneration and `scripts/build_manuscript.py --check` plus XeLaTeX build: 28 used/32 defined citations, zero unresolved; 12 inserted/rendered figures. All 25 PDF pages rasterized and layout inspected, including current timing/montage and references. |
| Documentation | Markdown target check: no missing local file targets; native manuscript references checked separately. Generic Markdown anchors and every external HTTP link were not exhaustively validated. |
| Dependencies | Native lock regeneration; OSV exact-version query over 170 locked registry variants, zero advisory matches/no pagination at observation time. This is neither range-wide nor comprehensive security/authenticity assurance. |

Exact executable/tool/package versions, lock hashes, input bytes, source manifests, gate bounds and generations are in the structured receipt. Native commands ran on macOS arm64 with core Python **3.15.2**; the compatible voice environment used **3.14.10**. Existing FFmpeg-full **9.0.2** was selected only through process-local PATH.

### Canonical media, not a silent substitute

Actual command (relative paths shown):

```sh
output/wfz/voice-env/bin/python -m democreate.cli render \
  output/wfz/stage9/examples/democreate_showcase.json \
  -o output/wfz/canonical-stage9 --tts kokoro --voice af_heart \
  --resolution 2160p --author "Daniel Ari Friedman" \
  --watermark "github.com/docxology/democreate"
output/wfz/voice-env/bin/python -m democreate.cli verify \
  output/wfz/canonical-stage9/video/demo.mp4 --width 3840 --height 2160
```

The staged input matches the integrated example bytes. The final integrated result is 3840x2160 H.264/AAC at 15 fps, 159.867 s video / 159.905 s audio, mean volume -16.4 dB (not LUFS). MP4 SHA-256: `234d3d282f015a2cfa4de24eb7729ce19076c1147652ae8bf5693fff0c18efd4`. Fifteen caption cues and chapters, six newly decoded representative frames and the decoded audio signal were inspected. Raw, normalized and faded WAVs all retain 22,050 Hz mono/16-bit and 3,525,912 frames; post-processing actually ran, not the raw fallback. SRT/VTT are sidecars; this recipe does not burn them. No listening/intelligibility or independent event/word-onset evaluation was performed. Requested extraction seek offsets are not annotated frame/event timestamps.

### Reproducibility and timing limits

[The distinct benchmark](../data/benchmarks-0.8.0.json) retains all five samples, including the first timed build, and both measured video duration and planned timeline. It is one synthetic silent starter on one host, not the planned voiced corpus, a cold-process startup estimate, or evidence of improvement over the unbound historical aggregate. Same-environment core byte identity is not cross-host, optional-model or encoded-media byte determinism.

## Failures, skips and unexamined runtime surfaces

- The first full-suite collection found obsolete private compositor imports; a subsequent diagnostic run exposed old wording/fallback expectations. Callers/regressions were migrated without shims; old incidental tests were deleted. The corrected full coverage run passed. Initial benchmark proof instrumentation used a nonexistent workspace property, and the tar audit initially rejected the standard root-directory entry; both proof-driver errors were corrected against observed APIs/bytes, not hidden.
- The first hosted matrix run on `865dc3371f42212d54b191748c99cbc148f74acc` failed: Python 3.11 had three real render failures (`wave.Error: unknown format: 65534`), while 3.12–3.15 passed tests but missed coverage at 89.95% because Pandoc/crossref were absent. The WAV producer was repaired, and CI now installs a version-matched, upstream-digest-checked tool pair; the 90% threshold and tests were not relaxed. Native post-fix scoped proof passed 140 tests, and the full gate passed 921. [Hosted post-fix CI passed all five Python 3.11–3.15 jobs on `7e4d0e4`](https://github.com/docxology/democreate/actions/runs/42448902641).
- The separate post-CI refutation pool identified malformed-WAV error leakage and a benchmark crash when only `ffprobe` is absent. Real reproduction produced four failures and one already-passing boundary case. Both roots were corrected; final scoped/full gates passed. Standalone API/CLI smoke confirmed typed `RenderError`, unchanged source/prior output, and a retained partial benchmark report naming `ffprobe`; a real rejected FFmpeg filter also preserved prior output. Fresh timing retains the slower observed samples rather than selecting earlier faster runs.
- Stock FFmpeg lacked libass; an existing read-only full build was used. Native system TTS was unusable. Core Python 3.15 lacks a locked ONNX wheel; a separate compatible repository-local voice prefix was used, without changing the core pin.
- The 325 MB model exceeds the runner's 256 MiB per-seed limit. Its small manifest was sealed and runtime hashes matched before/after, but the model itself was not a kernel-protected seed. Supplier digests were unavailable: observed hashes are not publisher authentication.
- Nested Chrome's own sandbox failed under the qualified outer Seatbelt sandbox. Only the owned proof instance used `--no-sandbox`; the outer offline/Git-store/seed controls remained active. No user browser session or Herdr pane was commandeered.
- Twelve core-suite skips concern optional Manim/Playwright/Kokoro/system-voice paths, missing-binary guards while FFmpeg is present, and absent tracked output. Separate real Kokoro/Chrome proofs do not turn those unit-suite skips into passes.
- Real cloud-provider/LLM calls, live desktop/replay effects, Playwright capture, Manim/Whisper/Chatterbox implementations, and the optional external curated-paper video were not established. Unwired slots remain unavailable. Primary research references were spot-checked, not the entire bibliography independently authenticated. Default font glyph coverage and hostile same-UID filesystem replacement remain documented limits.

## Publication barrier

The unchanged blocking research criterion requires an independently annotated voiced corpus of at least 30 demos (at least ten per declared mode), with **both** pooled absolute event-error median and median of demo-level absolute error medians <=120 ms. Corpus, independent acoustic/visible-event evaluator and condition/baseline/ablation results are absent. Silence and estimated timestamps cannot satisfy it.

The observed configured identity is pinned `docxology`; the GitHub **release** write class is disabled. No settings change, invented confirmation, tag replacement or alternate ambient account is authorized. Live main rules prohibit deletion/non-fast-forward updates, not ordinary fast-forward integration. Engineering source can be committed/pushed without representing it as a release.

**Candidate 0.8.0 is not tagged or published.** The live established release remains [v0.6.2](https://github.com/docxology/democreate/releases/tag/v0.6.2), with its existing manuscript/wheel/source assets unchanged. Local candidate media, packages, PDF, receipts and environments remain repository-local under `output/wfz/`; they are not registry or repository-release uploads.
