"""Score supplied independent onset annotations without certifying an experiment.

Annotation format ``1`` is separate from the Demo schema. One JSON object declares
one fixed engine/voice/capture cohort, an externally referenced expected-event
inventory, and per-demo expected events plus observations. Missing observations
remain in the denominator. References and media digests are declarations: this
module neither opens media nor verifies independence, provenance or predeclaration.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["SyncEvaluation", "load_sync_annotations", "score_sync_annotations"]

_MODES = ("codebase", "website", "terminal")
_EVENT_FIELDS = {"scene_id", "chunk_id", "action_index"}
_COHORT_FIELDS = {
    "condition", "tts_backend", "voice", "animation", "website_capture",
    "annotation_method", "timebase", "inventory_ref", "annotation_ref",
}
_LIMITS = (
    "Media bytes and their declared digests were not verified.",
    "Annotator independence, inventory predeclaration and provenance were not verified.",
    "Completeness beyond the supplied expected-event inventory was not verified.",
    "Passing supplied-data checks is not study verification or release authorization.",
)


@dataclass(frozen=True)
class SyncEvaluation:
    """Diagnostic arithmetic and eligibility checks for one supplied cohort.

    Attributes:
        cohort: Declared conditions and opaque provenance references.
        demos: Every declared demo and expected event, including missing onsets.
        metrics: Unrounded aggregate errors, counts and annotation coverage.
        checks: Separate numeric, corpus, eligibility and accounting outcomes.
        issues: Reasons the supplied cohort does not meet those checks.
    """

    cohort: dict[str, str]
    demos: list[dict[str, Any]]
    metrics: dict[str, Any]
    checks: dict[str, bool]
    issues: tuple[str, ...]

    @property
    def criteria_met_for_supplied_annotations(self) -> bool:
        """Whether all checks pass, not whether an independent study is verified."""
        return all(self.checks.values())

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable report with its evidence limits attached."""
        return {
            "report_version": "1",
            "cohort": self.cohort,
            "demos": self.demos,
            "metrics": self.metrics,
            "checks": self.checks,
            "criteria_met_for_supplied_annotations": (
                self.criteria_met_for_supplied_annotations
            ),
            "issues": list(self.issues),
            "evidence_limits": list(_LIMITS),
            "evidence_verification": {
                "media_bytes": "not_verified",
                "annotation_independence": "not_verified",
                "inventory_predeclaration": "not_verified",
                "complete_real_corpus": "not_verified",
            },
        }


def _object(
    value: object, required: set[str], optional: set[str], label: str
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(k, str) for k in value):
        raise ValueError(f"{label} must be an object with string keys")
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing or unknown:
        raise ValueError(
            f"{label}: missing fields {sorted(missing)}; unknown fields {sorted(unknown)}"
        )
    return value


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{label} must be a nonempty string without surrounding space")
    return value


def _number(value: object, label: str, *, positive: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a finite number")
    try:
        number = float(value)
    except OverflowError as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(number) or number < 0 or (positive and number == 0):
        raise ValueError(f"{label} must be finite and {'positive' if positive else 'nonnegative'}")
    if isinstance(value, int) and number != value:
        raise ValueError(f"{label} cannot be represented losslessly as binary64")
    return number


def _array(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{label} must be an array")
    return value


def _key(value: Mapping[str, Any], label: str) -> tuple[str, str, int]:
    index = value["action_index"]
    if isinstance(index, bool) or not isinstance(index, int) or index < 0:
        raise ValueError(f"{label}.action_index must be a nonnegative integer")
    return (
        _text(value["scene_id"], f"{label}.scene_id"),
        _text(value["chunk_id"], f"{label}.chunk_id"),
        index,
    )


def _digest(value: object, label: str) -> str:
    text = _text(value, label)
    if re.fullmatch(r"[0-9a-fA-F]{64}", text) is None:
        raise ValueError(f"{label} must be a 64-digit hexadecimal SHA-256 declaration")
    return text.lower()


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[middle]
    low, high = ordered[middle - 1], ordered[middle]
    # Errors are nonnegative: unlike (low + high) / 2 this cannot overflow.
    return low + (high - low) / 2


def _cohort(root: Mapping[str, Any]) -> dict[str, str]:
    cohort = {key: _text(root[key], key) for key in sorted(_COHORT_FIELDS)}
    choices = {
        "condition": {"default", "voiced_heuristic", "high_fidelity"},
        "animation": {"scheduled", "static"},
        "website_capture": {"synthetic", "real"},
        "timebase": {"encoded_video_ms"},
    }
    for key, allowed in choices.items():
        if cohort[key] not in allowed:
            raise ValueError(f"{key} must be one of {sorted(allowed)}")
    return cohort


def _demo_scores(
    raw: object, cohort: dict[str, str], seen_ids: set[str], seen_video: set[str]
) -> tuple[dict[str, Any], list[float]]:
    demo = _object(raw, {
        "id", "mode", "audio_sha256", "video_sha256", "fps", "duration_ms",
        "expected_events", "observations",
    }, _COHORT_FIELDS | {"failure_reason"}, "demo")
    ident = _text(demo["id"], "demo.id")
    if ident in seen_ids:
        raise ValueError(f"duplicate demo id: {ident}")
    seen_ids.add(ident)
    for field in _COHORT_FIELDS & demo.keys():
        if demo[field] != cohort[field]:
            raise ValueError(f"demo {ident}: mixed {field}; score separate cohorts")
    mode = _text(demo["mode"], f"demo {ident}.mode")
    if mode not in _MODES:
        raise ValueError(f"demo {ident}.mode must be one of {list(_MODES)}")
    failure = demo.get("failure_reason")
    if failure is not None:
        failure = _text(failure, f"demo {ident}.failure_reason")
    audio_hash = (
        None if demo["audio_sha256"] is None
        else _digest(demo["audio_sha256"], f"demo {ident}.audio_sha256")
    )
    video_hash = (
        None if demo["video_sha256"] is None
        else _digest(demo["video_sha256"], f"demo {ident}.video_sha256")
    )
    if video_hash is not None:
        if video_hash in seen_video:
            raise ValueError(f"duplicate video digest in demo {ident}; cannot count media twice")
        seen_video.add(video_hash)
    fps = (
        None if demo["fps"] is None
        else _number(demo["fps"], f"demo {ident}.fps", positive=True)
    )
    duration = (
        None if demo["duration_ms"] is None
        else _number(demo["duration_ms"], f"demo {ident}.duration_ms", positive=True)
    )
    media_available = all(
        value is not None for value in (audio_hash, video_hash, fps, duration)
    )
    if not media_available and failure is None:
        raise ValueError(f"demo {ident}: unavailable media requires failure_reason")

    expected: dict[tuple[str, str, int], Mapping[str, Any]] = {}
    for raw_event in _array(demo["expected_events"], f"demo {ident}.expected_events"):
        event = _object(raw_event, _EVENT_FIELDS | {"trigger_ref"}, set(), "expected event")
        key = _key(event, "expected event")
        _text(event["trigger_ref"], "expected event.trigger_ref")
        if key in expected:
            raise ValueError(f"demo {ident}: duplicate expected event {key}")
        expected[key] = event

    observed: dict[tuple[str, str, int], Mapping[str, Any]] = {}
    for raw_event in _array(demo["observations"], f"demo {ident}.observations"):
        event = _object(raw_event, _EVENT_FIELDS | {
            "acoustic_onset_ms", "visual_onset_ms", "uncertainty_ms",
        }, {"adjudication_ref"}, "observation")
        key = _key(event, "observation")
        if key not in expected or key in observed:
            raise ValueError(f"demo {ident}: unknown or duplicate observed event {key}")
        if "adjudication_ref" in event:
            _text(event["adjudication_ref"], "observation.adjudication_ref")
        observed[key] = event

    errors: list[float] = []
    events: list[dict[str, Any]] = []
    for key, event in expected.items():
        observation = observed.get(key)
        acoustic = visual = uncertainty = None
        if observation is not None:
            if not media_available and any(
                observation[field] is not None
                for field in ("acoustic_onset_ms", "visual_onset_ms")
            ):
                raise ValueError(
                    "unavailable media cannot have encoded-video onset observations"
                )
            onsets: list[float | None] = []
            for field in ("acoustic_onset_ms", "visual_onset_ms"):
                value = observation[field]
                onset = None if value is None else _number(value, f"observation.{field}")
                if onset is not None and (duration is None or onset >= duration):
                    raise ValueError(f"demo {ident}: {field} is outside the video interval")
                onsets.append(onset)
            acoustic, visual = onsets
            value = observation["uncertainty_ms"]
            uncertainty = None if value is None else _number(value, "observation.uncertainty_ms")
            if acoustic is not None and visual is not None and uncertainty is None:
                raise ValueError("complete observations must report uncertainty_ms")
            if (cohort["condition"] == "default" or cohort["tts_backend"] == "silent") and acoustic is not None:
                raise ValueError("silent/default cohorts cannot declare acoustic onsets")
        error = None if acoustic is None or visual is None else abs(visual - acoustic)
        if error is not None:
            errors.append(error)
        events.append({
            "scene_id": key[0], "chunk_id": key[1], "action_index": key[2],
            "trigger_ref": event["trigger_ref"],
            "acoustic_onset_ms": acoustic, "visual_onset_ms": visual,
            "uncertainty_ms": uncertainty, "absolute_error_ms": error,
            "adjudication_ref": observation.get("adjudication_ref") if observation else None,
        })
    return {
        "id": ident, "mode": mode, "audio_sha256": audio_hash,
        "video_sha256": video_hash, "fps": fps, "duration_ms": duration,
        "failure_reason": failure, "expected_event_count": len(expected),
        "observed_event_count": len(errors), "missing_event_count": len(expected) - len(errors),
        "median_error_ms": _median(errors), "events": events,
    }, errors


def score_sync_annotations(document: Mapping[str, Any]) -> SyncEvaluation:
    """Score one declared onset-annotation cohort under the existing H1 criteria.

    Both the pooled event median and median of per-demo medians must be at most
    120 ms, without rounding. Corpus accounting requires at least 30 distinct
    demos and ten per fixed mode (codebase, website, terminal). Missing events or
    failed demos remain explicit and withhold a passing supplied-data outcome;
    this accounting safeguard is not a newly claimed experimental success rate.

    Args:
        document: Annotation-format-1 JSON object. Onsets use encoded-video ms;
            expected events are declared separately from measured observations.

    Returns:
        Arithmetic, eligibility, missing-data diagnostics and explicit limits.

    Raises:
        ValueError: Malformed, duplicate, mixed-cohort or contradictory input.
    """
    root = _object(document, _COHORT_FIELDS | {"annotation_version", "demos"}, set(), "annotations")
    if root["annotation_version"] != "1":
        raise ValueError("annotation_version must be the string '1'")
    cohort = _cohort(root)
    demos: list[dict[str, Any]] = []
    errors: list[float] = []
    seen_ids: set[str] = set()
    seen_video: set[str] = set()
    for raw in _array(root["demos"], "demos"):
        demo, event_errors = _demo_scores(raw, cohort, seen_ids, seen_video)
        demos.append(demo)
        errors.extend(event_errors)
    medians = [d["median_error_ms"] for d in demos if d["median_error_ms"] is not None]
    pooled, per_demo = _median(errors), _median(medians)
    mode_counts = {mode: sum(d["mode"] == mode for d in demos) for mode in _MODES}
    scored_counts = {
        mode: sum(d["mode"] == mode and d["median_error_ms"] is not None for d in demos)
        for mode in _MODES
    }
    expected_count = sum(d["expected_event_count"] for d in demos)
    eligible = (
        cohort["condition"] == "voiced_heuristic"
        and cohort["tts_backend"] in {"system", "kokoro"}
        and cohort["animation"] == "scheduled"
        and cohort["annotation_method"] == "independent_manual"
    )
    checks = {
        "numeric_thresholds_met": pooled is not None and per_demo is not None and pooled <= 120 and per_demo <= 120,
        "corpus_counts_met": len(demos) >= 30 and all(count >= 10 for count in scored_counts.values()),
        "declared_eligible": eligible,
        "all_declared_events_observed": bool(demos) and all(
            d["expected_event_count"] > 0 and d["missing_event_count"] == 0
            and d["failure_reason"] is None for d in demos
        ),
    }
    messages = {
        "numeric_thresholds_met": "Both unrounded medians must exist and be <=120 ms.",
        "corpus_counts_met": "At least 30 distinct demos and ten scored demos per fixed mode are required.",
        "declared_eligible": "The declared cohort is not scheduled, independently annotated voiced-heuristic H1 with system/Kokoro TTS.",
        "all_declared_events_observed": "The supplied inventory contains empty, missing-onset or failed demos/events.",
    }
    return SyncEvaluation(
        cohort=cohort, demos=demos,
        metrics={
            "declared_demo_count": len(demos), "mode_counts": mode_counts,
            "scored_mode_counts": scored_counts,
            "expected_event_count": expected_count, "observed_event_count": len(errors),
            "missing_event_count": expected_count - len(errors),
            "annotation_coverage": len(errors) / expected_count if expected_count else None,
            "pooled_event_median_ms": pooled, "median_of_demo_medians_ms": per_demo,
        },
        checks=checks, issues=tuple(messages[key] for key, passed in checks.items() if not passed),
    )


def load_sync_annotations(path: Path) -> SyncEvaluation:
    """Read strict JSON and score annotations without opening referenced media.

    Args:
        path: UTF-8 JSON annotation file. Provenance references remain opaque.

    Returns:
        The scored report; inspect its supplied-data checks and evidence limits.

    Raises:
        OSError: The annotation file cannot be read.
        ValueError: JSON or annotation data are malformed, including duplicate keys.
    """
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    document = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    return score_sync_annotations(document)
