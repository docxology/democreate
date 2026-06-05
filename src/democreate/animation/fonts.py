"""Scalable font resolution for crisp, large frame text.

The synthetic renderer's original ``ImageFont.load_default()`` is a ~10px bitmap
font — illegible at 1080p. This module resolves a real **TrueType** font from the
operating system (so glyphs scale to any size) and exposes helpers to size text
relative to the frame height, which is what keeps titles and captions readable on
an HD video.

Resolution is best-effort and cached: if no system TrueType font is found, it
degrades to the bitmap default rather than failing — the renderer still produces a
frame, just a smaller-text one.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from PIL import ImageFont

__all__ = [
    "resolve_font_path",
    "load_font",
    "scaled_font",
    "SANS_CANDIDATES",
    "MONO_CANDIDATES",
]

# Ordered preference of common system fonts across macOS and Linux. The first
# readable file wins. ``.ttc`` collections are supported via a face index.
SANS_CANDIDATES: tuple[tuple[str, int], ...] = (
    ("/System/Library/Fonts/SFNS.ttf", 0),
    ("/System/Library/Fonts/Helvetica.ttc", 0),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", 0),
    ("/System/Library/Fonts/Geneva.ttf", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 0),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", 0),
    ("/usr/share/fonts/TTF/DejaVuSans.ttf", 0),
)

MONO_CANDIDATES: tuple[tuple[str, int], ...] = (
    ("/System/Library/Fonts/SFNSMono.ttf", 0),
    ("/System/Library/Fonts/Menlo.ttc", 0),
    ("/System/Library/Fonts/Monaco.ttf", 0),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 0),
    ("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf", 0),
    ("/usr/share/fonts/TTF/DejaVuSansMono.ttf", 0),
)


@lru_cache(maxsize=2)
def resolve_font_path(*, mono: bool = False) -> tuple[str, int] | None:
    """Return ``(path, face_index)`` of the first available system font, or ``None``.

    Args:
        mono: Prefer a monospaced font (for code/terminal frames).

    Returns:
        A ``(path, index)`` tuple, or ``None`` if no candidate file exists.
    """
    candidates = MONO_CANDIDATES if mono else SANS_CANDIDATES
    for path, index in candidates:
        if Path(path).exists():
            return (path, index)
    return None


@lru_cache(maxsize=64)
def load_font(size: int, *, mono: bool = False) -> ImageFont.FreeTypeFont:
    """Load a TrueType font at ``size`` px, cached, with a bitmap fallback.

    Args:
        size: Pixel size of the font.
        mono: Prefer a monospaced face.

    Returns:
        A Pillow font object usable with ``ImageDraw.text``.
    """
    from PIL import ImageFont

    size = max(1, int(size))
    resolved = resolve_font_path(mono=mono)
    if resolved is not None:
        path, index = resolved
        try:
            return ImageFont.truetype(path, size=size, index=index)
        except OSError:  # pragma: no cover - defensive (unreadable font file)
            pass
    default_font = ImageFont.load_default(size=size)
    assert isinstance(default_font, ImageFont.FreeTypeFont)
    return default_font


def scaled_font(
    frame_height: int, ratio: float, *, mono: bool = False
) -> ImageFont.FreeTypeFont:
    """Load a font sized to a fraction of the frame height.

    This is how text stays proportionally large across resolutions: a title at
    ``ratio=0.06`` of a 1080px frame is a comfortable ~64px.

    Args:
        frame_height: Height of the target frame in pixels.
        ratio: Font size as a fraction of ``frame_height`` (e.g. ``0.03``).
        mono: Prefer a monospaced face.

    Returns:
        A Pillow font object.
    """
    return load_font(max(1, int(round(frame_height * ratio))), mono=mono)
