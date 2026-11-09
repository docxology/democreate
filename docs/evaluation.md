# Annotation scoring: two medians, missing data and unverified evidence

`democreate score-sync ANNOTATIONS.json` scores supplied onset annotations. It
neither detects acoustic/visual onsets nor verifies media, annotator independence
or inventory predeclaration. **No empirical corpus or passing study is bundled.**
The unchanged research gate in [`domain_profile.yaml`](../domain_profile.yaml)
remains pending; [`experiment_plan.yaml`](../experiment_plan.yaml) owns the
prospective scientific criteria.

## Run the complete missing-data example

```bash
democreate score-sync examples/sync_annotations_missing.json
```

Expected exit **1**: this working negative control declares one intended event,
no rendered media and no measurements. Its medians are `null`, never zero.
It is an annotation-format walkthrough, not a Demo artifact or research datum.

| Exit | Meaning | Output |
|---|---|---|
| 0 | All checks on the supplied declarations pass | Diagnostic JSON on stdout; independence/media remain unverified |
| 1 | Well-formed input does not meet those checks | Diagnostic JSON on stdout, retaining missing/failed rows |
| 2 | Malformed/unreadable input | Error JSON on stderr; no successful report |

Library entry points are `democreate.evaluation.score_sync_annotations(document)`
and `load_sync_annotations(Path(...))`. `SyncEvaluation.to_dict()` produces the
same report shape. See the [generated API](api.md) for signatures.

## Declare one fixed condition, not a pooled best case

Annotation format **`"1"`** is independent of **Demo schema 1.1**. Top-level fields
are required; unknown fields and duplicate JSON keys are errors.

| Field | Contract |
|---|---|
| `annotation_version` | String `"1"` |
| `condition` | `default`, `voiced_heuristic` or `high_fidelity` |
| `tts_backend`, `voice` | Nonempty fixed engine/voice declarations |
| `animation` | `scheduled` or `static` |
| `website_capture` | `synthetic` or `real`; score these strata separately |
| `annotation_method` | `independent_manual` is the eligible declared method; the tool cannot verify it |
| `timebase` | `encoded_video_ms`: zero-based milliseconds from the first presented video timestamp, shared by both onset tracks |
| `inventory_ref`, `annotation_ref` | Nonempty opaque provenance references, never opened or fetched |
| `demos` | Array of every declared demo, including failures |

Only scheduled `voiced_heuristic` cohorts with declared system/Kokoro TTS and
`independent_manual` annotations are eligible for H1 checks. Other conditions
retain available arithmetic diagnostics but cannot pass eligibility. A silent
or `default` cohort must use `null` acoustic onsets: silence has no spoken onset.
Installing Whisper does not make the future `high_fidelity` condition runnable.

A demo may repeat cohort fields only with exactly matching values. Mixed engines,
voices, conditions or website-capture strata are rejected rather than silently
pooled. This scorer handles one fixed cohort per input, not every planned
baseline, ablation or multi-voice experiment.

## Keep expected events separate from observed successes

Each demo requires `id`, `mode`, `audio_sha256`, `video_sha256`, `fps`,
`duration_ms`, `expected_events` and `observations`. Modes are fixed to
`codebase`, `website`, and `terminal`. IDs and declared video digests must be
unique; duplicate bytes cannot be counted twice merely by renaming a demo.
Audio digests may repeat. Digests are 64 hexadecimal characters, not signatures.

For available media, FPS and duration must be finite and positive. An unavailable
media identity, FPS or duration may be `null` **only with `failure_reason`**;
that row cannot supply encoded-video onset observations. Keep the expected events
and use an empty observation array. Never fabricate a digest or duration to make
a failed render fit the format. Multiple unavailable videos need no fake unique
hashes.

| Record | Required fields |
|---|---|
| Expected event | `scene_id`, `chunk_id`, nonnegative integer `action_index`, `trigger_ref` identifying the intended token occurrence |
| Observation | The same three-key event identity, `acoustic_onset_ms`, `visual_onset_ms`, `uncertainty_ms` |

Expected events must come from the independently referenced inventory, not be
constructed from successful observation rows. Duplicate expected/observed keys
and observations outside that inventory are errors. An observation may add an
opaque `adjudication_ref`; retain disagreement/adjudication records externally.

Onsets are finite, nonnegative and strictly before the encoded video's duration.
Use the same zero origin for audio and video, retaining configured lead/gaps;
normalize nonzero container timestamps consistently before entering measurements.
Either onset may be `null`; a missing row also remains a missing event. Complete
pairs require finite nonnegative `uncertainty_ms`. Booleans, NaN/infinity and
out-of-range values are not measurements. FPS/uncertainty are reported, not turned
into an invented minimum-FPS or maximum-uncertainty acceptance threshold.
Numeric fields use binary64 arithmetic. Integer inputs must convert losslessly;
otherwise validation fails rather than silently changing a threshold decision.
JSON floating-point literals are interpreted with Python's binary64 precision.

## Read arithmetic, eligibility and accounting separately

For each complete pair, absolute error is `abs(visual - acoustic)` in ms. The
report retains every expected event, missing onset, failure reason, per-demo
median and unrounded aggregate. An undefined median or coverage is `null`.

| Check | Supplied-data requirement |
|---|---|
| Numeric thresholds | Both pooled event median **and** median of demo-level medians exist and are <=120 ms, without display rounding |
| Corpus counts | >=30 distinct demos; >=10 demos with scored pairs in **each** fixed mode |
| Declared eligibility | The fixed scheduled voiced-heuristic condition described above |
| Complete accounting | No empty expected inventory, missing onset pair or explicitly failed demo |

A partial cohort still reports medians from available pairs and explicit coverage;
it does not silently relabel partial arithmetic as a passing complete input.
Complete accounting is a tooling safeguard against missing denominators, not a
new claim that the prospective scientific protocol specified a 100% event-success
threshold. Unequal event counts can make the two medians disagree; neither may
substitute for the other.

`criteria_met_for_supplied_annotations` combines these checks. Even when true,
`evidence_verification` remains `not_verified`: the tool has not checked media
bytes, annotator independence, predeclaration or completeness beyond the supplied
inventory. It provides neither `study_verified` nor `release_ready` authority.
Synthetic regression fixtures prove arithmetic and error handling, not the
planned experiment or its hypotheses.
