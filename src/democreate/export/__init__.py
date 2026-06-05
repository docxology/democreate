"""Export subsystem — turn a :class:`~democreate.schema.Demo` into deliverables.

This package converts the deterministic spine artifacts (a ``Demo`` plus its
rendered frames and audio) into shareable outputs:

* :mod:`democreate.export.video` — build the ``ffmpeg`` argv for an MP4 encode
  (pure) and assemble an animated GIF straight from frames with Pillow (pure).
  Actually shelling out to ``ffmpeg`` is guarded behind a backend check.
* :mod:`democreate.export.interactive` — render a self-contained, dependency-free
  HTML5 player (Jinja2, a core dep) with a chapter sidebar and caption track.
* :mod:`democreate.export.formats` — readable transcript (Markdown), JSON, and a
  chapter list for players/YouTube. PDF is guarded behind a backend check.

Everything except the explicitly-guarded ``ffmpeg``/PDF paths runs with only the
core dependencies (pyyaml, typer, rich, jinja2, pillow) and is fully testable.
"""

from __future__ import annotations

from .formats import export_pdf, to_chapters, to_json, to_markdown
from .interactive import export_html_player
from .video import build_ffmpeg_command, export_video, frames_to_gif

__all__ = [
    "build_ffmpeg_command",
    "frames_to_gif",
    "export_video",
    "export_html_player",
    "to_markdown",
    "to_json",
    "to_chapters",
    "export_pdf",
]
