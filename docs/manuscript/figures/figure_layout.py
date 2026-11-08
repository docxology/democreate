"""Small, bounded Pillow layouts shared by the manuscript schematics.

All text uses the package's bundled font. Layout fails rather than silently
cropping text; figures contain no host-font discovery or external assets.
"""

from __future__ import annotations

from PIL import ImageDraw

from democreate.animation.fonts import load_font

__all__ = ["ACCENT", "BG", "DIM", "FG", "PANEL", "arrow", "card", "text"]

BG = (12, 12, 14)
PANEL = (22, 22, 26)
FG = (242, 242, 244)
DIM = (182, 182, 190)
ACCENT = (244, 90, 100)


def _lines(draw: ImageDraw.ImageDraw, value: str, size: int, width: int) -> list[str]:
    """Wrap paragraphs and long identifiers without discarding content."""
    font = load_font(size)
    lines: list[str] = []
    for paragraph in value.split("\n"):
        current = ""
        for word in paragraph.split():
            trial = f"{current} {word}" if current else word
            if draw.textlength(trial, font=font) <= width:
                current = trial
                continue
            if current:
                lines.append(current)
                current = ""
            for char in word:
                if current and draw.textlength(current + char, font=font) > width:
                    lines.append(current)
                    current = ""
                current += char
        lines.append(current)
    return lines


def text(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    value: str,
    *,
    size: int = 30,
    minimum: int | None = None,
    fill: tuple[int, int, int] = FG,
) -> int:
    """Draw complete wrapped text inside a box and return its occupied height.

    Font reduction is bounded by ``minimum`` (defaults to ``size``). Long hashes
    can wrap, but are never shortened. Explicit newlines separate paragraphs.
    """
    x0, y0, x1, y1 = box
    floor = size if minimum is None else minimum
    for pixels in range(size, floor - 1, -1):
        lines = _lines(draw, value, pixels, x1 - x0)
        step = int(pixels * 1.32)
        if len(lines) * step <= y1 - y0:
            font = load_font(pixels)
            for index, line in enumerate(lines):
                draw.text((x0, y0 + index * step), line, font=font, fill=fill,
                          anchor="lt")
            return len(lines) * step
    raise ValueError(f"figure text does not fit its box: {value!r}")


def card(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    label: str,
    heading: str,
    body: str,
    *,
    foot: str = "",
    size: int = 30,
    surface: tuple[int, int, int] = PANEL,
    foreground: tuple[int, int, int] = FG,
    accent: tuple[int, int, int] = ACCENT,
) -> None:
    """Draw a card with distinct category, heading, body and boundary note."""
    x0, y0, x1, y1 = box
    pad = max(22, size)
    left, right = x0 + pad, x1 - pad
    draw.rounded_rectangle(box, radius=16, fill=surface, outline=accent, width=2)
    y = y0 + pad
    y += text(draw, (left, y, right, y + size * 2), label,
              size=size - 4, fill=accent)
    y += 14
    y += text(draw, (left, y, right, y + size * 4), heading,
              size=size + 8, fill=foreground)
    y += 24
    foot_height = 0
    if foot:
        foot_height = len(_lines(draw, foot, size - 4, right - left))
        foot_height *= int((size - 4) * 1.32)
        text(draw, (left, y1 - pad - foot_height, right, y1 - pad), foot,
             size=size - 4, fill=accent)
        draw.line((left, y1 - pad - foot_height - 16,
                   right, y1 - pad - foot_height - 16), fill=accent, width=1)
    body_bottom = y1 - pad - foot_height - (32 if foot else 0)
    text(draw, (left, y, right, body_bottom), body,
         size=size, minimum=size - 2, fill=foreground)


def arrow(draw: ImageDraw.ImageDraw, start: tuple[int, int], end: tuple[int, int]) -> None:
    """Connect horizontal stages with a small explicit direction marker."""
    x, y = end
    draw.line((start, end), fill=ACCENT, width=3)
    draw.polygon(((x, y), (x - 12, y - 8), (x - 12, y + 8)), fill=ACCENT)
