"""Gate: the public repo may track ONLY DemoCreate's own self-descriptor output.

The `output/` tree is gitignored, but the package deliberately force-tracks its
*self-descriptor* — the showcase video and the research-paper demos (DemoCreate
describing itself) — as the canonical public example. Everything else under
`output/` is regeneratable and, when DemoCreate is pointed at a directory of other
projects (``democreate portfolio``), is a per-project render that must **never**
be committed to the public repository.

This test is the confirmation/gating that enforces exactly that: every path under
``output/`` that git tracks must live in one of the fixed self-descriptor
workspace directories. A per-project render lands under ``output/<project-name>/``
whose top segment is the project's name — not in the allowlist — so committing one
makes this test fail loudly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

# Fixed workspace directory names the self-descriptor renders into. The showcase
# renders to the output/ root (output/video, output/web, ...); the two paper
# demos are their own sub-workspaces. A `portfolio` run instead writes to
# output/<project-name>/..., whose top segment will NOT be in this set.
_ALLOWED_TOP = frozenset(
    {
        # showcase workspace at output/ root
        "video",
        "web",
        "chapters",
        "provenance",
        "demos",
        "audio",
        "frames",
        "assets",
        "pages",
        # the two self-descriptor paper demos (their own workspaces)
        "paper_demo",
        "paper_showcase",
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
