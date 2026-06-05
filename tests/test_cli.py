"""Tests for the democreate CLI (via typer's CliRunner — real invocations)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from democreate.cli import app
from democreate.schema import Demo

runner = CliRunner()


def test_version() -> None:
    res = runner.invoke(app, ["version"])
    assert res.exit_code == 0
    assert "democreate" in res.stdout


def test_init_writes_json_then_inspect(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo.json"
    res = runner.invoke(app, ["init", str(demo_path)])
    assert res.exit_code == 0
    assert demo_path.exists()
    # the written demo is valid
    d = Demo.from_json(demo_path.read_text(encoding="utf-8"))
    assert d.is_valid()
    res2 = runner.invoke(app, ["inspect", str(demo_path)])
    assert res2.exit_code == 0
    assert "scenes" in res2.stdout


def test_init_yaml(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo.yaml"
    res = runner.invoke(app, ["init", str(demo_path), "--format", "yaml"])
    assert res.exit_code == 0
    assert Demo.from_yaml(demo_path.read_text(encoding="utf-8")).is_valid()


def test_inspect_invalid_demo_exits_nonzero(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"title": ""}), encoding="utf-8")
    res = runner.invoke(app, ["inspect", str(bad)])
    assert res.exit_code == 1


def test_build_end_to_end(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo.json"
    runner.invoke(app, ["init", str(demo_path)])
    out = tmp_path / "out"
    res = runner.invoke(app, ["build", str(demo_path), "--output", str(out)])
    assert res.exit_code == 0, res.stdout
    assert (out / "web" / "player.html").exists()


def test_captions_srt(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo.json"
    runner.invoke(app, ["init", str(demo_path)])
    res = runner.invoke(app, ["captions", str(demo_path), "--format", "srt"])
    assert res.exit_code == 0
    assert "-->" in res.stdout


def test_captions_bad_format(tmp_path: Path) -> None:
    demo_path = tmp_path / "demo.json"
    runner.invoke(app, ["init", str(demo_path)])
    res = runner.invoke(app, ["captions", str(demo_path), "--format", "xyz"])
    assert res.exit_code != 0


def test_backends_lists_capabilities() -> None:
    res = runner.invoke(app, ["backends"])
    assert res.exit_code == 0
    assert "TTS" in res.stdout
    assert "default" in res.stdout or "installed" in res.stdout


def test_tour_generates_demo(tmp_path: Path) -> None:
    # tour over the package's own source tree
    src = Path(__file__).resolve().parent.parent / "src" / "democreate"
    out = tmp_path / "tourout"
    res = runner.invoke(app, ["tour", str(src), "--output", str(out), "--no-build"])
    assert res.exit_code == 0, res.stdout
    assert (out / "demos" / "tour.json").exists()
