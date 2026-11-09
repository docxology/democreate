# Runtime Observations, Annotation Scoring, and the Unmet Acoustic Study {#sec:evaluation}

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

The canonical package recipe remains **Kokoro `af_heart` at 2160p**. The 2026-11-09 native run reused repository-local Python 3.14.10 with an asserted import of current repository source and candidate version; the core pin remains 3.15. `data/showcase-2026-11-09.json` binds package Python bytes, authored Demo, background images, runtime and before/after model hashes to the verified 3840×2160 H.264/AAC output. The MP4 identity is `1b0bf706335d2465e85f91ec3f241b68acf1d68d38cef9566282d58fd25f52ff`; its 15-cue SRT/VTT windows agree. Six montage samples include the encoded evidence-boundary graphic, themes and explicitly illustrative code; an additional opening-title sample is retained. Earlier same-input byte equality remains a separate observation, not transferred to these changed inputs or generalized to neural-model determinism. Decoded audio signal and representative frames were inspected; no listening or independent word-onset annotation was performed. The local, unpublished MP4 does not replace the blocking study or certify later code edits.

![Six digest-checked decoded frames from the 2026-11-09 candidate package MP4, arranged in a 3×2 package-only montage. Encoded synthetic visuals include the evidence-boundary graphic, themes and explicitly illustrative code. Labels are requested cue-midpoint seeks, not annotated event or acoustic onsets. Input, frame and MP4 identities are in data/showcase-2026-11-09.json; sparse samples do not establish full-timeline quality or a paper-demo result.](figures/video_stills.png){#fig:video_stills}

## Supplied-Annotation Arithmetic Without Evidence Certification

`democreate score-sync` and `democreate.evaluation` score one declared fixed
engine/voice/capture cohort. Expected events are separate from observations;
missing onsets and whole failed demos remain explicit. Available pairs produce
per-event errors, per-demo medians, the pooled event median and the median of
demo medians. Both unrounded aggregates must meet the 120 ms bound, alongside
fixed-mode counts and declared eligibility. Undefined values remain null rather
than zero. Distinct event counts can make the two aggregates disagree.

Missing measurements cannot yield a passing complete-input report; this is not
a measured 100% success criterion. Synthetic regressions establish arithmetic
and error handling, not H1. Media identity, independence, predeclaration and
completeness beyond the supplied inventory remain unverified. Unavailable media
permit null identities/durations only with a failure reason. See
`docs/evaluation.md` for the input/exit contract.

## Blocking Study: Independent Voiced-Event Annotation and Both Medians

`experiment_plan.yaml` remains prospective. Its independently annotated **voiced, animated** corpus is **PLANNED** and blocking: at least 30 demos, with at least 10 each for codebase, website and terminal modes. Both pooled event-error median and median of demo-level error medians must be ≤120 ms; one weighting cannot substitute for the other. Annotators must identify actual encoded visible-event onsets and independent acoustic trigger-word onsets, retain media identities and uncertainty, and account for frame cadence. Silent WAVs contain no spoken words and are ineligible. Supplied-annotation arithmetic is implemented, but no independent corpus/onset measurements, empirical condition comparison, baseline or ablation result is supplied. Timestamp completeness, monotonicity and a non-silent MP4 cannot confirm those hypotheses. Silent-default reproducibility is a separate fixed-input/assets/configuration/environment check. Operator-controlled release-class enablement and frozen-plan/exact confirmation are separate requirements; engineering gates waive neither permission nor the unmet scientific criterion.
