"""Frame rendering — the synthetic virtual renderer at the heart of capture.

A :class:`FrameSource` turns a :class:`~democreate.media.FrameState` into a
:class:`PIL.Image.Image`. The default :class:`SyntheticRenderer` is a pure-Python
(Pillow-only) "virtual desktop" in the spirit of CodeVideo: instead of capturing
real pixels it *draws* a clean, deterministic representation of the editor,
terminal, browser, or slide implied by the frame state.

Every metric is proportional to the frame height and all text uses real, scalable
TrueType fonts (via :mod:`democreate.animation.fonts`); colors and font scale come
from a :class:`~democreate.config.Theme` so the whole look is configurable. Code is
syntax-highlighted with **pygments** when available (a transitive dependency via
rich), falling back to a small keyword set otherwise. A frame may use a full-frame
``background_image`` (e.g. a real browser screenshot or a generated diagram), and
the renderer reserves a bottom band for the animated speech waveform.

The real :class:`MssScreenCapture` is provided behind the ``capture`` extra; it is
never required.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

from .._logging import get_logger
from ..animation.fonts import load_font, scaled_font
from ..config import Theme
from ..errors import BackendUnavailableError
from ..media import FrameState
from ..schema import Demo, SceneKind

if TYPE_CHECKING:  # pragma: no cover - typing only
    from PIL import Image as _ImageModule

__all__ = [
    "FrameSource",
    "SyntheticRenderer",
    "MssScreenCapture",
    "render_frame",
    "render_demo_thumbnail",
    "waveform_band_box",
    "WAVEFORM_BAND_FRAC",
]

logger = get_logger(__name__)

_FALLBACK_KEYWORDS = frozenset(
    {"def", "class", "return", "import", "from", "if", "else", "for", "while",
     "with", "as", "in", "not", "and", "or", "None", "True", "False", "self",
     "lambda", "yield", "await", "async", "try", "except", "raise"}
)

# Fraction of the frame height reserved at the bottom for the speech waveform.
WAVEFORM_BAND_FRAC = 0.12


def waveform_band_box(width: int, height: int) -> tuple[int, int, int, int]:
    """Return the ``(x0, y0, x1, y1)`` band reserved for the waveform overlay.

    Args:
        width: Frame width in pixels.
        height: Frame height in pixels.

    Returns:
        The band rectangle at the bottom of the frame.
    """
    band_h = max(1, int(round(height * WAVEFORM_BAND_FRAC)))
    return (0, height - band_h, width, height)


def _have(dep: str) -> bool:
    """Return ``True`` if an optional dependency is importable."""
    return importlib.util.find_spec(dep) is not None


class FrameSource:
    """Abstract source of rendered frames.

    A concrete source maps a :class:`~democreate.media.FrameState` to a Pillow
    image of a requested pixel size.
    """

    def render(self, state: FrameState, size: tuple[int, int]) -> _ImageModule.Image:
        """Render ``state`` to an image of ``size`` ``(width, height)``.

        Args:
            state: The virtual-environment snapshot to render.
            size: Output ``(width, height)`` in pixels.

        Returns:
            A :class:`PIL.Image.Image` in ``RGB`` mode.

        Raises:
            NotImplementedError: Always, on the abstract base.
        """
        raise NotImplementedError


class SyntheticRenderer(FrameSource):
    """Deterministic, themeable, resolution-aware pure-Pillow renderer.

    Args:
        theme: Colors and font scale to use; defaults to the built-in dark theme.

    It draws an editor, terminal, browser, or slide depending on
    ``state.scene_kind`` — or a full-frame ``background_image`` when present — with
    large TrueType text, pygments-highlighted code, a top chrome bar carrying the
    section label, a word-wrapped lower-third caption, and a reserved bottom band
    for the waveform. Output is byte-for-byte deterministic for a given state,
    size, and theme.
    """

    def __init__(self, theme: Theme | None = None) -> None:
        self.t = theme or Theme()

    def render(self, state: FrameState, size: tuple[int, int]) -> _ImageModule.Image:
        """Draw ``state`` onto a fresh image of ``size``."""
        from PIL import Image, ImageDraw

        t = self.t
        width, height = self._normalize_size(size)
        kind = state.scene_kind
        bg = {
            SceneKind.CODEBASE: t.bg_editor,
            SceneKind.TERMINAL: t.bg_terminal,
            SceneKind.WEBSITE: t.bg_browser,
            SceneKind.SLIDE: t.bg_slide,
        }.get(kind, t.bg_editor)
        img = Image.new("RGB", (width, height), bg)

        if state.background_image:
            cb = self._content_bottom(width, height, bool(state.caption))
            self._draw_background(img, state.background_image, content_bottom=cb)
            draw = ImageDraw.Draw(img)
        else:
            draw = ImageDraw.Draw(img)
            if kind == SceneKind.TERMINAL:
                self._draw_terminal(draw, state, width, height)
            elif kind == SceneKind.WEBSITE:
                self._draw_browser(draw, state, width, height)
            elif kind == SceneKind.SLIDE:
                self._draw_slide(draw, state, width, height)
            else:
                self._draw_editor(draw, state, width, height)

        bx0, by0, bx1, by1 = waveform_band_box(width, height)
        draw.rectangle([bx0, by0, bx1, by1], fill=t.band_bg)

        if state.section:
            self._draw_section(draw, state.section, width, height)
        if state.caption:
            self._draw_caption(draw, state.caption, width, height)
        return img

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _normalize_size(size: tuple[int, int]) -> tuple[int, int]:
        """Clamp a requested size to at least 1x1 integer pixels."""
        return max(1, int(size[0])), max(1, int(size[1]))

    @staticmethod
    def _text_w(draw, text: str, font) -> float:
        """Measured pixel width of ``text`` in ``font``."""
        return draw.textlength(text, font=font)

    def _content_bottom(self, width: int, height: int, has_caption: bool) -> int:
        """Return the y below which the caption + waveform bands live.

        Primary content (images, code) must stay above this line so the caption
        and waveform never overlap or crop it.
        """
        wf_top = waveform_band_box(width, height)[1]
        if has_caption:
            cap = scaled_font(height, self.t.caption_ratio)
            return int(wf_top - cap.size * 1.3 * 3 - height * 0.055)
        return int(wf_top - height * 0.02)

    def _draw_background(self, img, path: str, *, content_bottom: int) -> None:
        """Fit a background image *whole* (contain) into the content area.

        Unlike a cover-crop, this loses no part of the image: it scales by the
        smaller ratio so the entire figure/diagram/screenshot is visible, centers
        it on the theme background (a matte), and frames it with a thin border.
        The caption sits below it (never over it).
        """
        from PIL import Image, ImageDraw, UnidentifiedImageError

        try:
            src = Image.open(path).convert("RGB")
        except (FileNotFoundError, UnidentifiedImageError, OSError):  # pragma: no cover
            logger.warning("background image unavailable: %s", path)
            return
        tw, th = img.size
        bx0, by0 = int(tw * 0.025), int(th * 0.022)
        bx1, by1 = int(tw * 0.975), int(content_bottom - th * 0.01)
        bw, bh = max(1, bx1 - bx0), max(1, by1 - by0)
        sw, sh = src.size
        scale = min(bw / sw, bh / sh)  # CONTAIN — never crop
        nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
        resized = src.resize((nw, nh))
        px = bx0 + (bw - nw) // 2
        py = by0 + (bh - nh) // 2
        draw = ImageDraw.Draw(img)
        # subtle matte frame around the contained image
        draw.rectangle([px - 3, py - 3, px + nw + 2, py + nh + 2],
                       outline=tuple(min(255, c + 30) for c in self.t.band_bg), width=2)
        img.paste(resized, (px, py))

    def _draw_chrome(self, draw, label: str, width: int, height: int, *, fg=None) -> int:
        """Draw the top window-chrome bar and return its bottom y coordinate."""
        t = self.t
        bar_h = max(24, int(height * 0.052))
        draw.rectangle([0, 0, width, bar_h], fill=t.title_bar)
        r = max(5, int(bar_h * 0.18))
        cy = bar_h // 2
        # Theme-driven window dots: one accent + two dimmed — keeps a strict
        # palette (e.g. noir's black/white/red) instead of fixed red/amber/green.
        dim2 = tuple((a + b) // 2 for a, b in zip(t.dim, t.title_bar, strict=False))
        for i, color in enumerate((t.accent, t.dim, dim2)):
            cx = int(bar_h * 0.55) + i * int(r * 3.1)
            draw.ellipse([cx, cy - r, cx + 2 * r, cy + r], fill=color)
        if label:
            font = scaled_font(height, t.section_ratio)
            draw.text((int(bar_h * 2.4), cy - font.size // 2), label,
                      fill=fg or t.text, font=font)
        return bar_h

    def _draw_section(self, draw, section: str, width: int, height: int) -> None:
        """Draw a section/chapter label as a pill in the top-right of the chrome."""
        t = self.t
        font = scaled_font(height, t.section_ratio)
        text = section.upper()
        tw = self._text_w(draw, text, font)
        pad = int(height * 0.012)
        bar_h = max(24, int(height * 0.052))
        x1 = width - pad
        x0 = int(x1 - tw - 2 * pad)
        y0 = (bar_h - font.size) // 2 - pad // 2
        y1 = y0 + font.size + pad
        pill = tuple(min(255, c + 14) for c in t.title_bar)
        draw.rounded_rectangle([x0, y0, x1, y1], radius=pad, fill=pill)
        draw.text((x0 + pad, y0 + pad // 2), text, fill=t.section_fg, font=font)

    def _autosize_code(self, draw, code_lines, width, height, content_top, content_bottom):
        """Pick the largest legible mono font that fits the whole code, no crop.

        Returns ``(font, num_font, char_w, gutter_w, max_chars, line_h)``. Sizing
        is driven by both the longest line (so it fits the width without clipping)
        and the line count (so all lines fit the height); a hard legibility floor
        stops it shrinking below ~18px at 1080p (wrapping handles the rest).
        """
        n = max(1, len(code_lines))
        longest = max((len(line) for line in code_lines), default=1)
        num_chars = max(2, len(str(n)))
        # measure the mono character-width ratio once (constant for a mono face)
        ref = load_font(100, mono=True)
        cr = self._text_w(draw, "M", ref) / 100.0 or 0.6
        content_h = max(1, content_bottom - content_top)
        margins = width * 0.07  # gutter pad + left pad + right margin
        denom = cr * (longest + 0.9 * (num_chars + 1)) or 1.0
        size_w = (width - margins) / denom
        size_h = content_h / (n * 1.55)
        max_px = max(16, int(height * 0.034))
        min_px = max(14, int(height * 0.019))
        size = int(max(min_px, min(size_w, size_h, max_px)))
        font = load_font(size, mono=True)
        num_font = load_font(max(11, int(size * 0.8)), mono=True)
        char_w = self._text_w(draw, "M", font) or (cr * size)
        gutter_w = int((num_chars + 1) * self._text_w(draw, "M", num_font) + width * 0.012)
        content_w = width - gutter_w - int(width * 0.028)
        max_chars = max(8, int(content_w / max(1.0, char_w)))
        return font, num_font, char_w, gutter_w, max_chars, int(size * 1.55)

    def _wrap_code_rows(self, code_lines, max_chars):
        """Flatten code into visual rows, wrapping long lines with a hanging indent.

        Each row is ``(orig_index, text, char_offset, is_continuation)`` so typing
        and highlighting can be tracked against the original line.
        """
        rows: list[tuple[int, str, int, bool]] = []
        for i, line in enumerate(code_lines):
            if len(line) <= max_chars:
                rows.append((i, line, 0, False))
                continue
            indent = "  "
            off = 0
            first = True
            while off < len(line) or first:
                width_budget = max_chars if first else max_chars - len(indent)
                chunk = line[off:off + max(1, width_budget)]
                prefix = "" if first else indent
                rows.append((i, prefix + chunk, off, not first))
                off += len(chunk)
                first = False
                if off >= len(line):
                    break
        return rows

    def _draw_editor(self, draw, state: FrameState, width, height) -> None:
        """Draw an autosized, no-crop, line-numbered code editor with pygments."""
        t = self.t
        top = self._draw_chrome(draw, state.file_path or state.title, width, height)
        content_top = top + int(height * 0.022)
        content_bottom = self._content_bottom(width, height, bool(state.caption))
        code = state.code_lines or [""]
        font, num_font, char_w, gutter_w, max_chars, line_h = self._autosize_code(
            draw, code, width, height, content_top, content_bottom)
        draw.rectangle([0, top, gutter_w, height], fill=t.gutter)
        pad_x = gutter_w + int(width * 0.009)
        spans = self._highlight(code, state.file_path)
        rows = self._wrap_code_rows(code, max_chars)

        # how many characters of the whole block are revealed (typing animation)
        typed = state.cursor_typed
        revealed = [len(line) for line in code]
        if typed is not None:
            remaining = max(0, typed)
            for i, line in enumerate(code):
                revealed[i] = max(0, min(len(line), remaining))
                remaining -= len(line)

        y = content_top
        last_orig = -1
        for orig, text, offset, cont in rows:
            if y > content_bottom - line_h + 2:
                break
            # highlight band spans every visual row of a highlighted source line —
            # but only once the line has begun typing, so we never paint a green
            # band over a still-blank line during the type-in animation.
            line_reached = typed is None or revealed[orig] > 0
            if (orig + 1) in state.highlight_lines and line_reached:
                draw.rectangle([gutter_w, y - 2, width, y + line_h - 4], fill=t.highlight)
                draw.rectangle([0, y - 2, max(3, int(width * 0.004)), y + line_h - 4],
                               fill=t.highlight_bar)
            if not cont and orig != last_orig:
                draw.text((int(width * 0.006), y), f"{orig + 1:>3}", fill=t.dim,
                          font=num_font)
                last_orig = orig
            # reveal only the typed portion of this row's source characters
            row_src_len = len(text) - (2 if cont else 0)
            shown_src = max(0, min(row_src_len, revealed[orig] - offset))
            prefix = text[:len(text) - row_src_len]  # the hanging indent, if any
            visible = prefix + text[len(prefix):len(prefix) + shown_src]
            if cont or (orig + 1) not in range(len(spans) + 1) or len(code[orig]) > max_chars:
                # wrapped/continuation rows draw plain (token spans are per source line)
                draw.text((pad_x, y), visible, fill=t.text, font=font)
            else:
                self._draw_spans(draw, spans[orig], visible, pad_x, y, font, char_w)
            # typing caret at the end of the revealed text on the active row
            if typed is not None and offset <= revealed[orig] < offset + row_src_len + 1 \
                    and revealed[orig] < len(code[orig]) + 1:
                cx = int(pad_x + self._text_w(draw, visible, font))
                draw.rectangle([cx, y, cx + max(2, int(char_w * 0.12)), y + line_h - 4],
                               fill=t.cursor)
            y += line_h

    def _highlight(self, code_lines: list[str], path: str) -> list[list[tuple[str, tuple]]]:
        """Return per-line ``[(text, color), ...]`` spans via pygments (or fallback)."""
        t = self.t
        try:
            from pygments import lex
            from pygments.lexers import get_lexer_by_name, guess_lexer_for_filename
            from pygments.token import Token
            from pygments.util import ClassNotFound

            source = "\n".join(code_lines)
            try:
                lexer = guess_lexer_for_filename(path or "code.py", source)
            except ClassNotFound:  # pragma: no cover - rare
                lexer = get_lexer_by_name("python")

            def color_for(tok) -> tuple:
                if tok in Token.Keyword or tok in Token.Name.Builtin.Pseudo:
                    return t.syn_keyword
                if tok in Token.Name.Function or tok in Token.Name.Class:
                    return t.syn_name
                if tok in Token.Name.Builtin or tok in Token.Name.Decorator:
                    return t.syn_name
                if tok in Token.Literal.String:
                    return t.syn_string
                if tok in Token.Literal.Number:
                    return t.syn_number
                if tok in Token.Comment:
                    return t.syn_comment
                return t.text

            lines: list[list[tuple[str, tuple]]] = [[]]
            for tok, value in lex(source, lexer):
                color = color_for(tok)
                parts = value.split("\n")
                for i, part in enumerate(parts):
                    if i > 0:
                        lines.append([])
                    if part:
                        lines[-1].append((part, color))
            # Pad or trim to exactly one span-list per source line — keeping the
            # colors we DID get rather than discarding all highlighting when
            # pygments emits fewer lines (e.g. collapsed trailing blanks).
            if len(lines) < len(code_lines):
                lines += [[] for _ in range(len(code_lines) - len(lines))]
            return lines[: len(code_lines)]
        except Exception:  # pragma: no cover - any pygments hiccup → fallback
            pass
        # fallback: whole line in default text color
        return [[(line, t.text)] for line in code_lines]

    def _draw_spans(self, draw, spans, visible: str, x: int, y: int, font, char_w) -> None:
        """Draw colored spans for a line, clipped to ``visible`` characters."""
        t = self.t
        if not spans:
            if visible:
                draw.text((x, y), visible, fill=t.text, font=font)
            return
        shown = 0
        col = x
        budget = len(visible)
        for text, color in spans:
            if shown >= budget:
                break
            seg = text[: budget - shown]
            draw.text((col, y), seg, fill=color, font=font)
            col += int(self._text_w(draw, seg, font))
            shown += len(seg)

    def _draw_terminal(self, draw, state: FrameState, width, height) -> None:
        """Draw a dark terminal with output lines and a trailing prompt."""
        t = self.t
        top = self._draw_chrome(draw, state.title or "terminal", width, height)
        font = scaled_font(height, t.terminal_ratio, mono=True)
        line_h = int(font.size * 1.55)
        char_w = self._text_w(draw, "M", font)
        x = int(height * 0.022)
        y = top + int(height * 0.03)
        limit = waveform_band_box(width, height)[1] - line_h
        for line in state.terminal_lines:
            if y > limit:
                break
            color = t.prompt if line.startswith("$") else t.text
            draw.text((x, y), line, fill=color, font=font)
            y += line_h
        if y <= limit:
            draw.text((x, y), "$ ", fill=t.prompt, font=font)
            cx = int(x + 2 * char_w)
            draw.rectangle([cx, y, cx + max(2, int(char_w * 0.5)), y + font.size],
                           fill=t.cursor)

    def _draw_browser(self, draw, state: FrameState, width, height) -> None:
        """Draw browser chrome with an address bar and a light placeholder body."""
        t = self.t
        top = self._draw_chrome(draw, state.title, width, height)
        font = scaled_font(height, t.section_ratio)
        bar_h = int(height * 0.06)
        draw.rectangle([0, top, width, top + bar_h], fill=(228, 231, 236))
        pad = int(height * 0.014)
        box = [int(width * 0.06), top + pad, width - pad, top + bar_h - pad]
        draw.rounded_rectangle(box, radius=pad, fill=(255, 255, 255), outline=(203, 208, 214))
        draw.text((int(width * 0.07), top + pad + pad // 2), state.url or "about:blank",
                  fill=t.text_dark, font=font)
        body_top = top + bar_h
        draw.rectangle([0, body_top, width, height], fill=t.bg_browser)
        if state.title:
            htitle = scaled_font(height, 0.05)
            draw.text((int(width * 0.04), body_top + int(height * 0.04)), state.title,
                      fill=t.text_dark, font=htitle)
        for i in range(4):
            ly = body_top + int(height * 0.16) + i * int(height * 0.06)
            if ly < waveform_band_box(width, height)[1] - 20:
                draw.rounded_rectangle([int(width * 0.04), ly, width - int(width * 0.06),
                                        ly + int(height * 0.03)], radius=6, fill=(220, 224, 230))

    def _draw_slide(self, draw, state: FrameState, width, height) -> None:
        """Draw a slide: a stat row, a bullet list, or a centered title card."""
        if state.stats:
            self._draw_stats(draw, state, width, height)
        elif state.bullets:
            self._draw_bullets(draw, state, width, height)
        else:
            self._draw_title_card(draw, state, width, height)

    def _draw_title_card(self, draw, state: FrameState, width, height) -> None:
        """Draw a large centered title card with optional subtitle."""
        t = self.t
        title = state.title or state.caption or ""
        subtitle = state.subtitle
        title_font = scaled_font(height, t.title_ratio)
        cy = int(height * 0.42)
        if title:
            tw = self._text_w(draw, title, title_font)
            draw.text(((width - tw) / 2, cy - title_font.size), title, fill=t.text,
                      font=title_font)
        uw = int(width * 0.16)
        draw.rectangle([(width - uw) // 2, cy + int(height * 0.02),
                        (width + uw) // 2, cy + int(height * 0.02) + max(3, int(height * 0.006))],
                       fill=t.accent)
        if subtitle:
            sub_font = scaled_font(height, t.subtitle_ratio)
            sw = self._text_w(draw, subtitle, sub_font)
            draw.text(((width - sw) / 2, cy + int(height * 0.05)), subtitle,
                      fill=t.dim, font=sub_font)

    def _draw_slide_heading(self, draw, state, width, height) -> int:
        """Draw a slide title (top-anchored) + accent rule; return content top y."""
        t = self.t
        x = int(width * 0.07)
        y = int(height * 0.10)
        if state.title:
            hf = scaled_font(height, 0.058)
            draw.text((x, y), state.title, fill=t.text, font=hf)
            y += int(hf.size * 1.15)
            draw.rectangle([x, y, x + int(width * 0.10), y + max(3, int(height * 0.006))],
                           fill=t.accent)
            y += int(height * 0.03)
        if state.subtitle:
            sf = scaled_font(height, t.subtitle_ratio * 0.85)
            draw.text((x, y), state.subtitle, fill=t.dim, font=sf)
            y += int(sf.size * 1.6)
        return y

    def _draw_bullets(self, draw, state: FrameState, width, height) -> None:
        """Draw a title + a clean bulleted list, distributed to fill the slide."""
        t = self.t
        top = self._draw_slide_heading(draw, state, width, height)
        bottom = self._content_bottom(width, height, bool(state.caption))
        bullets = [b for b in state.bullets if b][:6]
        if not bullets:
            return
        x = int(width * 0.085)
        max_w = width - x - int(width * 0.07)
        avail = bottom - top
        # Autosize: shrink the bullet font (down to a legible floor) until the
        # wrapped block fits the available height — so many long bullets never
        # overflow into the caption/waveform band (no-crop rule).
        ratio = 0.040
        while True:
            font = scaled_font(height, ratio)
            wrapped = [self._wrap(draw, b, font, max_w) for b in bullets]
            total_rows = sum(len(w) for w in wrapped)
            line_h = int(font.size * 1.35)
            gap = int(font.size * 0.7)
            block_h = total_rows * line_h + (len(bullets) - 1) * gap
            if block_h <= avail or ratio <= 0.024:
                break
            ratio -= 0.003
        y = top + max(0, (avail - block_h) // 2)
        r = max(5, int(font.size * 0.18))
        for rows in wrapped:
            by = y + (line_h - font.size) // 2 + int(font.size * 0.35)
            draw.ellipse([x, by, x + 2 * r, by + 2 * r], fill=t.accent)
            for row in rows:
                draw.text((x + 3 * r + int(width * 0.012), y), row, fill=t.text, font=font)
                y += line_h
            y += gap

    def _draw_stats(self, draw, state: FrameState, width, height) -> None:
        """Draw a title + a row of big-number stat cards (packed, not floating)."""
        t = self.t
        top = self._draw_slide_heading(draw, state, width, height)
        bottom = self._content_bottom(width, height, bool(state.caption))
        stats = list(state.stats)[:5]
        if not stats:
            return
        n = len(stats)
        margin = int(width * 0.06)
        gap = int(width * 0.02)
        card_w = (width - 2 * margin - (n - 1) * gap) // n
        card_h = min(int(height * 0.34), bottom - top - int(height * 0.02))
        cy = top + max(0, (bottom - top - card_h) // 2)
        val_font = scaled_font(height, 0.085)
        lab_font = scaled_font(height, 0.026)
        for i, (value, label) in enumerate(stats):
            cx = margin + i * (card_w + gap)
            panel = tuple(min(255, c + 12) for c in t.bg_slide)
            draw.rounded_rectangle([cx, cy, cx + card_w, cy + card_h], radius=int(height * 0.02),
                                   fill=panel, outline=tuple(min(255, c + 30) for c in panel),
                                   width=2)
            draw.rectangle([cx, cy, cx + card_w, cy + max(4, int(height * 0.006))], fill=t.accent)
            vw = self._text_w(draw, str(value), val_font)
            draw.text((cx + (card_w - vw) / 2, cy + card_h * 0.22), str(value),
                      fill=t.accent, font=val_font)
            for k, lab in enumerate(self._wrap(draw, str(label), lab_font, card_w * 0.9)[:2]):
                lw = self._text_w(draw, lab, lab_font)
                draw.text((cx + (card_w - lw) / 2,
                           cy + card_h * 0.62 + k * lab_font.size * 1.25),
                          lab, fill=t.dim, font=lab_font)

    def _wrap(self, draw, text: str, font, max_w: float) -> list[str]:
        """Greedy word-wrap ``text`` to lines no wider than ``max_w`` pixels."""
        words = text.split()
        lines: list[str] = []
        cur = ""
        for w in words:
            trial = f"{cur} {w}".strip()
            if self._text_w(draw, trial, font) <= max_w or not cur:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def _draw_caption(self, draw, caption: str, width, height) -> None:
        """Overlay ``caption`` as a word-wrapped lower-third subtitle band."""
        t = self.t
        font = scaled_font(height, t.caption_ratio)
        max_w = width * 0.86
        lines = self._wrap(draw, caption, font, max_w)[:3]
        line_h = int(font.size * 1.3)
        block_h = line_h * len(lines)
        band_top = waveform_band_box(width, height)[1] - block_h - int(height * 0.05)
        pad = int(height * 0.018)
        text_w = max((self._text_w(draw, ln, font) for ln in lines), default=0)
        x0 = int((width - text_w) / 2 - pad)
        x1 = int((width + text_w) / 2 + pad)
        draw.rounded_rectangle([x0, band_top - pad, x1, band_top + block_h + pad // 2],
                               radius=pad, fill=t.caption_bg)
        y = band_top
        for ln in lines:
            lw = self._text_w(draw, ln, font)
            draw.text(((width - lw) / 2, y), ln, fill=t.caption_fg, font=font)
            y += line_h


class MssScreenCapture(FrameSource):
    """Real screen-pixel capture via the ``mss`` library (extra: ``capture``)."""

    def __init__(self, monitor: int = 1) -> None:
        """Store the monitor index and verify the backend is installed.

        Args:
            monitor: 1-based monitor index understood by ``mss``.

        Raises:
            BackendUnavailableError: If ``mss`` is not installed.
        """
        if not _have("mss"):
            raise BackendUnavailableError("mss", extra="capture")
        self.monitor = monitor

    def render(self, state: FrameState, size: tuple[int, int]) -> _ImageModule.Image:  # pragma: no cover - requires real display
        """Capture the current screen and resize it to ``size``."""
        import mss
        from PIL import Image

        with mss.mss() as sct:
            grab = sct.grab(sct.monitors[self.monitor])
            img = Image.frombytes("RGB", grab.size, grab.bgra, "raw", "BGRX")
        return img.resize(size)


def render_frame(
    state: FrameState,
    size: tuple[int, int] = (1920, 1080),
    *,
    theme: Theme | None = None,
) -> _ImageModule.Image:
    """Render a single frame with the default synthetic renderer.

    Args:
        state: The frame state to render.
        size: Output ``(width, height)`` in pixels.
        theme: Optional theme; defaults to the built-in dark theme.

    Returns:
        A rendered :class:`PIL.Image.Image`.
    """
    return SyntheticRenderer(theme).render(state, size)


def render_demo_thumbnail(
    demo: Demo, size: tuple[int, int] = (1280, 720), *, theme: Theme | None = None
) -> _ImageModule.Image:
    """Render a thumbnail from the opening frame of a demo's first scene.

    Args:
        demo: The demo to summarize visually.
        size: Output ``(width, height)`` in pixels.
        theme: Optional theme.

    Returns:
        A rendered :class:`PIL.Image.Image`.
    """
    if not demo.scenes:
        state = FrameState(scene_kind=SceneKind.SLIDE, title=demo.title)
        return render_frame(state, size, theme=theme)
    scene = demo.scenes[0]
    caption = scene.chunks[0].text if scene.chunks else ""
    state = FrameState(
        scene_kind=scene.kind,
        title=scene.title,
        caption=caption,
        file_path=str(scene.context.get("repo", "")),
        terminal_lines=[scene.title] if scene.kind == SceneKind.TERMINAL else [],
        url=str(scene.context.get("url", "")),
    )
    return render_frame(state, size, theme=theme)
