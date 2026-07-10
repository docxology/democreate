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
import json
from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError
from ..project_paths import relativize_under_root
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


def to_markdown(
    demo: Demo,
    *,
    format: str = "full",
) -> str:
    """Render the demo as a readable Markdown transcript.

    The document has an H1 title, an H2 per scene, and for each chunk the
    narration text followed by a bulleted list of its actions.

    Args:
        demo: The demo to render.
        format: Output shape — ``"full"`` (default, readable transcript with
            action bullets), ``"compact"`` (one line per scene: title and
            narration only, no actions), or ``"outline"`` (a nested bullet
            outline: demo title → scene titles → chunk first sentences).

    Returns:
        A Markdown string ending with a trailing newline.
    """
    if format == "compact":
        lines: list[str] = [f"# {demo.title}", ""]
        for scene in demo.scenes:
            heading = scene.title or scene.id
            narration = " ".join(c.text for c in scene.chunks if c.text)
            lines.append(f"## {heading}")
            lines.append(narration or "(no narration)")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    if format == "outline":
        lines = [f"# {demo.title}", ""]
        for scene in demo.scenes:
            heading = scene.title or scene.id
            lines.append(f"- **{heading}** ({scene.kind.value})")
            for chunk in scene.chunks:
                first = _first_clause(chunk.text)
                lines.append(f"  - {first}")
        return "\n".join(lines).rstrip() + "\n"

    # full (default)
    lines = [f"# {demo.title}", ""]
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


def _first_clause(text: str, *, limit: int = 80) -> str:
    """Return the first clause of ``text``, bounded to ``limit`` chars."""
    clean = " ".join(text.split())
    if not clean:
        return "(no narration)"
    for stop in (". ", "! ", "? "):
        idx = clean.find(stop)
        if 0 < idx < limit:
            return clean[: idx + 1].strip()
    return (clean[:limit].rstrip() + "…") if len(clean) > limit else clean


def to_json(
    demo: Demo, *, indent: int = 2, relative_to: Path | str | None = None
) -> str:
    """Serialize the demo to JSON.

    Args:
        demo: The demo to serialize.
        indent: Indentation passed through to :meth:`Demo.to_json`.
        relative_to: If given, rewrite absolute audio paths embedded by the
            render pipeline to paths relative to this workspace root, so the
            serialized demo is byte-stable across runs/machines.

    Returns:
        A JSON string round-trippable via :meth:`Demo.from_json`.
    """
    if relative_to is None:
        return demo.to_json(indent=indent)
    data = relativize_under_root(demo.to_dict(), relative_to)
    return json.dumps(data, indent=indent, ensure_ascii=False)


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


def _markdown_to_html(demo: Demo) -> str:
    """Convert the demo transcript to styled HTML for PDF rendering."""
    parts: list[str] = [
        "<html><head><meta charset='utf-8'>",
        "<style>",
        "body { font-family: 'Helvetica Neue', Arial, sans-serif; "
        "max-width: 48rem; margin: 2rem auto; line-height: 1.6; color: #1a1a1a; }",
        "h1 { font-size: 1.8rem; border-bottom: 2px solid #333; padding-bottom: .3rem; }",
        "h2 { font-size: 1.3rem; color: #333; margin-top: 2rem; }",
        "code, pre { font-family: 'SF Mono', 'Fira Code', monospace; "
        "background: #f4f4f4; padding: .1rem .3rem; border-radius: .2rem; }",
        "pre { padding: .8rem; overflow-x: auto; }",
        "ul { color: #555; }",
        ".meta { color: #888; font-size: .85rem; margin-top: 2rem; }",
        "</style></head><body>",
    ]
    parts.append(f"<h1>{html.escape(demo.title)}</h1>")
    for scene in demo.scenes:
        heading = html.escape(scene.title or scene.id)
        parts.append(f"<h2>{heading}</h2>")
        for chunk in scene.chunks:
            if chunk.text:
                parts.append(f"<p>{html.escape(chunk.text)}</p>")
            if chunk.actions:
                parts.append("<ul>")
                for action in chunk.actions:
                    parts.append(f"<li><code>{html.escape(_describe_action(action))}</code></li>")
                parts.append("</ul>")
    parts.append(
        f"<p class='meta'>Generated by DemoCreate — "
        f"{len(demo.scenes)} scenes, {len(demo.iter_chunks())} chunks, "
        f"{len(demo.iter_actions())} actions</p>"
    )
    parts.append("</body></html>")
    return "\n".join(parts)


def export_pdf(demo: Demo, out_path: Path) -> Path:  # pragma: no cover - needs engine
    """Render the demo transcript to a styled PDF.

    Produces a proper typeset document with headings, paragraphs, and inline
    code formatting — not a ``<pre>`` dump. Requires WeasyPrint. When it is
    unavailable this raises so the caller can fall back to :func:`to_markdown`,
    which is always available.

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

    out_path.parent.mkdir(parents=True, exist_ok=True)
    weasyprint.HTML(string=_markdown_to_html(demo)).write_pdf(str(out_path))
    return out_path
