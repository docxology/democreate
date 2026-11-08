"""Gate: generated workspaces must stay out of the public source index.

``output/`` and ``project_videos/`` are repository-local, regeneratable workspaces
that may contain private project inputs or renders. Public figures and decoded
samples belong in their reviewed documentation locations, not a force-tracked
workspace. Check Git's actual index; an unavailable reader must fail, not certify
that no generated files are tracked. This is not a content or secret scanner.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _tracked_output_paths() -> list[str]:
    """Return indexed generated files; propagate an unavailable Git observation."""
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--", "output/", "project_videos/"],
        cwd=ROOT,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    return [path for path in proc.stdout.split("\0") if path]


def test_generated_workspaces_are_not_tracked() -> None:
    """Neither canonical nor per-project generated workspaces may be published."""
    tracked = _tracked_output_paths()
    assert not tracked, (
        "Generated workspaces must remain untracked; review intended public "
        "figures separately under docs/ or examples/:\n  "
        + "\n  ".join(sorted(tracked))
    )
