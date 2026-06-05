"""Smoke tests for the thin orchestrator scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PROJECT_ROOT / "scripts"


def test_preflight_runs_and_reports_ok() -> None:
    res = subprocess.run(
        [sys.executable, str(SCRIPTS / "00_preflight.py")],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert "core import: OK" in res.stdout


def test_generate_demo_script_end_to_end(tmp_path: Path) -> None:
    from democreate.cli import _starter_demo

    demo_path = tmp_path / "demo.json"
    demo_path.write_text(_starter_demo().to_json(), encoding="utf-8")
    out = tmp_path / "out"
    res = subprocess.run(
        [sys.executable, str(SCRIPTS / "generate_demo.py"), str(demo_path), "--output", str(out)],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
    )
    assert res.returncode == 0, res.stdout + res.stderr
    assert (out / "web" / "player.html").exists()
