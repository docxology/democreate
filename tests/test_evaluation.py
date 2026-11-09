"""Synthetic arithmetic fixtures, never an independently annotated study corpus."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from democreate.evaluation import load_sync_annotations, score_sync_annotations


def _event(index: int = 0) -> dict:
    return {"scene_id": "scene", "chunk_id": "chunk", "action_index": index}


def _cohort() -> dict:
    demos = []
    for index in range(30):
        demos.append({
            "id": f"synthetic-{index}",
            "mode": ("codebase", "website", "terminal")[index // 10],
            "audio_sha256": "a" * 64,
            "video_sha256": f"{index:064x}",
            "fps": 30, "duration_ms": 2000,
            "expected_events": [{**_event(), "trigger_ref": "synthetic-occurrence-1"}],
            "observations": [{
                **_event(), "acoustic_onset_ms": 100,
                "visual_onset_ms": 220, "uncertainty_ms": 20,
            }],
        })
    return {
        "annotation_version": "1", "condition": "voiced_heuristic",
        "tts_backend": "kokoro", "voice": "af_heart", "animation": "scheduled",
        "website_capture": "synthetic", "annotation_method": "independent_manual",
        "timebase": "encoded_video_ms", "inventory_ref": "synthetic-test-inventory",
        "annotation_ref": "synthetic-test-observations", "demos": demos,
    }


def test_exact_boundary_is_inclusive_but_never_certifies_a_study() -> None:
    result = score_sync_annotations(_cohort())
    assert result.criteria_met_for_supplied_annotations
    assert result.metrics["pooled_event_median_ms"] == 120
    assert result.metrics["median_of_demo_medians_ms"] == 120
    assert set(result.to_dict()["evidence_verification"].values()) == {"not_verified"}
    json.dumps(result.to_dict(), allow_nan=False)


@pytest.mark.parametrize("dominant_error,other_error", [(0, 200), (200, 0)])
def test_both_medians_are_required_with_unequal_event_counts(
    dominant_error: int, other_error: int
) -> None:
    document = _cohort()
    for demo in document["demos"]:
        demo["observations"][0]["visual_onset_ms"] = 100 + other_error
    dominant = document["demos"][0]
    dominant["expected_events"] = [
        {**_event(i), "trigger_ref": f"synthetic-occurrence-{i}"} for i in range(80)
    ]
    dominant["observations"] = [
        {**_event(i), "acoustic_onset_ms": 100,
         "visual_onset_ms": 100 + dominant_error, "uncertainty_ms": 1}
        for i in range(80)
    ]
    result = score_sync_annotations(document)
    assert result.metrics["pooled_event_median_ms"] == dominant_error
    assert result.metrics["median_of_demo_medians_ms"] == other_error
    assert not result.checks["numeric_thresholds_met"]
    assert not result.criteria_met_for_supplied_annotations


def test_unrounded_threshold_is_not_a_display_precision_decision() -> None:
    document = _cohort()
    for demo in document["demos"]:
        demo["observations"][0]["visual_onset_ms"] = 220.000001
    result = score_sync_annotations(document)
    assert result.metrics["pooled_event_median_ms"] > 120
    assert not result.checks["numeric_thresholds_met"]


@pytest.mark.parametrize("offset,expected", [(120, True), (122, False)])
def test_large_lossless_integers_keep_the_threshold_decision(
    offset: int, expected: bool
) -> None:
    document = _cohort()
    for demo in document["demos"]:
        demo["duration_ms"] = 9007199254741992
        demo["observations"][0]["acoustic_onset_ms"] = 9007199254740992
        demo["observations"][0]["visual_onset_ms"] = 9007199254740992 + offset
    result = score_sync_annotations(document)
    assert result.metrics["pooled_event_median_ms"] == offset
    assert result.metrics["median_of_demo_medians_ms"] == offset
    assert result.criteria_met_for_supplied_annotations is expected


def test_lossy_integer_cannot_round_a_failing_error_into_a_pass() -> None:
    document = _cohort()
    for demo in document["demos"]:
        demo["duration_ms"] = 9007199254741992
        demo["observations"][0]["acoustic_onset_ms"] = 9007199254740992
        demo["observations"][0]["visual_onset_ms"] = 9007199254741113
    with pytest.raises(ValueError):
        score_sync_annotations(document)


@pytest.mark.parametrize("case", ["29-demos", "one-mode", "empty-events", "no-demos"])
def test_denominator_cannot_be_replaced_by_successful_rows(case: str) -> None:
    document = _cohort()
    if case == "29-demos":
        document["demos"].pop()
    elif case == "one-mode":
        for demo in document["demos"]:
            demo["mode"] = "codebase"
    elif case == "empty-events":
        for demo in document["demos"]:
            demo["expected_events"] = []
            demo["observations"] = []
    else:
        document["demos"] = []
    result = score_sync_annotations(document)
    assert not result.checks["corpus_counts_met"]
    assert not result.criteria_met_for_supplied_annotations
    if case in {"empty-events", "no-demos"}:
        assert result.metrics["pooled_event_median_ms"] is None
        assert result.metrics["median_of_demo_medians_ms"] is None
        assert result.metrics["annotation_coverage"] is None


@pytest.mark.parametrize("missing", ["row", "acoustic", "visual", "failed-demo"])
def test_missing_and_failed_measurements_remain_explicit(missing: str) -> None:
    document = _cohort()
    demo = document["demos"][0]
    if missing in {"row", "failed-demo"}:
        demo["observations"] = []
    else:
        demo["observations"][0][f"{missing}_onset_ms"] = None
    if missing == "failed-demo":
        demo["failure_reason"] = "Synthetic encode failure"
    result = score_sync_annotations(document)
    assert result.metrics["expected_event_count"] == 30
    assert result.metrics["observed_event_count"] == 29
    assert result.metrics["missing_event_count"] == 1
    assert result.metrics["annotation_coverage"] == pytest.approx(29 / 30)
    assert result.demos[0]["median_error_ms"] is None
    assert result.demos[0]["events"][0]["absolute_error_ms"] is None
    assert not result.checks["all_declared_events_observed"]
    assert not result.criteria_met_for_supplied_annotations


@pytest.mark.parametrize("case", ["id", "video", "expected", "observation", "unknown-event"])
def test_duplicate_or_uninventoried_measurements_are_rejected(case: str) -> None:
    document = _cohort()
    first, second = document["demos"][:2]
    if case == "id":
        second["id"] = first["id"]
    elif case == "video":
        first["video_sha256"] = "a" * 64
        second["video_sha256"] = first["video_sha256"].upper()
    elif case == "expected":
        first["expected_events"].append(deepcopy(first["expected_events"][0]))
    elif case == "observation":
        first["observations"].append(deepcopy(first["observations"][0]))
    else:
        first["observations"][0]["action_index"] = 999
    with pytest.raises(ValueError):
        score_sync_annotations(document)


@pytest.mark.parametrize(
    "value", [True, -1, float("nan"), float("inf"), 10**400, 2**53 + 1, "100"]
)
@pytest.mark.parametrize("field", ["fps", "duration_ms", "acoustic_onset_ms", "uncertainty_ms"])
def test_invalid_numbers_never_become_measurements(field: str, value: object) -> None:
    document = _cohort()
    demo = document["demos"][0]
    target = demo if field in {"fps", "duration_ms"} else demo["observations"][0]
    target[field] = value
    with pytest.raises(ValueError):
        score_sync_annotations(document)


@pytest.mark.parametrize("value", [True, -1, 0.5, "0"])
def test_action_identity_requires_an_actual_nonnegative_integer(value: object) -> None:
    document = _cohort()
    document["demos"][0]["expected_events"][0]["action_index"] = value
    with pytest.raises(ValueError):
        score_sync_annotations(document)


def test_outside_video_or_missing_uncertainty_cannot_score() -> None:
    for field, value in (("visual_onset_ms", 2001), ("uncertainty_ms", None)):
        document = _cohort()
        document["demos"][0]["observations"][0][field] = value
        with pytest.raises(ValueError):
            score_sync_annotations(document)


@pytest.mark.parametrize("field,value", [
    ("voice", "am_adam"), ("tts_backend", "system"),
    ("website_capture", "real"), ("condition", "high_fidelity"),
])
def test_mixed_strata_cannot_be_silently_pooled(field: str, value: str) -> None:
    document = _cohort()
    document["demos"][0][field] = value
    with pytest.raises(ValueError, match="mixed"):
        score_sync_annotations(document)


@pytest.mark.parametrize("field,value", [
    ("animation", "static"), ("annotation_method", "derived_from_timestamps"),
    ("condition", "high_fidelity"), ("tts_backend", "other-engine"),
])
def test_ineligible_conditions_retain_diagnostics_without_passing(field: str, value: str) -> None:
    document = _cohort()
    document[field] = value
    result = score_sync_annotations(document)
    assert result.metrics["pooled_event_median_ms"] == 120
    assert not result.checks["declared_eligible"]
    assert not result.criteria_met_for_supplied_annotations


def test_silent_controls_have_undefined_acoustic_error_not_zero() -> None:
    document = _cohort()
    document["condition"] = "default"
    document["tts_backend"] = "silent"
    for demo in document["demos"]:
        demo["observations"][0]["acoustic_onset_ms"] = None
    result = score_sync_annotations(document)
    assert result.metrics["pooled_event_median_ms"] is None
    assert result.metrics["median_of_demo_medians_ms"] is None
    assert not result.criteria_met_for_supplied_annotations
    document["demos"][0]["observations"][0]["acoustic_onset_ms"] = 100
    with pytest.raises(ValueError, match="silent"):
        score_sync_annotations(document)


def test_uncertainty_and_fps_are_reported_not_invented_acceptance_gates() -> None:
    document = _cohort()
    for demo in document["demos"]:
        demo["fps"] = 0.1
        demo["observations"][0]["uncertainty_ms"] = 100000
    result = score_sync_annotations(document)
    assert result.criteria_met_for_supplied_annotations
    assert result.demos[0]["fps"] == 0.1
    assert result.demos[0]["events"][0]["uncertainty_ms"] == 100000


def test_finite_extreme_errors_do_not_overflow_the_median() -> None:
    document = _cohort()
    for demo in document["demos"]:
        demo["duration_ms"] = 1.7e308
        demo["observations"][0]["acoustic_onset_ms"] = 0
        demo["observations"][0]["visual_onset_ms"] = 1.6e308
    result = score_sync_annotations(document)
    assert result.metrics["pooled_event_median_ms"] == 1.6e308
    assert result.metrics["median_of_demo_medians_ms"] == 1.6e308
    json.dumps(result.to_dict(), allow_nan=False)
    assert not result.criteria_met_for_supplied_annotations


@pytest.mark.parametrize("case", ["unknown-field", "digest", "mode", "timebase", "version", "array"])
def test_malformed_contract_is_rejected(case: str) -> None:
    document = _cohort()
    if case == "unknown-field":
        document["invented"] = True
    elif case == "digest":
        document["demos"][0]["audio_sha256"] = "not-a-digest"
    elif case == "mode":
        document["demos"][0]["mode"] = "slide"
    elif case == "timebase":
        document["timebase"] = "chunk_local_ms"
    elif case == "version":
        document["annotation_version"] = 1
    else:
        document["demos"] = {}
    with pytest.raises(ValueError):
        score_sync_annotations(document)


def test_strict_file_reader_rejects_duplicate_json_keys(tmp_path) -> None:
    path = tmp_path / "ambiguous.json"
    path.write_text('{"annotation_version":"1","annotation_version":"2"}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_sync_annotations(path)


def test_file_reader_returns_actual_scored_result(tmp_path) -> None:
    document = _cohort()
    document["demos"][0]["observations"] = []
    path = tmp_path / "annotations.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = load_sync_annotations(path)
    assert result.metrics["missing_event_count"] == 1
    assert not result.criteria_met_for_supplied_annotations


@pytest.mark.parametrize("field", ["acoustic_onset_ms", "visual_onset_ms"])
def test_video_end_is_not_a_sampleable_onset(field: str) -> None:
    document = _cohort()
    document["demos"][0]["observations"][0][field] = 2000
    with pytest.raises(ValueError, match="video interval"):
        score_sync_annotations(document)


@pytest.mark.parametrize("per_event", [False, True])
def test_unequal_middle_values_are_averaged_at_both_levels(per_event: bool) -> None:
    document = _cohort()
    for index, demo in enumerate(document["demos"]):
        if per_event:
            demo["expected_events"] = [
                {**_event(i), "trigger_ref": f"synthetic-occurrence-{i}"}
                for i in range(2)
            ]
            demo["observations"] = [
                {**_event(i), "acoustic_onset_ms": 100,
                 "visual_onset_ms": 100 + 240 * i, "uncertainty_ms": 1}
                for i in range(2)
            ]
        else:
            demo["observations"][0]["visual_onset_ms"] = 100 if index < 15 else 340
    result = score_sync_annotations(document)
    assert result.metrics["pooled_event_median_ms"] == 120
    assert result.metrics["median_of_demo_medians_ms"] == 120
    assert result.criteria_met_for_supplied_annotations


@pytest.mark.parametrize("all_media_missing", [False, True])
def test_failed_media_needs_no_fabricated_digest_or_duration(
    all_media_missing: bool,
) -> None:
    document = _cohort()
    for demo in document["demos"][:2]:
        demo["failure_reason"] = "Synthetic unavailable media"
        demo["video_sha256"] = demo["fps"] = demo["duration_ms"] = None
        if all_media_missing:
            demo["audio_sha256"] = None
        demo["observations"] = []
    result = score_sync_annotations(document)
    assert result.metrics["declared_demo_count"] == 30
    assert result.metrics["expected_event_count"] == 30
    assert result.metrics["missing_event_count"] == 2
    assert result.demos[0]["video_sha256"] is None
    assert result.demos[0]["median_error_ms"] is None
    assert not result.criteria_met_for_supplied_annotations


def test_unavailable_media_cannot_support_onsets_or_unexplained_missing_identity() -> None:
    document = _cohort()
    document["demos"][0]["video_sha256"] = None
    with pytest.raises(ValueError, match="failure_reason"):
        score_sync_annotations(document)
    document["demos"][0]["failure_reason"] = "No encoded video"
    with pytest.raises(ValueError, match="unavailable media"):
        score_sync_annotations(document)


@pytest.mark.parametrize("insufficient", [False, True])
def test_cli_diagnostics_distinguish_criteria_exit_status(
    tmp_path, insufficient: bool,
) -> None:
    from typer.testing import CliRunner

    from democreate.cli import app

    document = _cohort()
    if insufficient:
        document["demos"].pop()
    path = tmp_path / "annotations.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    result = CliRunner().invoke(app, ["score-sync", str(path)])
    assert result.exit_code == (1 if insufficient else 0), result.output
    report = json.loads(result.stdout)
    assert report["metrics"]["pooled_event_median_ms"] == 120
    assert report["criteria_met_for_supplied_annotations"] is not insufficient
    assert report["evidence_verification"]["annotation_independence"] == "not_verified"


def test_cli_malformed_input_is_not_an_unmet_study_report(tmp_path) -> None:
    from typer.testing import CliRunner

    from democreate.cli import app

    path = tmp_path / "bad.json"
    path.write_text(
        '{"annotation_version":"1","annotation_version":"2"}', encoding="utf-8"
    )
    result = CliRunner().invoke(app, ["score-sync", str(path)])
    assert result.exit_code == 2
    assert result.stdout == ""
    assert "duplicate JSON key" in json.loads(result.stderr)["error"]
