"""Gate: the public repo may track ONLY DemoCreate's own self-descriptor output.

The `output/` tree is gitignored, but the package deliberately force-tracks ONE
bundle — DemoCreate's own *self-descriptor*, the showcase render (`output/video`,
`output/web`, `output/chapters`, `output/provenance`) — as the canonical public
example. Everything else under `output/` is regeneratable and must **never** be
committed: a per-project render from ``democreate portfolio`` (lands under
``output/<project-name>/``) AND the research-paper demos from ``democreate paper``
(``output/paper_demo`` / ``output/paper_showcase`` — those describe a *paper*, not
DemoCreate, and are regeneratable, so they stay out of the public repo).

This test is the confirmation/gating that enforces exactly that: every path under
``output/`` that git tracks must live in one of the fixed showcase self-descriptor
workspace directories. Anything else — a project render or a paper demo — makes
this test fail loudly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Fixed workspace directory names the showcase self-descriptor renders into at the
# output/ root. A `portfolio` run writes to output/<project-name>/..., and a paper
# demo to output/paper_demo|paper_showcase/... — none of those tops are in this set,
# so committing one fails the gate.
_ALLOWED_TOP = frozenset(
    {
        "video",
        "web",
        "chapters",
        "provenance",
        "captions",
        "demos",
        "audio",
        "frames",
        "assets",
        "pages",
    }
)


def _tracked_output_paths() -> list[str]:
    """Return git-tracked paths under output/ (empty if git/output absent)."""
    try:
        proc = subprocess.run(
            ["git", "ls-files", "output/"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:  # pragma: no cover - git not installed
        pytest.skip("git not available")
    return [line for line in proc.stdout.splitlines() if line.strip()]


def test_only_self_descriptor_output_is_tracked() -> None:
    """No confidential per-project render may be tracked under output/."""
    offenders: list[str] = []
    for path in _tracked_output_paths():
        parts = Path(path).parts  # e.g. ("output", "anterra", "video", "demo.mp4")
        if len(parts) < 2 or parts[0] != "output":
            continue
        top = parts[1]
        if top not in _ALLOWED_TOP:
            offenders.append(path)
    assert not offenders, (
        "Only DemoCreate's self-descriptor output may be public; these tracked "
        "output/ paths are NOT in the self-descriptor allowlist (a confidential "
        "per-project render must never be committed):\n  "
        + "\n  ".join(sorted(offenders))
        + f"\nAllowed top-level output dirs: {sorted(_ALLOWED_TOP)}"
    )


def test_self_descriptor_is_present() -> None:
    """The repo should track the showcase self-descriptor video (positive control).

    Skips on a shallow/sparse checkout that excludes output/ entirely, so the gate
    never produces a false failure where the self-descriptor simply was not
    checked out.
    """
    tracked = _tracked_output_paths()
    if not tracked:
        pytest.skip("no tracked output/ in this checkout")
    assert any(
        p == "output/video/demo.mp4" for p in tracked
    ), "expected the showcase self-descriptor at output/video/demo.mp4 to be tracked"
