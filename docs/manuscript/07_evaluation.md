# Evaluation: Source-Bound Observations and Blocking Acoustic Study {#sec:evaluation}

## Unbound Historical Timing and Its Measurement Boundaries

`data/benchmarks.json` retains a historical aggregate record reviewed on 2026-11-07. Its original measurement date, source revision, host, tool versions and raw samples were not recorded; it is not evidence of current 0.8.0 performance. The distinct source-bound engineering observation is retained in `data/benchmarks-0.8.0.json`; neither record is evidence for later source edits, and the old record is not overwritten.

| Historical metric | Recorded value | Actual timing boundary |
|---|---|---|
| Build, median of five runs | 25.8 ms | `build_demo`: validation, TTS, synchronization, frames and exports; starter construction is outside the timer. |
| Animated render | 256.7 ms per planned timeline second at 15 fps | Entire `render_video(..., verify=False)` call, including voiceover processing, animation, encoding and sidecars; 1981.9 ms divided by the reported 7.72-second timeline, not an independently probed video-stream duration. |
| Timestamp structure | Three of three actions timestamped, monotonic | Silent-audio heuristic sanity check, not measured acoustic accuracy. |

: Historical aggregate measurements; different units must not be interpreted as a common latency scale. {#tbl:bench}

25.8 ms is **greater** than the 16.7 ms interval of a 60 fps display, not faster than one display frame. The render figure is wall-clock throughput, not isolated compositing compute. Neither quantity predicts another host, dependency set, resolution or voiced render.

## Source-Bound Silent Starter: Build and Whole-Render Timing

The 2026-11-08 record retains the exact starter input, runtime-package/resources manifest, lock, interpreter, installed packages, tool versions and raw samples. It is a synthetic **silent** starter at 1920×1080, not a voiced corpus or a neural-TTS benchmark. Five consecutive build samples include the first timed build; process imports and input construction are outside the timer. The median is not a cold-process startup estimate.

The current record was re-measured after the final PCM/error-boundary and
missing-probe corrections. Earlier candidate raw samples remain under
`prior_candidate_records`; these are retained observations, not a controlled
before/after performance comparison.

![Source-bound silent-starter timing shown as independent cards with separate units. Whole-render throughput uses ffprobe's measured video-stream duration outside the timer; the planned timeline is retained separately. The record in data/benchmarks-0.8.0.json is host/source-specific, not a compatible historical comparison, performance-improvement claim or measurement of a subsequently edited tree.](figures/latency.png){#fig:latency}

## Core Coverage and Engineering Receipts, Not Acoustic Evidence

The real-filesystem test suite exercises schema round-trips, rendering, narration, synchronization, captions, exports and optional adapter boundaries. `pyproject.toml` defines a ≥90% core coverage gate. A fresh run supplies the result; no current coverage percentage or test count is asserted here. Coverage and default-path tests do not establish optional backend availability or empirical media quality.

`domain_profile.yaml` lists executable engineering checks. A declaration is not a passing receipt. Locked-environment checks and latest-compatible dependency CI answer different questions; release readiness also requires built-distribution, manuscript and actual voiced-video checks where their prerequisites are present.

## Structural Media Checks Versus Perceptual and Scientific Quality

The verifier checks stream geometry and duration, an audio/video duration ratio, mean audio volume, and sampled picture variance. These are structural/content-presence checks, not speech recognition, intelligibility, intended-scene identity or human quality evaluation. Mean volume in dB is **not integrated loudness in LUFS**.

Unsigned poster payloads associate a content digest with a Demo ([@sec:provenance]); they do not authenticate authorship, bind video or cover pixels, or resist an adversary who can recompute the record.

## Identified Package MP4, Cue Sidecars, and Decoded Still Samples

The historical template-paper run and distinct curated showcase are described in [@sec:paper]. Earlier documentation also recorded a 3840×2160, 155.6-second package showcase; that record alone does not identify or verify a 0.8.0 output.

The canonical package recipe remains **Kokoro `af_heart` at 2160p**. Its recorded 2026-11-08 candidate run used Python 3.14.10 and local model/voices assets, while the core pin remains 3.15. The source-bound `data/release-0.8.0.json` identifies a structurally verified 3840×2160 H.264/AAC result, 15-cue SRT/VTT sidecars, six decoded stills and MP4 SHA-256 `234d3d282f015a2cfa4de24eb7729ce19076c1147652ae8bf5693fff0c18efd4`. Sidecar cues and the decoded audio signal were inspected; no listening or independent word-onset annotation was performed. The local, unpublished video is an observation tied to its recorded source and assets, not proof of a later edited tree or a substitute for the blocking study.

![Six digest-checked decoded frames from the identified candidate package MP4, arranged in a 3×2 package-only montage. Labels are recorded requested seek offsets at cue midpoints, not annotated event or acoustic onsets. Input paths, frame hashes and MP4 identity are retained in data/release-0.8.0.json; these sparse samples do not establish full-timeline quality or a paper-demo result.](figures/video_stills.png){#fig:video_stills}

## Blocking Study: Independent Voiced-Event Annotation and Both Medians

`experiment_plan.yaml` is the prospective protocol, not an executed result. Its independently annotated **voiced, animated** corpus remains **PLANNED** and blocking: at least 30 demos, with at least 10 each for codebase, website and terminal modes. Both the pooled event-error median and the median of demo-level error medians must be ≤120 ms; one weighting cannot substitute for the other. Annotators must identify actual encoded visible-event onsets and independent acoustic trigger-word onsets, retain media identities and annotation uncertainty, and account for frame cadence. Silent WAVs are ineligible because they contain no spoken words. No independent acoustic/visible-event corpus, executable acoustic evaluator, condition comparison, baseline or ablation result is supplied. Timestamp completeness, monotonicity and a non-silent MP4 cannot confirm those hypotheses. Silent-default reproducibility is a separate fixed-input/assets/configuration/environment engineering check. The configured GitHub release class remains disabled; engineering gates do not waive this research criterion.
