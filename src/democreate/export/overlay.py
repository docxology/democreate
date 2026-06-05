"""On-screen top/bottom metadata bars — a broadcast-style provenance overlay.

This module draws configurable metadata bars at the **top** (header) and
**bottom** (footer) of a rendered frame, the way a TV broadcast pins a
station bug and a lower-third strap onto live video. The header carries the
demo title and the current section; the footer carries provenance —
author, source, a URL, an optional running clock, and a small persistent
watermark — set just above the very bottom edge so it never collides with a
waveform band drawn flush to the frame bottom.

Everything is pure Pillow plus :func:`democreate.animation.fonts.scaled_font`,
so the bars scale proportionally at any resolution. Drawing onto a translucent
RGBA layer and compositing it back gives the bars a semi-dark, see-through
look without mutating the frame's mode. Both drawing functions are no-ops when
their relevant fields are empty, so it is always safe to call them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ..animation.fonts import scaled_font

if TYPE_CHECKING:  # pragma: no cover
    from PIL import Image, ImageDraw, ImageFont

    from ..config import MetadataConfig

__all__ = [
    "OverlayInfo",
    "draw_header",
    "draw_footer",
    "format_clock",
    "from_metadata_config",
]

# Type aliases for the RGB color tuples the public API accepts.
RGB = tuple[int, int, int]

_DEFAULT_ACCENT: RGB = (56, 139, 253)
_DEFAULT_FG: RGB = (235, 238, 243)
_DEFAULT_BG: RGB = (0, 0, 0)


@dataclass
class OverlayInfo:
    """Resolved text for the on-screen metadata bars.

    A flat bag of already-formatted strings; the drawing functions place each
    field and skip anything left blank. ``clock`` is a preformatted readout
    such as ``"1:23 / 4:56"`` (see :func:`format_clock`) or ``""``.

    Attributes:
        title: Demo title, drawn at the header left.
        section: Current section/scene title, drawn at the header right.
        author: Creator name, drawn at the footer left.
        source: Source label (repo/paper/project), joined after the author.
        url: A URL drawn toward the footer center/right.
        watermark: Small persistent watermark text, drawn at the footer far right.
        clock: Preformatted ``"M:SS / M:SS"`` time readout, or ``""``.
    """

    title: str = ""
    section: str = ""
    author: str = ""
    source: str = ""
    url: str = ""
    watermark: str = ""
    clock: str = ""


def format_clock(t_ms: int, total_ms: int) -> str:
    """Format a ``current / total`` time readout for the footer clock.

    Both values are rendered ``M:SS`` (minutes are not zero-padded), promoting
    to ``H:MM:SS`` the moment either side reaches an hour. Negative inputs are
    clamped to zero.

    Args:
        t_ms: Current playback position in milliseconds.
        total_ms: Total duration in milliseconds.

    Returns:
        A string like ``"1:23 / 4:56"`` or ``"1:02:03 / 1:30:00"``.
    """
    use_hours = max(t_ms, total_ms) >= 3_600_000
    return f"{_fmt_time(t_ms, use_hours)} / {_fmt_time(total_ms, use_hours)}"


def _fmt_time(t_ms: int, use_hours: bool) -> str:
    """Format a single millisecond duration as ``M:SS`` or ``H:MM:SS``.

    Args:
        t_ms: Duration in milliseconds (clamped to zero if negative).
        use_hours: Force ``H:MM:SS`` form (with zero-padded minutes).

    Returns:
        The formatted time string.
    """
    total_seconds = max(0, t_ms) // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if use_hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def from_metadata_config(
    meta: MetadataConfig,
    *,
    title: str = "",
    section: str = "",
    clock: str = "",
) -> OverlayInfo:
    """Build an :class:`OverlayInfo` from a :class:`MetadataConfig`.

    All provenance fields are copied unconditionally — the caller decides
    whether to actually draw the bars based on ``meta.header`` / ``meta.footer``.
    The metadata's own ``title`` wins when set; otherwise the passed ``title``
    (typically the demo title) is used.

    Args:
        meta: A metadata config (duck-typed: ``author``/``source``/``url``/
            ``watermark``/``title``).
        title: Fallback title used when ``meta.title`` is empty.
        section: Current section/scene title for the header right.
        clock: Preformatted clock string for the footer, or ``""``.

    Returns:
        A populated :class:`OverlayInfo`.
    """
    return OverlayInfo(
        title=getattr(meta, "title", "") or title,
        section=section,
        author=getattr(meta, "author", "") or "",
        source=getattr(meta, "source", "") or "",
        url=getattr(meta, "url", "") or "",
        watermark=getattr(meta, "watermark", "") or "",
        clock=clock,
    )


def _composite_bar(
    image: Image.Image,
    box: tuple[int, int, int, int],
    bg: RGB,
    alpha: int,
) -> ImageDraw.ImageDraw:
    """Paint a translucent bar onto ``image`` and return a draw layer for text.

    Composites a semi-opaque ``bg`` rectangle over ``box`` so the underlying
    frame shows through, then returns a fresh ``ImageDraw`` bound to the
    (now-modified) image for placing text on top.

    Args:
        image: The frame being annotated (modified in place).
        box: ``(left, top, right, bottom)`` of the bar in pixels.
        bg: Bar fill color.
        alpha: Opacity of the bar, 0–255.

    Returns:
        An ``ImageDraw.ImageDraw`` for drawing text onto ``image``.
    """
    from PIL import Image as _Image
    from PIL import ImageDraw

    left, top, right, bottom = box
    width = max(1, right - left)
    height = max(1, bottom - top)
    base = image.convert("RGBA") if image.mode != "RGBA" else image
    bar = _Image.new("RGBA", (width, height), (*bg, alpha))
    base.alpha_composite(bar, dest=(left, top))
    if base is not image:
        image.paste(base.convert(image.mode))
    return ImageDraw.Draw(image)


def draw_header(
    image: Image.Image,
    info: OverlayInfo,
    *,
    accent: RGB = _DEFAULT_ACCENT,
    fg: RGB = _DEFAULT_FG,
    bg: RGB = _DEFAULT_BG,
) -> None:
    """Draw a slim translucent top bar: title (left) and section (right).

    The bar spans the full width at roughly the top 5% of the frame. The title
    is drawn in ``fg``, the section in ``accent``. If both ``info.title`` and
    ``info.section`` are empty the call is a silent no-op.

    Args:
        image: The frame to annotate (modified in place).
        info: Resolved overlay text.
        accent: Color for the section label (and emphasis).
        fg: Foreground text color for the title.
        bg: Bar background color (composited translucently).
    """
    if not info.title and not info.section:
        return

    width, height = image.size
    # Sit just below the window chrome + progress bar (~6–10.5% of height) so the
    # ribbon never collides with the title bar or the section pill.
    bar_top = int(round(height * 0.062))
    bar_bottom = int(round(height * 0.105))
    pad = max(1, int(round(width * 0.018)))
    draw = _composite_bar(image, (0, bar_top, width, bar_bottom), bg, alpha=150)

    font = scaled_font(height, 0.024)
    text_y = bar_top + (bar_bottom - bar_top - _text_height(draw, font)) // 2

    if info.title:
        draw.text((pad, text_y), info.title, font=font, fill=fg)
    if info.section:
        section_w = draw.textlength(info.section, font=font)
        draw.text((width - pad - section_w, text_y), info.section, font=font, fill=accent)


def draw_footer(
    image: Image.Image,
    info: OverlayInfo,
    *,
    accent: RGB = _DEFAULT_ACCENT,
    fg: RGB = _DEFAULT_FG,
    bg: RGB = _DEFAULT_BG,
) -> None:
    """Draw a slim translucent bottom bar of provenance, above the frame edge.

    The bar sits at roughly 88–93% of the frame height — high enough to clear a
    waveform band drawn flush to the bottom. Layout: ``author · source`` at the
    left, the URL toward the right, a watermark at the far right, and (if set)
    the clock just left of the watermark. Skipped silently when every field is
    empty.

    Args:
        image: The frame to annotate (modified in place).
        info: Resolved overlay text.
        accent: Color for the watermark/clock emphasis.
        fg: Foreground text color for author/source/url.
        bg: Bar background color (composited translucently).
    """
    if not any(
        (info.author, info.source, info.url, info.watermark, info.clock)
    ):
        return

    width, height = image.size
    # Sit at the very bottom edge (lowest ~4.5%), overlaid on the bottom of the
    # waveform band with a darker composite so text stays legible over the bars.
    bar_top = int(round(height * 0.955))
    bar_bottom = height
    pad = max(1, int(round(width * 0.018)))
    draw = _composite_bar(image, (0, bar_top, width, bar_bottom), bg, alpha=185)

    font = scaled_font(height, 0.020)
    text_y = bar_top + (bar_bottom - bar_top - _text_height(draw, font)) // 2

    # Left: "author · source".
    left_parts = [p for p in (info.author, info.source) if p]
    if left_parts:
        draw.text(
            (pad, text_y), " · ".join(left_parts), font=font, fill=fg
        )

    # Far right: watermark, in accent.
    right_x = float(width - pad)
    if info.watermark:
        wm_w = draw.textlength(info.watermark, font=font)
        right_x -= wm_w
        draw.text((right_x, text_y), info.watermark, font=font, fill=accent)
        right_x -= max(1, int(round(width * 0.012)))

    # Just left of the watermark: the clock, in accent.
    if info.clock:
        clock_w = draw.textlength(info.clock, font=font)
        right_x -= clock_w
        draw.text((right_x, text_y), info.clock, font=font, fill=accent)
        right_x -= max(1, int(round(width * 0.012)))

    # Center/right of remaining space: the URL.
    if info.url:
        url_w = draw.textlength(info.url, font=font)
        url_x = max(pad, right_x - url_w)
        draw.text((url_x, text_y), info.url, font=font, fill=fg)


def _text_height(
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
) -> int:
    """Return a representative pixel height for ``font`` (for vertical centering).

    Args:
        draw: An ``ImageDraw`` used to measure a reference glyph string.
        font: The font being measured.

    Returns:
        The bounding-box height of a representative ascender/descender sample.
    """
    bbox = draw.textbbox((0, 0), "Ag", font=font)
    return int(bbox[3] - bbox[1])
