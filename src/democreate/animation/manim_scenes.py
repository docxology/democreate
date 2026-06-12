"""Manim code-walkthrough scene specs.

The *spec* is pure data: :func:`build_code_scene_spec` returns a JSON-serializable
description of a line-by-line code reveal (title, code, language, ordered reveal
steps with durations). It needs no manim and is fully testable.

The *render* step, :func:`render_manim_scene`, is a guarded adapter slot for the
heavy optional ``animation`` extra (manim). If manim is absent it raises
:class:`~democreate.errors.BackendUnavailableError`; if present, the concrete
renderer still needs to be wired.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from .._logging import get_logger
from ..errors import BackendUnavailableError

__all__ = ["build_code_scene_spec", "render_manim_scene"]

logger = get_logger(__name__)

# Per-line reveal pacing for the deterministic spec (ms). Chosen to read at a
# comfortable code-walkthrough pace; longer lines linger slightly longer.
_BASE_REVEAL_MS = 600
_PER_CHAR_MS = 12


def _reveal_duration_ms(line: str) -> int:
    """Return the reveal duration for one code line in milliseconds.

    Args:
        line: The source line (without trailing newline).

    Returns:
        A deterministic positive duration scaling mildly with line length.
    """
    return _BASE_REVEAL_MS + _PER_CHAR_MS * len(line.strip())


def build_code_scene_spec(
    code: str,
    *,
    title: str = "",
    language: str = "python",
) -> dict[str, Any]:
    """Build a JSON-serializable manim code-walkthrough scene description.

    The scene reveals the code one line at a time. Each reveal step records the
    1-based line number, its text, a cumulative reveal index, and a per-line
    duration. The result is pure data — render it later with
    :func:`render_manim_scene` (or any other backend).

    Args:
        code: The source code to walk through.
        title: Optional on-screen title for the scene.
        language: Lexer/grammar name for the code (informational; e.g. ``python``).

    Returns:
        A dict with keys ``kind``, ``title``, ``language``, ``code``, ``steps``,
        and ``total_duration_ms``. ``steps`` is a list of per-line dicts.
    """
    lines = code.splitlines()
    steps: list[dict[str, Any]] = []
    total = 0
    for index, line in enumerate(lines):
        duration = _reveal_duration_ms(line)
        steps.append(
            {
                "order": index,
                "line_no": index + 1,
                "text": line,
                "action": "reveal_line",
                "duration_ms": duration,
                "start_ms": total,
            }
        )
        total += duration

    return {
        "kind": "code_walkthrough",
        "title": title,
        "language": language,
        "code": code,
        "line_count": len(lines),
        "steps": steps,
        "total_duration_ms": total,
    }


def render_manim_scene(spec: dict[str, Any], out_path: Path) -> Path:  # pragma: no cover
    """Render a scene spec to a video file using manim.

    Args:
        spec: A scene description as produced by :func:`build_code_scene_spec`.
        out_path: Destination path for the rendered video.

    Returns:
        The path to the rendered file.

    Raises:
        BackendUnavailableError: If the ``manim`` package is not installed.
    """
    if importlib.util.find_spec("manim") is None:
        raise BackendUnavailableError("manim", extra="animation")

    # Real rendering path — exercised only when manim is installed, hence the
    # module-level ``# pragma: no cover`` on this function.
    import manim  # noqa: F401

    raise NotImplementedError(
        "manim rendering backend is installed but not yet wired up"
    )
