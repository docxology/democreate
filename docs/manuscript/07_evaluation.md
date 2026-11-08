# Evaluation: Historical Measurements and Engineering Gates {#sec:evaluation}

## Historical Timing Record

`data/benchmarks.json` retains a historical aggregate record reviewed on 2026-11-07. Its original measurement date, source revision, host, tool versions and raw samples were not recorded; it is not evidence of current 0.8.0 performance. The distinct current engineering observation is retained in `data/benchmarks-0.8.0.json`; the old record is not overwritten.

| Historical metric | Recorded value | Actual timing boundary |
|---|---|---|
| Build, median of five runs | 25.8 ms | `build_demo`: validation, TTS, synchronization, frames and exports; starter construction is outside the timer. |
| Animated render | 256.7 ms per planned timeline second at 15 fps | Entire `render_video(..., verify=False)` call, including voiceover processing, animation, encoding and sidecars; 1981.9 ms divided by the reported 7.72-second timeline, not an independently probed video-stream duration. |
| Timestamp structure | Three of three actions timestamped, monotonic | Silent-audio heuristic sanity check, not measured acoustic accuracy. |

: Historical aggregate measurements; different units must not be interpreted as a common latency scale. {#tbl:bench}

25.8 ms is **greater** than the 16.7 ms interval of a 60 fps display, not faster than one display frame. The render figure is wall-clock throughput, not isolated compositing compute. Neither quantity predicts another host, dependency set, resolution or voiced render.

## Source-Bound Starter Observation

The 2026-11-08 record retains the exact starter input, runtime-package/resources manifest, lock, interpreter, installed packages, tool versions and raw samples. It is a synthetic **silent** starter at 1920×1080, not a voiced corpus or a neural-TTS benchmark. Five consecutive build samples include the first timed build; process imports and input construction are outside the timer. The median is not a cold-process startup estimate.

![Current starter timing shown as independent cards, not dimensionally incompatible bars on one axis. Whole-render throughput uses ffprobe's measured video-stream duration outside the timer; the planned timeline is retained separately. These host-specific observations provide no compatible historical comparison or performance-improvement claim.](figures/latency.png){#fig:latency}

## Engineering Gates, Not Suite-Size Claims

The real-filesystem test suite exercises schema round-trips, rendering, narration, synchronization, captions, exports and optional adapter boundaries. `pyproject.toml` defines a ≥90% core coverage gate. A fresh run supplies the result; no current coverage percentage or test count is asserted here. Coverage and default-path tests do not establish optional backend availability or empirical media quality.

`domain_profile.yaml` lists executable engineering checks. A declaration is not a passing receipt. Locked-environment checks and latest-compatible dependency CI answer different questions; release readiness also requires built-distribution, manuscript and actual voiced-video checks where their prerequisites are present.

## Media Verification and Its Limits

The verifier checks stream geometry and duration, an audio/video duration ratio, mean audio volume, and sampled picture variance. These are structural/content-presence checks, not speech recognition, intelligibility, intended-scene identity or human quality evaluation. Mean volume in dB is **not integrated loudness in LUFS**.

Unsigned poster payloads associate a content digest with a Demo ([@sec:provenance]); they do not authenticate authorship, bind video or cover pixels, or resist an adversary who can recompute the record.

## Candidate Media and Historical Limits

Earlier documentation recorded a 3840×2160, 155.6-second package showcase and a distinct 1920×1080, 188.0-second template paper demo. Those records are historical, not verified 0.8.0 outputs. The curated paper showcase is a separate artifact with separate inputs; its approximately 168-second record must not be assigned to the template demo.

The canonical package recipe remains **Kokoro `af_heart` at 2160p**. Its 2026-11-08 candidate run used Python 3.14.10 and local model/voices assets, while the core pin remains 3.15. The source-bound `data/release-0.8.0.json` records a structurally verified 3840×2160 H.264/AAC result and the exact source-video digest. Its SRT/VTT cues and decoded audio signal were inspected; no listening or independent word-onset annotation was performed. The video is local and unpublished, not a substitute for the blocking empirical study.

![Six digest-checked decoded frames from the identified candidate package MP4, sampled at recorded cue midpoints. This is a package-only montage, not a paper-demo result or a full-timeline quality/acoustic evaluation. Input paths, frame hashes, source receipt and MP4 digest are retained in data/release-0.8.0.json.](figures/video_stills.png){#fig:video_stills}

## Planned Empirical Study

The ≥30-demo independently annotated voiced corpus remains **PLANNED** and blocking. Both the pooled event-error median and the median of demo-level error medians must be ≤120 ms under `experiment_plan.yaml`; one aggregate cannot substitute for the other. Silent WAVs are ineligible because they contain no spoken words. No independent acoustic/visible-event corpus, evaluator, condition comparison, baseline or ablation result is present. Timestamp completeness, monotonicity and a non-silent MP4 cannot confirm those hypotheses. Silent-default reproducibility is a separate fixed-input/environment engineering check.
