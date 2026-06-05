"""Poster/thumbnail frame and GIF preview export.

Two presentation-layer helpers for surfacing a demo at a glance:

* :func:`render_poster` paints a designed still — themed background, the demo
  title (large, word-wrapped), an optional subtitle, and a thin accent rule —
  suitable as a video poster frame, social thumbnail, or chapter card. It is a
  pure function of its inputs and uses only Pillow (a core dependency).
* :func:`demo_to_gif` down-samples a long frame sequence to an animated GIF
  preview by evenly picking up to ``max_frames`` frames (always keeping the
  first and last) and delegating the encode to
  :func:`democreate.export.video.frames_to_gif`.

Both are deterministic and import no heavy or optional dependencies at module
top level.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from .._logging import get_logger
from ..config import Theme
from .video import frames_to_gif

if TYPE_CHECKING:  # pragma: no cover
    from PIL import ImageDraw, ImageFont

    from ..schema import Demo

__all__ = [
    "render_poster",
    "demo_to_gif",
]

logger = get_logger(__name__)


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont | ImageFont.FreeTypeFont,
    max_width: int,
) -> list[str]:
    """Greedily word-wrap ``text`` so each line fits within ``max_width`` pixels.

    Args:
        draw: An ``ImageDraw`` used to measure rendered text width.
        text: The text to wrap (whitespace-delimited words).
        font: The font the text will be drawn with.
        max_width: Maximum line width in pixels.

    Returns:
        A list of lines (never empty; a single overlong word stays on its own line).
    """
    words = text.split()
    if not words:
        return [""]

    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        candidate = f"{current} {word}"
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def render_poster(
    demo: Demo,
    out_path: Path,
    *,
    size: tuple[int, int] = (1920, 1080),
    theme: Theme | None = None,
    subtitle: str | None = None,
) -> Path:
    """Render a designed poster/thumbnail PNG for a demo.

    Paints a themed background, the demo title (large, word-wrapped and centered),
    an optional subtitle (defaulting to a ``"<N> scenes · <duration>s"`` summary),
    and a thin horizontal accent rule beneath the title. Fonts are sized relative
    to the frame height via :func:`democreate.animation.fonts.scaled_font` so text
    stays crisp at any resolution. The output is fully deterministic.

    Args:
        demo: The demo to render a poster for (uses its title, scenes, duration).
        out_path: Destination ``.png`` path. Parent directories are created.
        size: Output ``(width, height)`` in pixels.
        theme: Theme to color the poster, or ``None`` for the default :class:`Theme`.
        subtitle: Explicit subtitle text, or ``None`` to use a generated summary.

    Returns:
        ``out_path``.

    Raises:
        ValueError: If ``size`` has a non-positive dimension.
    """
    from PIL import Image, ImageDraw

    from ..animation.fonts import scaled_font

    width, height = size
    if width <= 0 or height <= 0:
        raise ValueError(f"poster size must be positive, got {width}x{height}")

    theme = theme if theme is not None else Theme()

    img = Image.new("RGB", (width, height), color=theme.bg_slide)
    draw = ImageDraw.Draw(img)

    margin = int(width * 0.08)
    max_text_width = width - 2 * margin

    title_font = scaled_font(height, theme.title_ratio)
    subtitle_font = scaled_font(height, theme.subtitle_ratio)

    title = demo.title.strip() or "Untitled Demo"
    title_lines = _wrap_text(draw, title, title_font, max_text_width)

    # Measure the title block height to vertically center the whole composition.
    line_heights: list[int] = []
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        line_heights.append(int(bbox[3] - bbox[1]))
    line_gap = int(max(line_heights) * 0.28) if line_heights else 0
    title_block_h = sum(line_heights) + line_gap * (len(title_lines) - 1)

    if subtitle is None:
        n_scenes = len(demo.scenes)
        duration_s = round(demo.estimated_duration_ms() / 1000)
        scene_word = "scene" if n_scenes == 1 else "scenes"
        subtitle = f"{n_scenes} {scene_word} · {duration_s}s"

    rule_gap = int(height * 0.04)
    rule_thickness = max(2, int(height * 0.006))
    rule_width = int(max_text_width * 0.32)
    sub_bbox = draw.textbbox((0, 0), subtitle, font=subtitle_font)
    sub_h = sub_bbox[3] - sub_bbox[1]
    sub_gap = int(height * 0.045)

    composition_h = title_block_h + rule_gap + rule_thickness + sub_gap + sub_h
    y = max(margin, (height - composition_h) // 2)

    # Draw the title lines, centered horizontally.
    for line, lh in zip(title_lines, line_heights, strict=True):
        line_w = draw.textlength(line, font=title_font)
        x = (width - line_w) / 2
        bbox = draw.textbbox((0, 0), line, font=title_font)
        # Offset by the bbox top so ascenders/descenders sit on a stable baseline.
        draw.text((x, y - bbox[1]), line, font=title_font, fill=theme.text)
        y += lh + line_gap
    y -= line_gap

    # Thin accent rule, centered.
    y += rule_gap
    rule_x0 = (width - rule_width) / 2
    draw.rectangle(
        [rule_x0, y, rule_x0 + rule_width, y + rule_thickness],
        fill=theme.accent,
    )
    y += rule_thickness + sub_gap

    # Subtitle, centered and dimmed.
    sub_w = draw.textlength(subtitle, font=subtitle_font)
    sub_x = (width - sub_w) / 2
    draw.text(
        (sub_x, y - sub_bbox[1]),
        subtitle,
        font=subtitle_font,
        fill=theme.dim,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, format="PNG")
    logger.info("wrote poster (%dx%d) → %s", width, height, out_path)
    return out_path


def _sample_indices(count: int, max_frames: int) -> list[int]:
    """Pick up to ``max_frames`` evenly-spaced indices from ``range(count)``.

    The first and last indices are always included; interior indices are spread
    as evenly as integer arithmetic allows. Order is preserved and indices are
    unique.

    Args:
        count: Number of available frames (``>= 1``).
        max_frames: Maximum number of indices to return (``>= 1``).

    Returns:
        A sorted list of distinct indices, length ``min(count, max_frames)``.
    """
    if count <= max_frames:
        return list(range(count))
    if max_frames == 1:
        return [0]

    indices: list[int] = []
    step = (count - 1) / (max_frames - 1)
    for i in range(max_frames):
        indices.append(round(i * step))
    # Deduplicate while preserving order (rounding can collide on dense steps).
    seen: set[int] = set()
    unique: list[int] = []
    for idx in indices:
        if idx not in seen:
            seen.add(idx)
            unique.append(idx)
    return unique


def demo_to_gif(
    frame_paths: list[Path],
    out_path: Path,
    *,
    fps: int = 8,
    max_frames: int = 48,
) -> Path:
    """Build an animated GIF preview by evenly sampling a frame sequence.

    Evenly down-samples ``frame_paths`` to at most ``max_frames`` frames (always
    keeping the first and last, order preserved), then delegates the encode to
    :func:`democreate.export.video.frames_to_gif`.

    Args:
        frame_paths: Ordered list of image files to preview.
        out_path: Destination ``.gif`` path. Parent directories are created.
        fps: Playback frame rate of the GIF.
        max_frames: Maximum number of frames to include in the preview.

    Returns:
        ``out_path``.

    Raises:
        ValueError: If ``frame_paths`` is empty, or ``max_frames``/``fps`` is not
            positive.
    """
    if not frame_paths:
        raise ValueError("demo_to_gif requires at least one frame")
    if max_frames <= 0:
        raise ValueError(f"max_frames must be positive, got {max_frames}")
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")

    indices = _sample_indices(len(frame_paths), max_frames)
    sampled = [frame_paths[i] for i in indices]
    logger.info(
        "sampling %d of %d frame(s) for GIF preview", len(sampled), len(frame_paths)
    )
    return frames_to_gif(sampled, out_path, fps=fps)
