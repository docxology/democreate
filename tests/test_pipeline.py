"""End-to-end integration tests for the pipeline (deterministic default backends).

These exercise the whole package wired together: TTS -> sync -> timeline ->
compose -> captions -> export, using only the core dependencies.
"""

from __future__ import annotations

import json

import pytest

from democreate.errors import SchemaValidationError
from democreate.pipeline import Pipeline, PipelineResult, build_demo
from democreate.schema import Demo


def test_full_pipeline_produces_all_artifacts(sample_demo: Demo, tmp_workspace) -> None:
    result = build_demo(sample_demo, tmp_workspace)
    assert isinstance(result, PipelineResult)
    # audio: one clip per chunk
    assert len(result.clips) == len(sample_demo.iter_chunks())
    for clip in result.clips:
        assert clip.path.exists() and clip.path.stat().st_size > 0
    # timeline
    assert result.timeline is not None
    assert result.timeline.total_ms > 0
    # frames + manifest
    assert result.manifest_path is not None and result.manifest_path.exists()
    assert len(result.frame_paths) > 0
    for f in result.frame_paths:
        assert f.exists() and f.stat().st_size > 0
    # captions
    assert result.caption_paths["srt"].exists()
    assert result.caption_paths["vtt"].read_text().startswith("WEBVTT")
    # exports
    assert result.player_path is not None and result.player_path.exists()
    assert sample_demo.title in result.player_path.read_text(encoding="utf-8")
    assert result.transcript_path.exists()
    assert result.demo_path.exists()


def test_pipeline_sets_timing_on_demo(sample_demo: Demo, tmp_workspace) -> None:
    build_demo(sample_demo, tmp_workspace)
    # sync assigned chunk start times and action timestamps
    for chunk in sample_demo.iter_chunks():
        assert chunk.start_ms is not None
        assert chunk.audio_path is not None
    for action in sample_demo.iter_actions():
        assert action.timestamp_ms is not None


def test_pipeline_strict_rejects_invalid_demo(tmp_workspace) -> None:
    bad = Demo(title="")  # empty title fails validation
    with pytest.raises(SchemaValidationError):
        build_demo(bad, tmp_workspace, strict=True)


def test_pipeline_non_strict_allows_invalid_demo(tmp_workspace) -> None:
    # a demo with no scenes is structurally "valid" but trivial; force a warning
    # path by using non-strict with a duplicate id demo
    from democreate.schema import Scene

    d = Demo(title="dupes", scenes=[Scene(id="x"), Scene(id="x")])
    result = build_demo(d, tmp_workspace, strict=False)
    assert isinstance(result, PipelineResult)


def test_result_summary_is_json_serializable(sample_demo: Demo, tmp_workspace) -> None:
    result = build_demo(sample_demo, tmp_workspace)
    blob = json.dumps(result.summary())
    parsed = json.loads(blob)
    assert parsed["title"] == sample_demo.title
    assert parsed["frames"] == len(result.frame_paths)


def test_pipeline_reload_demo_from_disk(sample_demo: Demo, tmp_workspace) -> None:
    result = build_demo(sample_demo, tmp_workspace)
    reloaded = Demo.from_json(result.demo_path.read_text(encoding="utf-8"))
    assert reloaded.title == sample_demo.title
    assert len(reloaded.iter_actions()) == len(sample_demo.iter_actions())


def test_custom_pipeline_construction(sample_demo: Demo, tmp_workspace) -> None:
    p = Pipeline(wpm=200, strict=False)
    result = p.run(sample_demo, tmp_workspace)
    assert result.timeline is not None
