"""Syntax-highlighted code rendering for demo frames.

Three pure, deterministic renderers built on core dependencies only:

* :func:`highlight_to_svg` — vector syntax highlighting via ``rich`` (record
  console + ``export_svg``). Ideal for crisp, scalable code panels.
* :func:`highlight_to_text` — the highlighted code flattened to plain text (line
  numbers included), useful for captions, diffs, and snapshot tests.
* :func:`render_code_image` — a Pillow raster code frame on a fixed character
  grid, with line numbers and highlighted-line background bands. The grid is
  computed from a fixed cell size rather than the host font's metrics, so output
  is byte-stable across machines regardless of the available system fonts.

All three are pure functions of their inputs: no I/O, no randomness, no network.
"""

from __future__ import annotations

from rich.console import Console
from rich.syntax import Syntax

from .._logging import get_logger

__all__ = ["highlight_to_svg", "highlight_to_text", "render_code_image"]

logger = get_logger(__name__)

# Fixed character cell for the raster renderer. Chosen so a 1280px-wide frame
# fits ~140 columns — comfortable for code — while staying integer-clean.
_CELL_W = 9
_CELL_H = 20
_MARGIN = 16
_GUTTER_COLS = 5  # line-number gutter width in character cells

# Default raster colors (deterministic; not theme-dependent).
_BG = (30, 30, 30)
_FG = (220, 220, 220)
_GUTTER_FG = (120, 120, 120)
_HIGHLIGHT_BAND = (60, 60, 90)


def _build_console(width_chars: int) -> Console:
    """Return a recording console of a fixed character width.

    Args:
        width_chars: Console width in character cells.

    Returns:
        A non-terminal recording :class:`rich.console.Console`.
    """
    return Console(record=True, width=width_chars, file=None, force_terminal=False)


def highlight_to_svg(
    code: str,
    *,
    language: str = "python",
    theme: str = "monokai",
    line_numbers: bool = True,
) -> str:
    """Render ``code`` to a syntax-highlighted SVG string.

    Args:
        code: The source code to highlight.
        language: Lexer name understood by ``rich``/``pygments`` (e.g. ``python``).
        theme: A ``rich`` syntax theme name (e.g. ``monokai``).
        line_numbers: Whether to render a line-number gutter.

    Returns:
        A standalone SVG document as a string (always contains ``<svg``).
    """
    syntax = Syntax(
        code,
        language,
        theme=theme,
        line_numbers=line_numbers,
        word_wrap=False,
    )
    console = _build_console(width_chars=120)
    console.print(syntax)
    return console.export_svg(title=language)


def highlight_to_text(code: str, *, language: str = "python") -> str:
    """Render ``code`` to plain text via ``rich`` (line numbers included).

    Args:
        code: The source code to render.
        language: Lexer name understood by ``rich``/``pygments``.

    Returns:
        The flattened plain-text rendering of the highlighted code.
    """
    syntax = Syntax(code, language, line_numbers=True, word_wrap=False)
    console = _build_console(width_chars=120)
    console.print(syntax)
    return console.export_text()


def render_code_image(
    code: str,
    *,
    language: str = "python",
    size: tuple[int, int] = (1280, 720),
    highlight_lines: tuple[int, ...] = (),
):
    """Render ``code`` to a Pillow image on a fixed character grid.

    Line numbers are drawn in a left gutter; any line in ``highlight_lines``
    (1-based) gets a full-width background band. Layout uses a fixed cell size so
    the result is deterministic regardless of host fonts.

    Args:
        code: The source code to draw.
        language: Informational only (kept for API symmetry; not used for
            tokenizing the raster output).
        size: ``(width, height)`` of the output image in pixels.
        highlight_lines: 1-based line numbers to emphasize with a band.

    Returns:
        A :class:`PIL.Image.Image` of exactly ``size``.
    """
    from PIL import Image, ImageDraw, ImageFont

    width, height = size
    image = Image.new("RGB", (width, height), _BG)
    draw = ImageDraw.Draw(image)

    try:
        font = ImageFont.load_default(size=16)
    except TypeError:  # pragma: no cover - very old Pillow without size kwarg
        font = ImageFont.load_default()

    highlight_set = set(highlight_lines)
    gutter_px = _MARGIN + _GUTTER_COLS * _CELL_W
    lines = code.splitlines() or [""]

    for index, line in enumerate(lines):
        line_no = index + 1
        y = _MARGIN + index * _CELL_H
        if y + _CELL_H > height:
            break  # clip to frame; deterministic truncation

        if line_no in highlight_set:
            draw.rectangle(
                [(0, y), (width, y + _CELL_H)],
                fill=_HIGHLIGHT_BAND,
            )

        draw.text(
            (_MARGIN, y),
            str(line_no).rjust(_GUTTER_COLS - 1),
            fill=_GUTTER_FG,
            font=font,
        )
        draw.text((gutter_px, y), line, fill=_FG, font=font)

    return image
