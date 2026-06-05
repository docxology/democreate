"""Pure Pillow image effects for the assembly stage.

A small library of deterministic, size-preserving transforms applied to rendered
frames: fades to/from black, crossfades between two frames, highlight boxes for
drawing attention, and lower-third caption bands. Every function takes and
returns a :class:`PIL.Image.Image` and depends only on Pillow (a core
dependency), so the whole module is import-safe and fully testable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._logging import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from PIL import Image as _ImageModule

logger = get_logger(__name__)

__all__ = [
    "fade",
    "crossfade",
    "highlight_box",
    "lower_third",
]


def _clamp01(value: float) -> float:
    """Clamp ``value`` into the closed interval ``[0.0, 1.0]``."""
    if value < 0.0:
        return 0.0
    if value > 1.0:
        return 1.0
    return value


def fade(image: _ImageModule.Image, alpha: float) -> _ImageModule.Image:
    """Fade ``image`` toward black.

    Args:
        image: Source image.
        alpha: Visibility of the source, ``0.0`` (full black) to ``1.0``
            (unchanged). Values outside the range are clamped.

    Returns:
        A new image the same size as ``image``.
    """
    from PIL import Image

    a = _clamp01(alpha)
    black = Image.new(image.mode, image.size, 0)
    return Image.blend(black, image.convert(image.mode), a)


def crossfade(
    a: _ImageModule.Image, b: _ImageModule.Image, t: float
) -> _ImageModule.Image:
    """Blend from image ``a`` to image ``b``.

    Args:
        a: Start image.
        b: End image (resized to ``a``'s size if it differs).
        t: Interpolation factor, ``0.0`` (pure ``a``) to ``1.0`` (pure ``b``).
            Values outside the range are clamped.

    Returns:
        A new image the same size as ``a``.
    """
    from PIL import Image

    factor = _clamp01(t)
    b_aligned = b if b.size == a.size else b.resize(a.size)
    if b_aligned.mode != a.mode:
        b_aligned = b_aligned.convert(a.mode)
    return Image.blend(a, b_aligned, factor)


def highlight_box(
    image: _ImageModule.Image,
    box: tuple[int, int, int, int],
    *,
    color: tuple[int, int, int] = (255, 214, 0),
    width: int = 4,
) -> _ImageModule.Image:
    """Draw a rectangular highlight outline on a copy of ``image``.

    Args:
        image: Source image (not mutated).
        box: ``(left, top, right, bottom)`` in pixels.
        color: Outline RGB color.
        width: Outline thickness in pixels.

    Returns:
        A new image the same size as ``image`` with the box drawn.
    """
    from PIL import ImageDraw

    out = image.copy()
    draw = ImageDraw.Draw(out)
    draw.rectangle(box, outline=color, width=width)
    return out


def lower_third(
    image: _ImageModule.Image,
    text: str,
    *,
    height: int = 120,
) -> _ImageModule.Image:
    """Overlay a translucent caption band ("lower third") at the bottom.

    Args:
        image: Source image (not mutated).
        text: Caption text to render in the band.
        height: Band height in pixels (clamped to the image height).

    Returns:
        A new image the same size as ``image`` with the band and text drawn.
    """
    from PIL import Image, ImageDraw

    out = image.convert("RGB").copy()
    img_w, img_h = out.size
    band_h = min(max(height, 0), img_h)
    if band_h == 0:
        return out

    band = Image.new("RGB", (img_w, band_h), (0, 0, 0))
    overlay = Image.blend(
        out.crop((0, img_h - band_h, img_w, img_h)), band, 0.6
    )
    out.paste(overlay, (0, img_h - band_h))

    draw = ImageDraw.Draw(out)
    draw.text((24, img_h - band_h + max(band_h // 2 - 8, 0)), text, fill=(255, 255, 255))
    return out
