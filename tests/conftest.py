"""Shared pytest fixtures and import path setup for the DemoCreate suite.

Tests use real computation against real (temporary) files — no mocks. Heavy
optional backends are exercised only when installed, guarded by
``pytest.importorskip`` or the ``backend`` marker.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Ensure `src/` is importable even without the editable install (belt and braces).
_SRC = Path(__file__).resolve().parent.parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Keep any matplotlib/manim-adjacent backend headless so tests never open a window.
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("DEMOCREATE_LOG_LEVEL", "WARNING")

from democreate.schema import (  # noqa: E402  (import after sys.path setup)
    Action,
    ActionType,
    Chunk,
    Demo,
    Scene,
    SceneKind,
)


@pytest.fixture
def tmp_workspace(tmp_path: Path):
    """Return a :class:`democreate.project_paths.Workspace` rooted in a temp dir."""
    from democreate.project_paths import Workspace

    return Workspace(tmp_path / "output")


@pytest.fixture
def sample_demo() -> Demo:
    """A small but structurally complete demo used across subsystem tests.

    Two scenes (codebase + terminal), multiple chunks, and trigger-word-anchored
    actions, so timing/sync/timeline/caption logic has real material to chew on.
    """
    intro = Scene(
        id="intro",
        title="Project Overview",
        kind=SceneKind.CODEBASE,
        context={"repo": "democreate"},
    )
    intro.chunks.append(
        Chunk(
            id="c-open",
            text="We begin by opening the main entry point of the package.",
            actions=[
                Action(
                    ActionType.OPEN_FILE,
                    {"path": "src/democreate/cli.py"},
                    trigger_word="opening",
                ),
                Action(
                    ActionType.HIGHLIGHT_LINES,
                    {"lines": [1, 2, 3]},
                    trigger_word="entry",
                ),
            ],
        )
    )
    intro.chunks.append(
        Chunk(
            id="c-explain",
            text="The pipeline turns a declarative demo into audio and video.",
            actions=[
                Action(
                    ActionType.TYPE_CODE,
                    {"code": "demo = Demo(title='Tour')"},
                    trigger_word="declarative",
                )
            ],
        )
    )
    run = Scene(id="run", title="Running It", kind=SceneKind.TERMINAL)
    run.chunks.append(
        Chunk(
            id="c-run",
            text="Finally we run the command line interface to build everything.",
            actions=[
                Action(
                    ActionType.RUN_COMMAND,
                    {"command": "democreate build demo.json"},
                    trigger_word="run",
                )
            ],
        )
    )
    return Demo(title="DemoCreate Self Tour", scenes=[intro, run], width=1280, height=720)


@pytest.fixture
def sample_python_source() -> str:
    """A representative Python module source for codebase/AST tests."""
    return (
        '"""Example module."""\n'
        "import os\n"
        "from pathlib import Path\n\n\n"
        "CONSTANT = 42\n\n\n"
        "def greet(name: str) -> str:\n"
        '    """Return a greeting."""\n'
        '    return f"hello {name}"\n\n\n'
        "class Widget:\n"
        '    """A widget."""\n\n'
        "    def render(self) -> str:\n"
        '        """Render it."""\n'
        '        return "widget"\n'
    )
