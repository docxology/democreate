"""Shared media value types used across capture, narration, and assembly.

These are deliberately small, dependency-free dataclasses that several
subsystems exchange. Keeping them in one module prevents the definitions from
drifting apart between producers (TTS, capture) and consumers (sync, assembly).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .schema import SceneKind

__all__ = ["AudioClip", "FrameState"]


@dataclass
class AudioClip:
    """A rendered narration audio file and its measured properties.

    Attributes:
        path: Filesystem path to the audio (typically a ``.wav``).
        duration_ms: Measured duration in milliseconds.
        sample_rate: Audio sample rate in Hz.
        text: The narration text this clip was synthesized from.
        chunk_id: The id of the :class:`~democreate.schema.Chunk` it belongs to.
    """

    path: Path
    duration_ms: int
    sample_rate: int = 22050
    text: str = ""
    chunk_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "duration_ms": self.duration_ms,
            "sample_rate": self.sample_rate,
            "text": self.text,
            "chunk_id": self.chunk_id,
        }


@dataclass
class FrameState:
    """A renderable snapshot of the virtual environment at one instant.

    The synthetic renderer turns a ``FrameState`` into an image; the compositor
    builds a timeline of them. Producers fill only the fields relevant to the
    scene kind (e.g. a terminal scene leaves ``code_lines`` empty).

    Attributes:
        scene_kind: Which surface is on screen (editor, terminal, browser, slide).
        title: Window/title-bar text (e.g. the open file or page title).
        caption: The narration subtitle to overlay for this frame.
        file_path: Path label shown in an editor frame.
        code_lines: Lines of code displayed in an editor frame.
        highlight_lines: 1-based line numbers to emphasize.
        cursor_typed: Number of characters revealed so far (for typing animation).
        terminal_lines: Lines shown in a terminal frame.
        url: Address-bar text for a browser frame.
        cursor_xy: Optional ``(x, y)`` cursor position in pixels.
        scale: Camera zoom factor (1.0 == no zoom).
        background_image: Optional path to a full-frame background image (e.g. a
            real browser screenshot or a generated architecture diagram). When set,
            the renderer fits it behind the chrome and overlays caption/header.
        section: Optional section/chapter label shown in the top chrome.
        subtitle: Optional larger headline text for slide-style frames.
        bullets: Optional bullet-list items for a slide (rendered as a packed,
            distributed list rather than a floating title).
        stats: Optional ``(value, label)`` pairs for a slide, drawn as a row of
            big-number stat cards.
    """

    scene_kind: SceneKind = SceneKind.CODEBASE
    title: str = ""
    caption: str = ""
    file_path: str = ""
    code_lines: list[str] = field(default_factory=list)
    highlight_lines: list[int] = field(default_factory=list)
    cursor_typed: int | None = None
    terminal_lines: list[str] = field(default_factory=list)
    url: str = ""
    cursor_xy: tuple[int, int] | None = None
    scale: float = 1.0
    background_image: str | None = None
    section: str = ""
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    stats: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_kind": self.scene_kind.value,
            "title": self.title,
            "caption": self.caption,
            "file_path": self.file_path,
            "code_lines": list(self.code_lines),
            "highlight_lines": list(self.highlight_lines),
            "cursor_typed": self.cursor_typed,
            "terminal_lines": list(self.terminal_lines),
            "url": self.url,
            "cursor_xy": list(self.cursor_xy) if self.cursor_xy else None,
            "scale": self.scale,
            "background_image": self.background_image,
            "section": self.section,
            "subtitle": self.subtitle,
            "bullets": list(self.bullets),
            "stats": [list(s) for s in self.stats],
        }
