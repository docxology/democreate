"""Document-format exports for a :class:`~democreate.schema.Demo`.

Pure, dependency-free conversions to text-y deliverables:

* :func:`to_markdown` — a readable transcript (title, per-scene sections, per-chunk
  narration with a bulleted action list).
* :func:`to_json` — passthrough to ``Demo.to_json`` for tooling.
* :func:`to_chapters` — a chapter list for HTML players and YouTube descriptions.

:func:`export_pdf` is guarded behind a Markdown-to-PDF engine and raises
:class:`~democreate.errors.BackendUnavailableError` when none is installed; the
pure :func:`to_markdown` output is always available as a fallback.
"""

from __future__ import annotations

import html
import importlib.util
from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError
from ..schema import Action, Demo

__all__ = ["to_markdown", "to_json", "to_chapters", "export_pdf"]

logger = get_logger(__name__)


def _describe_action(action: Action) -> str:
    """Return a one-line human description of an action for the transcript."""
    label = action.type.value.replace("_", " ")
    detail = ""
    params = action.params
    for key in ("path", "command", "url", "code", "text", "lines", "selector"):
        if key in params:
            detail = f" — `{params[key]}`"
            break
    trigger = f" (on “{action.trigger_word}”)" if action.trigger_word else ""
    return f"{label}{detail}{trigger}"


def to_markdown(demo: Demo) -> str:
    """Render the demo as a readable Markdown transcript.

    The document has an H1 title, an H2 per scene, and for each chunk the
    narration text followed by a bulleted list of its actions.

    Args:
        demo: The demo to render.

    Returns:
        A Markdown string ending with a trailing newline.
    """
    lines: list[str] = [f"# {demo.title}", ""]
    for scene in demo.scenes:
        heading = scene.title or scene.id
        lines.append(f"## {heading}")
        lines.append("")
        for chunk in scene.chunks:
            if chunk.text:
                lines.append(chunk.text)
                lines.append("")
            if chunk.actions:
                for action in chunk.actions:
                    lines.append(f"- {_describe_action(action)}")
                lines.append("")
    text = "\n".join(lines).rstrip() + "\n"
    return text


def to_json(demo: Demo, *, indent: int = 2) -> str:
    """Serialize the demo to JSON.

    Args:
        demo: The demo to serialize.
        indent: Indentation passed through to :meth:`Demo.to_json`.

    Returns:
        A JSON string round-trippable via :meth:`Demo.from_json`.
    """
    return demo.to_json(indent=indent)


def to_chapters(demo: Demo) -> list[dict]:
    """Build a chapter list for players and YouTube descriptions.

    One chapter per scene, anchored to the running estimated start time of the
    scene (sum of prior scenes' estimated durations). A scene's own
    first-chunk ``start_ms`` is preferred when the sync engine has filled it in.

    Args:
        demo: The demo to map.

    Returns:
        A list of ``{"title", "scene_id", "start_ms"}`` dicts, scene-ordered.
    """
    chapters: list[dict] = []
    cursor = 0
    for scene in demo.scenes:
        start = cursor
        if scene.chunks and scene.chunks[0].start_ms is not None:
            start = scene.chunks[0].start_ms
        chapters.append(
            {
                "title": scene.title or scene.id,
                "scene_id": scene.id,
                "start_ms": start,
            }
        )
        cursor = start + scene.estimated_duration_ms()
    return chapters


def _has_pdf_engine() -> bool:
    """Return ``True`` if WeasyPrint is importable."""
    return importlib.util.find_spec("weasyprint") is not None


def export_pdf(demo: Demo, out_path: Path) -> Path:  # pragma: no cover - needs engine
    """Render the demo transcript to a PDF.

    Requires WeasyPrint. When it is unavailable this raises so the caller can
    fall back to :func:`to_markdown`, which is always available.

    Args:
        demo: The demo to render.
        out_path: Destination ``.pdf`` path.

    Returns:
        ``out_path``.

    Raises:
        BackendUnavailableError: If no Markdown→PDF engine is installed.
    """
    if not _has_pdf_engine():
        raise BackendUnavailableError("pdf", extra="docs")

    import weasyprint

    markdown = to_markdown(demo)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    escaped_markdown = html.escape(markdown)
    weasyprint.HTML(string=f"<pre>{escaped_markdown}</pre>").write_pdf(str(out_path))
    return out_path
