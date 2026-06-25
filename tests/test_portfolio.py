"""Tests for portfolio orchestration.

No mocks for the spine: facts collection, discovery, demo building, and index
writing run against a real tiny temporary repository tree. The failure-isolation
test uses ``monkeypatch`` to make one project's render raise — exercising the
batch loop's resilience, not faking any deterministic backend's output. The one
true end-to-end render is gated behind the ``backend``/ffmpeg marker.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate import portfolio
from democreate.export.video import ffmpeg_available
from democreate.portfolio import (
    ProjectResult,
    collect_project_facts,
    discover_projects,
    render_portfolio,
    utc_stamp,
)


def _make_repo(root: Path, name: str, *, readme: bool = True, py: bool = True) -> Path:
    """Create a tiny but real project tree under ``root/name``."""
    repo = root / name
    pkg = repo / "src" / name
    pkg.mkdir(parents=True)
    if readme:
        (repo / "README.md").write_text(
            f"# {name}\n\n"
            f"**{name}** is a small but real demonstration package.\n\n"
            "- It does one clear thing well.\n"
            "- It ships with tests and docs.\n",
            encoding="utf-8",
        )
    if py:
        (repo / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
        (pkg / "__init__.py").write_text("", encoding="utf-8")
        (pkg / "engine.py").write_text(
            '"""The engine drives the whole package end to end."""\n\n'
            "from __future__ import annotations\n\n\n"
            "class Engine:\n"
            '    """Run the core loop."""\n\n'
            "    def run(self, n: int) -> int:\n"
            "        return n * 2\n\n\n"
            "def helper(x: int) -> int:\n"
            "    return x + 1\n",
            encoding="utf-8",
        )
    return repo


def test_utc_stamp_is_filesystem_safe() -> None:
    from datetime import datetime, timezone

    stamp = utc_stamp(datetime(2026, 6, 25, 16, 45, 30, tzinfo=timezone.utc))
    assert stamp == "20260625T164530Z"
    assert "/" not in stamp and ":" not in stamp


def test_discover_projects_sorted_and_filtered(tmp_path: Path) -> None:
    _make_repo(tmp_path, "bravo")
    _make_repo(tmp_path, "alpha")
    (tmp_path / "output").mkdir()  # excluded build dir
    (tmp_path / ".hidden").mkdir()  # excluded hidden
    (tmp_path / "empty").mkdir()  # no README/py → not a project
    found = discover_projects(tmp_path)
    assert [p.name for p in found] == ["alpha", "bravo"]


def test_discover_skip(tmp_path: Path) -> None:
    _make_repo(tmp_path, "alpha")
    _make_repo(tmp_path, "bravo")
    found = discover_projects(tmp_path, skip=("bravo",))
    assert [p.name for p in found] == ["alpha"]


def test_collect_facts_from_real_repo(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, "widget")
    facts = collect_project_facts(repo)
    assert facts.name == "widget"
    assert "demonstration package" in facts.tagline
    assert facts.overview_bullets  # README bullets captured
    assert facts.module_count >= 1
    assert facts.class_count >= 1
    assert facts.function_count >= 1
    # the engine module is selected and carries a real excerpt + its docstring
    names = {m.name for m in facts.key_modules}
    assert "engine" in names
    engine = next(m for m in facts.key_modules if m.name == "engine")
    assert "class Engine" in engine.code_excerpt
    assert engine.docstring and "drives the whole package" in engine.docstring
    assert facts.run_command[0] == "uv run pytest -q"


def test_collect_facts_no_readme(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path, "noreadme", readme=False)
    facts = collect_project_facts(repo)
    assert facts.tagline == ""
    assert facts.overview_bullets == []
    assert facts.module_count >= 1  # still walks the code


def test_build_project_demo_writes_architecture(tmp_path: Path, tmp_workspace) -> None:
    repo = _make_repo(tmp_path, "arch")
    demo, facts = portfolio.build_project_demo(repo, tmp_workspace)
    assert demo.validate() == []
    arch = Path(tmp_workspace.root) / "assets" / "architecture.png"
    assert arch.exists() and arch.stat().st_size > 0
    # the architecture scene references the generated image
    arch_scene = next(s for s in demo.scenes if s.id == "arch")
    assert arch_scene.context["background_image"].endswith("architecture.png")
    assert facts.name == "arch"


def test_failure_isolation_one_bad_project(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "out"
    projects = tmp_path / "projects"
    projects.mkdir()
    _make_repo(projects, "good")
    _make_repo(projects, "bad")

    def fake_render(repo, output_root, **kwargs):
        if repo.name == "bad":
            raise RuntimeError("boom")
        return ProjectResult(name=repo.name, ok=True, scenes=7, duration_s=5.0)

    monkeypatch.setattr(portfolio, "render_project", fake_render)
    report = render_portfolio(projects, out, timestamp="20260625T000000Z")
    by_name = {r.name: r for r in report.results}
    assert by_name["good"].ok is True
    assert by_name["bad"].ok is False
    assert "boom" in by_name["bad"].error
    assert report.ok_count == 1


def test_index_files_written(tmp_path: Path, monkeypatch) -> None:
    out = tmp_path / "out"
    projects = tmp_path / "projects"
    projects.mkdir()
    _make_repo(projects, "solo")

    def fake_render(repo, output_root, **kwargs):
        vp = Path(output_root) / repo.name / "video" / f"{repo.name}-summary-X.mp4"
        return ProjectResult(name=repo.name, ok=True, video_path=vp, scenes=7, duration_s=9.0)

    monkeypatch.setattr(portfolio, "render_project", fake_render)
    report = render_portfolio(projects, out, timestamp="20260625T000000Z")

    assert report.index_json and report.index_json.exists()
    assert report.index_html and report.index_html.exists()
    import json

    data = json.loads(report.index_json.read_text())
    assert data["timestamp"] == "20260625T000000Z"
    assert data["ok_count"] == 1
    assert data["projects"][0]["name"] == "solo"
    html = report.index_html.read_text()
    assert "solo" in html and "portfolio" in html.lower()


def test_timestamp_in_output_path(tmp_path: Path, monkeypatch) -> None:
    captured = {}
    out = tmp_path / "out"
    projects = tmp_path / "projects"
    projects.mkdir()
    _make_repo(projects, "stamped")

    def fake_render(repo, output_root, **kwargs):
        captured["ts"] = kwargs.get("timestamp")
        return ProjectResult(name=repo.name, ok=True, scenes=1)

    monkeypatch.setattr(portfolio, "render_project", fake_render)
    render_portfolio(projects, out, timestamp="20260625T123456Z")
    assert captured["ts"] == "20260625T123456Z"


def test_strip_md_removes_images_and_badges() -> None:
    from democreate.portfolio import _strip_md

    assert _strip_md("![logo](x.png) Hello **world**") == "Hello world"
    assert _strip_md("See [the docs](https://x) now") == "See the docs now"
    assert _strip_md("`code` and _emphasis_") == "code and emphasis"


def test_readme_badge_row_does_not_become_tagline(tmp_path: Path) -> None:
    repo = tmp_path / "badged"
    (repo / "src").mkdir(parents=True)
    (repo / "README.md").write_text(
        "# Badged\n\n"
        "[![License](https://img.shields.io/badge/License-MIT-red.svg)](LICENSE)\n\n"
        "Badged is a real library for turning specs into binaries.\n",
        encoding="utf-8",
    )
    (repo / "x.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    facts = collect_project_facts(repo)
    assert facts.tagline.startswith("Badged is a real library")
    assert "shields.io" not in facts.tagline


def test_run_command_variants(tmp_path: Path) -> None:
    from democreate.portfolio import _run_command

    js = tmp_path / "js"
    js.mkdir()
    (js / "package.json").write_text("{}", encoding="utf-8")
    assert _run_command(js)[0].startswith("npm")

    mk = tmp_path / "mk"
    mk.mkdir()
    (mk / "Makefile").write_text("all:\n\techo hi\n", encoding="utf-8")
    assert _run_command(mk)[0] == "make"

    bare = tmp_path / "bare"
    bare.mkdir()
    assert "ls" in _run_command(bare)[0]


@pytest.mark.backend
@pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg not installed")
def test_render_project_end_to_end_silent(tmp_path: Path) -> None:
    """A real repo renders to a real MP4 via the full pipeline (silent TTS)."""
    repo = _make_repo(tmp_path, "e2e")
    out = tmp_path / "out"
    result = portfolio.render_project(
        repo, out, tts="silent", timestamp="20260625T000000Z", verify=False
    )
    assert result.video_path is not None
    assert result.video_path.exists() and result.video_path.stat().st_size > 0
    # lands in a per-project subfolder with a timestamped filename
    assert result.video_path.parent.parent.name == "e2e"
    assert "20260625T000000Z" in result.video_path.name
    assert result.scenes >= 4
