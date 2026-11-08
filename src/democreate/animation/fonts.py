"""Scalable, host-independent fonts from Pillow's bundled default face.

No operating-system font discovery: identical pinned Pillow builds use the same
font bytes. ``size`` scales the bundled TrueType face for HD/4K output.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from PIL import ImageFont

__all__ = ["load_font", "scaled_font"]


@lru_cache(maxsize=64)
def load_font(size: int, *, mono: bool = False) -> ImageFont.FreeTypeFont:
    """Load Pillow's bundled TrueType face at ``size`` px.

    Args:
        size: Pixel size of the font.
        mono: Semantic code-font hint; the bundled face is used for both styles.

    Returns:
        A Pillow font object usable with ``ImageDraw.text``.
    """
    from PIL import ImageFont

    default_font = ImageFont.load_default(size=max(1, int(size)))
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
