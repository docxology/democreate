"""Tests for foundational modules: project_paths, _logging, errors."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from democreate._logging import get_logger, log_stage
from democreate.errors import (
    BackendUnavailableError,
    DemoCreateError,
    SchemaValidationError,
)
from democreate.project_paths import Workspace, default_output_root


def test_default_output_root_is_cwd_output() -> None:
    assert default_output_root() == Path.cwd() / "output"


def test_workspace_creates_subdirs_lazily(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "out")
    for sub in (ws.audio, ws.frames, ws.video, ws.captions, ws.web, ws.manifests, ws.demos):
        assert sub.exists() and sub.is_dir()
    assert ws.root == tmp_path / "out"


def test_workspace_default_root_when_none(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    ws = Workspace()
    assert ws.root == tmp_path / "output"


def test_workspace_clean_removes_tree(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "out")
    _ = ws.audio  # force creation
    assert ws.root.exists()
    ws.clean()
    assert not ws.root.exists()
    ws.clean()  # idempotent on missing dir


def test_get_logger_namespacing() -> None:
    assert get_logger("democreate").name == "democreate"
    assert get_logger("foo.bar").name == "democreate.foo.bar"
    assert get_logger("democreate.x").name == "democreate.x"


def test_log_stage_success_and_failure(caplog) -> None:
    logger = get_logger("democreate.test")
    with caplog.at_level(logging.INFO, logger="democreate.test"):
        with log_stage("ok stage", logger):
            pass
    with pytest.raises(ValueError):
        with log_stage("bad stage", logger):
            raise ValueError("boom")


def test_schema_validation_error_carries_problems() -> None:
    err = SchemaValidationError(["a", "b"])
    assert err.problems == ["a", "b"]
    assert "a; b" in str(err)
    assert isinstance(err, DemoCreateError)


def test_schema_validation_error_empty() -> None:
    assert "unknown problem" in str(SchemaValidationError([]))


def test_backend_unavailable_hint() -> None:
    err = BackendUnavailableError("kokoro", extra="tts")
    assert err.backend == "kokoro" and err.extra == "tts"
    assert "uv sync --extra tts" in str(err)
    assert "uv sync" not in str(BackendUnavailableError("x"))
