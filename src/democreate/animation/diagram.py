"""Architecture / overview diagram renderer for demo frames.

A pure, deterministic Pillow renderer that turns a small declarative description
of an architecture — a title plus a set of named columns, each holding a vertical
stack of labeled nodes — into a clean, legible left-to-right diagram. It is built
for HD video frames: all text is sized relative to the frame height via
:mod:`democreate.animation.fonts`, boxes are rounded and sized to fit their text,
and light connectors are drawn between adjacent columns.

The renderer is a pure function of its inputs: no I/O, no randomness, no network,
and no heavy dependencies. :func:`democreate_architecture_image` packages the
canonical DemoCreate pipeline as a ready-to-render diagram.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PIL import Image, ImageDraw, ImageFont

from .._logging import get_logger
from .fonts import scaled_font

__all__ = [
    "DiagramNode",
    "render_architecture_diagram",
    "democreate_architecture_image",
]

logger = get_logger(__name__)

PillowFont = ImageFont.ImageFont | ImageFont.FreeTypeFont

# Text size ratios relative to frame height. Tuned so a 1080px frame yields a
# comfortable ~59px title down to ~26px sublabels.
_TITLE_RATIO = 0.055
_HEADER_RATIO = 0.034
_NODE_RATIO = 0.028
_SUB_RATIO = 0.022


@dataclass
class DiagramNode:
    """A single labeled box inside an architecture column.

    Args:
        label: The primary, prominent line of text for the box.
        sublabels: Optional smaller lines drawn beneath the label.
    """

    label: str
    sublabels: list[str] = field(default_factory=list)


def _text_size(
    draw: ImageDraw.ImageDraw, text: str, font: PillowFont
) -> tuple[int, int]:
    """Return the ``(width, height)`` of ``text`` rendered with ``font``.

    Args:
        draw: The drawing context used to measure.
        text: The string to measure.
        font: A Pillow font object.

    Returns:
        Pixel ``(width, height)`` of the text's bounding box.
    """
    left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
    return (int(right - left), int(bottom - top))


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Linearly blend two RGB colors.

    Args:
        a: The first color (returned when ``t`` is 0).
        b: The second color (returned when ``t`` is 1).
        t: Blend fraction in ``[0, 1]``.

    Returns:
        The interpolated RGB color.
    """
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))  # type: ignore[return-value]


def render_architecture_diagram(
    size: tuple[int, int],
    *,
    title: str,
    columns: list[tuple[str, list[DiagramNode]]],
    bg: tuple[int, int, int] = (13, 17, 23),
    accent: tuple[int, int, int] = (56, 139, 253),
    fg: tuple[int, int, int] = (230, 237, 243),
) -> Image.Image:
    """Render a clean left-to-right architecture diagram.

    Draws a large title across the top, then evenly-spaced labeled columns. Each
    column is a header above a vertical stack of rounded boxes — one per
    :class:`DiagramNode` — containing the node's label and any sublabels. Light
    arrows connect adjacent columns. All text is sized relative to ``size[1]`` so
    it stays legible at any resolution, and boxes are sized to fit their text.

    Args:
        size: ``(width, height)`` of the output image in pixels.
        title: The large heading drawn across the top.
        columns: Ordered ``(header, nodes)`` pairs; each becomes a column.
        bg: Background RGB color.
        accent: RGB color for headers, box borders, and connectors.
        fg: RGB color for body text.

    Returns:
        A :class:`PIL.Image.Image` of exactly ``size``.
    """
    width, height = int(size[0]), int(size[1])
    width = max(1, width)
    height = max(1, height)

    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)

    title_font = scaled_font(height, _TITLE_RATIO)
    header_font = scaled_font(height, _HEADER_RATIO)
    node_font = scaled_font(height, _NODE_RATIO)
    sub_font = scaled_font(height, _SUB_RATIO)

    margin = max(8, int(round(height * 0.045)))

    # --- Title across the top -------------------------------------------------
    title_w, title_h = _text_size(draw, title, title_font)
    title_x = max(margin, (width - title_w) // 2)
    title_y = margin
    draw.text((title_x, title_y), title, fill=fg, font=title_font)

    # Accent underline beneath the title.
    rule_y = title_y + title_h + max(4, int(round(height * 0.012)))
    draw.line(
        [(margin, rule_y), (width - margin, rule_y)],
        fill=accent,
        width=max(1, int(round(height * 0.003))),
    )

    content_top = rule_y + max(8, int(round(height * 0.03)))
    content_bottom = height - margin

    n_cols = len(columns)
    if n_cols == 0:
        return image

    gap = max(4, int(round(width * 0.02)))
    avail_w = width - 2 * margin - gap * (n_cols - 1)
    col_w = max(1, avail_w // n_cols)
    box_pad = max(4, int(round(height * 0.018)))
    line_gap = max(2, int(round(height * 0.006)))
    box_gap = max(6, int(round(height * 0.02)))
    radius = max(4, int(round(height * 0.018)))

    # Remember vertical box spans per column to route connectors sensibly.
    col_centers_y: list[list[int]] = []
    col_x_left: list[int] = []
    col_x_right: list[int] = []

    for ci, (header, nodes) in enumerate(columns):
        col_x = margin + ci * (col_w + gap)
        col_x_left.append(col_x)
        col_x_right.append(col_x + col_w)

        # Column header.
        _header_w, header_h = _text_size(draw, header, header_font)
        draw.text((col_x, content_top), header, fill=accent, font=header_font)

        stack_top = content_top + header_h + box_gap

        # Pre-compute each box's height from its text content.
        box_specs: list[tuple[int, list[tuple[str, PillowFont, int]]]] = []
        for node in nodes:
            lines: list[tuple[str, PillowFont, int]] = []
            lw, lh = _text_size(draw, node.label, node_font)
            lines.append((node.label, node_font, lh))
            for sub in node.sublabels:
                sw, sh = _text_size(draw, sub, sub_font)
                lines.append((sub, sub_font, sh))
            text_h = sum(lh for _, _, lh in lines) + line_gap * max(0, len(lines) - 1)
            box_h = text_h + 2 * box_pad
            box_specs.append((box_h, lines))

        total_boxes_h = sum(bh for bh, _ in box_specs)
        total_boxes_h += box_gap * max(0, len(box_specs) - 1)

        # Center the stack vertically in the available content region.
        region_h = content_bottom - stack_top
        y = stack_top + max(0, (region_h - total_boxes_h) // 2)

        centers: list[int] = []
        for box_h, lines in box_specs:
            box_top = y
            box_bottom = y + box_h
            draw.rounded_rectangle(
                [(col_x, box_top), (col_x + col_w, box_bottom)],
                radius=radius,
                fill=_mix(bg, accent, 0.12),
                outline=accent,
                width=max(1, int(round(height * 0.002))),
            )

            # Draw the text lines, vertically stacked and centered horizontally.
            ty = box_top + box_pad
            for text, fnt, lh in lines:
                tw, _ = _text_size(draw, text, fnt)
                tx = col_x + max(box_pad, (col_w - tw) // 2)
                draw.text((tx, ty), text, fill=fg, font=fnt)
                ty += lh + line_gap

            centers.append((box_top + box_bottom) // 2)
            y = box_bottom + box_gap

        col_centers_y.append(centers)

    # --- Connectors between adjacent columns ---------------------------------
    connector_w = max(1, int(round(height * 0.003)))
    arrow = max(4, int(round(height * 0.012)))
    for ci in range(n_cols - 1):
        left_centers = col_centers_y[ci]
        right_centers = col_centers_y[ci + 1]
        if not left_centers or not right_centers:
            continue
        x0 = col_x_right[ci]
        x1 = col_x_left[ci + 1]
        if x1 <= x0:
            continue
        # Route from the vertical midpoint of each column's stack.
        y0 = sum(left_centers) // len(left_centers)
        y1 = sum(right_centers) // len(right_centers)
        draw.line([(x0, y0), (x1, y1)], fill=accent, width=connector_w)
        # Simple arrowhead at the right end.
        draw.polygon(
            [
                (x1, y1),
                (x1 - arrow, y1 - arrow // 2),
                (x1 - arrow, y1 + arrow // 2),
            ],
            fill=accent,
        )

    return image


def democreate_architecture_image(
    size: tuple[int, int] = (1920, 1080),
    *,
    bg: tuple[int, int, int] = (13, 17, 23),
    accent: tuple[int, int, int] = (56, 139, 253),
    fg: tuple[int, int, int] = (230, 237, 243),
) -> Image.Image:
    """Render the canonical DemoCreate architecture as a diagram.

    Packages the four-stage DemoCreate pipeline — declarative spine, narration,
    render, and export — into columns and renders them via
    :func:`render_architecture_diagram`.

    Args:
        size: ``(width, height)`` of the output image in pixels.

    Returns:
        A :class:`PIL.Image.Image` of exactly ``size``.
    """
    columns: list[tuple[str, list[DiagramNode]]] = [
        (
            "Declarative Spine",
            [DiagramNode("Demo", ["scenes / chunks / actions"])],
        ),
        (
            "Narration",
            [
                DiagramNode("TTS", ["silent / system / kokoro"]),
                DiagramNode("Sync", ["TTS to STT"]),
            ],
        ),
        (
            "Render",
            [
                DiagramNode("Capture", ["synthetic frames"]),
                DiagramNode("Assembly", ["timeline + compositor"]),
                DiagramNode("Animation", ["waveform / zoom"]),
            ],
        ),
        (
            "Export",
            [
                DiagramNode("HD MP4", ["+ voiceover"]),
                DiagramNode("HTML player"),
                DiagramNode("Captions", ["JSON"]),
            ],
        ),
    ]
    return render_architecture_diagram(
        size,
        title="DemoCreate — Architecture",
        columns=columns,
        bg=bg,
        accent=accent,
        fg=fg,
    )
