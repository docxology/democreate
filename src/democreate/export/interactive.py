"""Export a caption/chapter HTML preview with optional local frame images.

JavaScript and CSS are inline; referenced PNGs must accompany the HTML file for
offline viewing. This preview has no audio track or audible narration playback.
"""

from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from .._logging import get_logger
from ..schema import Demo

__all__ = ["export_html_player", "build_timeline"]

logger = get_logger(__name__)

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_TEMPLATE_NAME = "player.html.j2"


def build_timeline(demo: Demo) -> dict:
    """Build a deterministic caption/chapter timeline from a demo.

    Each chunk becomes a caption cue. A cue's ``start_ms`` is the chunk's own
    ``start_ms`` if the sync engine has filled it in, otherwise the running sum of
    measured playback durations (falling back to estimates before synthesis).
    Each scene becomes a chapter anchored to its first chunk's start (or the
    running cursor when a scene has no chunks).

    Args:
        demo: The demo to lay out.

    Returns:
        A dict with ``"captions"`` (list of ``{chunk_id, scene_id, text,
        start_ms, end_ms, frame}``), ``"chapters"`` (list of ``{title, scene_id,
        start_ms}``), and ``"total_ms"`` (the timeline length).
    """
    captions: list[dict] = []
    chapters: list[dict] = []
    cursor = 0
    frame_index = 0  # global, matches the compositor's frame_NNNN.png numbering
    for scene in demo.scenes:
        chapter_start = cursor
        first = True
        for chunk in scene.chunks:
            start = chunk.start_ms if chunk.start_ms is not None else cursor
            end = start + chunk.playback_duration_ms()
            if first:
                chapter_start = start
                first = False
            captions.append(
                {
                    "chunk_id": chunk.id,
                    "scene_id": scene.id,
                    "text": chunk.text,
                    "start_ms": start,
                    "end_ms": end,
                    "frame": f"frame_{frame_index:04d}.png",
                }
            )
            cursor = end
            frame_index += 1
        chapters.append(
            {
                "title": scene.title or scene.id,
                "scene_id": scene.id,
                "start_ms": chapter_start,
            }
        )
    return {"captions": captions, "chapters": chapters, "total_ms": cursor}


def _script_json(value: object) -> Markup:
    """JSON-encode ``value`` for safe embedding inside a ``<script>`` block.

    HTML autoescaping must NOT apply to JSON inside ``<script>`` (browsers do not
    HTML-decode there, so ``&#34;`` would be literal and break ``JSON.parse``).
    Instead we mark the JSON safe but neutralize the sequences that could
    terminate the script element or be reinterpreted by the HTML parser:
    ``<``, ``>``, ``&``, and the U+2028 / U+2029 line separators.

    Args:
        value: Any JSON-serializable object.

    Returns:
        A :class:`markupsafe.Markup` string ready to drop into a template
        without further escaping.
    """
    text = json.dumps(value, ensure_ascii=False)
    text = (
        text.replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace(chr(0x2028), "\\u2028")
        .replace(chr(0x2029), "\\u2029")
    )
    return Markup(text)


def _environment() -> Environment:
    """Return a Jinja2 environment bound to the package templates directory."""
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml", "j2"]),
    )


def export_html_player(
    demo: Demo,
    timeline: dict | None,
    out_path: Path,
    *,
    frames_dir: str | None = None,
) -> Path:
    """Render a caption/chapter preview referencing sibling frame assets.

    This preview has a logical timer, not synthesized-audio playback.

    Args:
        demo: The demo to present.
        timeline: A timeline dict (as produced by :func:`build_timeline`) to use
            verbatim; when ``None`` one is computed from chunk timings.
        out_path: Destination ``.html`` path. Parent directories are created.
        frames_dir: Optional relative directory (served alongside the HTML) that
            holds the compositor's numbered frames (``frame_%04d.png``); when
            given, the player shows the current frame as an ``<img>``.

    Returns:
        ``out_path``.
    """
    tl = timeline if timeline is not None else build_timeline(demo)
    captions = tl.get("captions", [])
    chapters = tl.get("chapters", [])
    total_ms = (
        tl["total_ms"] if "total_ms" in tl else build_timeline(demo)["total_ms"]
    )

    env = _environment()
    template = env.get_template(_TEMPLATE_NAME)
    html = template.render(
        title=demo.title,
        chapters=chapters,
        frames_dir=frames_dir,
        captions_json=_script_json(captions),
        chapters_json=_script_json(chapters),
        frames_dir_json=_script_json(frames_dir),
        total_ms=int(total_ms),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    logger.info("wrote HTML player → %s", out_path)
    return out_path
