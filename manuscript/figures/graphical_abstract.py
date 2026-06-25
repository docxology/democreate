"""Publication-quality COVER graphical abstract for the DemoCreate manuscript.

A deterministic, pure-Pillow generator that composes a single dense-but-clean
cover graphic for DemoCreate v0.6.2 at 2400x1350 (high-res, 16:9). It reads in
one glance: a title band, an INPUTS column (codebase + paper), a horizontal
PIPELINE spine (declarative Demo -> TTS -> sync -> compose/animate -> encode ->
verify), a vertical FILM STRIP of the four real rendered stills, output chips,
and a bottom row of five property badges.

The generator is import-safe and *raises on any failure* (missing stills,
unreadable fonts, wrong output size) so a broken cover can never pass silently.
It uses the package's own font resolution (``democreate.animation.fonts``) so
text is crisp at this resolution, and the dark theme + single accent are taken
straight from ``democreate.config.THEMES["dark"]``.

Run directly::

    .venv/bin/python manuscript/figures/graphical_abstract.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

# --- Make the package importable when run as a standalone script -------------
_THIS = Path(__file__).resolve()
_REPO = _THIS.parents[2]  # .../demo_create
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from democreate.animation.fonts import load_font  # noqa: E402
from democreate.config import THEMES  # noqa: E402

# --------------------------------------------------------------------------- #
# Canvas + palette
# --------------------------------------------------------------------------- #
W, H = 2400, 1350
OUT = _THIS.parent / "graphical_abstract.png"
FRAMES_DIR = _REPO / "docs" / "_videoframes"

_T = THEMES["noir"]  # black / white / slight red
BG = (10, 10, 12)
PANEL = (18, 18, 21)
PANEL_HI = (26, 26, 30)
STROKE = (46, 46, 52)
ACCENT = _T.accent  # red (224, 49, 57)
ACCENT_DIM = (120, 34, 38)
TEXT = (242, 242, 244)
DIM = (150, 150, 156)
FAINT = (102, 102, 108)
GREEN = _T.accent  # monochrome+red: no green chroma in the noir cover

# Two large, legible stills (one per demo kind) read far better on the cover than
# four cramped thumbnails — the "by the numbers" package shot and a real paper
# figure carry the OUTPUTS story.
STILLS = [
    ("showcase_stats.png", "Package demo · by the numbers"),
    ("paper_figure.png", "Research-paper demo · a real figure"),
]


# --------------------------------------------------------------------------- #
# Font helpers
# --------------------------------------------------------------------------- #
def _font(px: int, *, mono: bool = False):
    return load_font(px, mono=mono)


def _measure(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    x0, y0, x1, y1 = draw.textbbox((0, 0), text, font=font)
    return (x1 - x0, y1 - y0)


def _text_center(draw, cx, y, text, font, fill):
    w, _ = _measure(draw, text, font)
    draw.text((cx - w // 2, y), text, font=font, fill=fill)


def _mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


# --------------------------------------------------------------------------- #
# Primitive shapes
# --------------------------------------------------------------------------- #
def _panel(draw, box, *, radius=18, fill=PANEL, outline=STROKE, width=2):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def _arrow_h(draw, x0, x1, y, *, color=ACCENT, width=5, head=16):
    """Horizontal left-to-right arrow."""
    draw.line([(x0, y), (x1 - head, y)], fill=color, width=width)
    draw.polygon(
        [(x1, y), (x1 - head, y - head * 0.62), (x1 - head, y + head * 0.62)],
        fill=color,
    )


def _arrow_into(draw, x0, y0, x1, y1, *, color=ACCENT, width=5, head=16):
    """Arrow from (x0,y0) to (x1,y1) with a head at the end."""
    import math

    draw.line([(x0, y0), (x1, y1)], fill=color, width=width)
    ang = math.atan2(y1 - y0, x1 - x0)
    for da in (2.5, -2.5):
        hx = x1 - head * math.cos(ang + da)
        hy = y1 - head * math.sin(ang + da)
        draw.line([(x1, y1), (hx, hy)], fill=color, width=width)


def _fit_contain(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize preserving aspect so the WHOLE image fits within (max_w, max_h)."""
    iw, ih = img.size
    scale = min(max_w / iw, max_h / ih)
    nw, nh = max(1, int(round(iw * scale))), max(1, int(round(ih * scale)))
    return img.resize((nw, nh), Image.LANCZOS)


# --------------------------------------------------------------------------- #
# Sections
# --------------------------------------------------------------------------- #
def _draw_title_band(img: Image.Image, draw: ImageDraw.ImageDraw) -> int:
    """Top title band. Returns the y where content below should start."""
    band_h = 196
    # subtle gradient strip behind the title
    grad = Image.new("RGB", (W, band_h), BG)
    gd = ImageDraw.Draw(grad)
    for y in range(band_h):
        t = y / band_h
        gd.line([(0, y), (W, y)], fill=_mix((16, 22, 34), BG, t))
    img.paste(grad, (0, 0))

    pad = 70
    title_font = _font(112)
    sub_font = _font(38)
    ver_font = _font(30, mono=True)

    # Accent tab + DemoCreate wordmark
    draw.rounded_rectangle([pad, 58, pad + 14, 150], radius=6, fill=ACCENT)
    tx = pad + 40
    draw.text((tx, 44), "DemoCreate", font=title_font, fill=TEXT)
    tw, _ = _measure(draw, "DemoCreate", title_font)

    # version chip beside the wordmark
    chip_x = tx + tw + 34
    ver = "v0.6.2"
    vw, vh = _measure(draw, ver, ver_font)
    draw.rounded_rectangle(
        [chip_x, 76, chip_x + vw + 36, 76 + vh + 26], radius=14,
        fill=_mix(BG, ACCENT, 0.18), outline=ACCENT, width=2,
    )
    draw.text((chip_x + 18, 76 + 13), ver, font=ver_font, fill=ACCENT)

    # tagline
    draw.text(
        (tx, 158),
        "Declarative, deterministic narrated demos of software & research papers",
        font=sub_font, fill=DIM,
    )

    # right-aligned meta line
    meta = "671 tests · ≥90% cov · 53 modules / 7 subsystems · Python ≥3.10 · MIT"
    mf = _font(27)
    mw, mh = _measure(draw, meta, mf)
    draw.text((W - pad - mw, 92), meta, font=mf, fill=FAINT)

    # band divider
    draw.line([(pad, band_h), (W - pad, band_h)], fill=STROKE, width=2)
    return band_h


def _input_card(draw, box, *, kicker, title, lines, mono_tag):
    x0, y0, x1, y1 = box
    _panel(draw, box, radius=20, fill=PANEL, outline=STROKE, width=2)
    # accent left rail
    draw.rounded_rectangle([x0, y0, x0 + 10, y1], radius=5, fill=ACCENT)
    pad = 26
    kf = _font(24)
    tf = _font(38)
    lf = _font(26)
    mf = _font(22, mono=True)
    cy = y0 + pad
    draw.text((x0 + pad + 6, cy), kicker, font=kf, fill=ACCENT)
    cy += 36
    draw.text((x0 + pad + 6, cy), title, font=tf, fill=TEXT)
    cy += 56
    for ln in lines:
        draw.text((x0 + pad + 6, cy), ln, font=lf, fill=DIM)
        cy += 34
    # mono tag at the bottom
    tw, th = _measure(draw, mono_tag, mf)
    draw.rounded_rectangle(
        [x0 + pad + 4, y1 - 44, x0 + pad + 4 + tw + 24, y1 - 44 + th + 18],
        radius=8, fill=_mix(BG, ACCENT, 0.12), outline=ACCENT_DIM, width=1,
    )
    draw.text((x0 + pad + 16, y1 - 44 + 9), mono_tag, font=mf, fill=_mix(TEXT, ACCENT, 0.4))


def _draw_inputs(draw, region):
    """Two stacked input cards. Returns list of (right_x, mid_y) feed points."""
    x0, y0, x1, y1 = region
    gap = 40
    card_h = (y1 - y0 - gap) // 2
    feeds = []

    top = (x0, y0, x1, y0 + card_h)
    _input_card(
        draw, top,
        kicker="INPUT  ·  SOURCE CODE",
        title="Codebase (AST)",
        lines=["Walk modules & symbols", "via Python AST — no", "runtime, no install."],
        mono_tag="ast.parse()",
    )
    feeds.append((x1, (top[1] + top[3]) // 2))

    bot = (x0, y1 - card_h, x1, y1)
    _input_card(
        draw, bot,
        kicker="INPUT  ·  RESEARCH",
        title="Research paper (PDF)",
        lines=["Real abstract, captions,", "sections via poppler CLI", "— zero pip, skips ToC."],
        mono_tag="pdftotext / pdfinfo",
    )
    feeds.append((x1, (bot[1] + bot[3]) // 2))

    # section label
    lf = _font(26)
    draw.text((x0 + 6, y0 - 40), "INPUTS", font=lf, fill=FAINT)
    return feeds


def _pipe_box(draw, cx, cy, w, h, *, title, sub, mono=False, emphasize=False):
    box = [cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2]
    fill = _mix(PANEL_HI, ACCENT, 0.18) if emphasize else PANEL_HI
    outline = ACCENT if emphasize else _mix(STROKE, ACCENT, 0.4)
    _panel(draw, box, radius=16, fill=fill, outline=outline, width=3 if emphasize else 2)
    tf = _font(30 if not emphasize else 32, mono=mono)
    sf = _font(20)
    tw, th = _measure(draw, title, tf)
    if sub:
        draw.text((cx - tw // 2, cy - th - 4), title, font=tf, fill=TEXT)
        sw, sh = _measure(draw, sub, sf)
        draw.text((cx - sw // 2, cy + 6), sub, font=sf, fill=DIM)
    else:
        draw.text((cx - tw // 2, cy - th // 2), title, font=tf, fill=TEXT)
    return box


def _draw_pipeline(draw, region, feeds):
    """Horizontal pipeline spine. Returns nothing; draws into region."""
    x0, y0, x1, y1 = region
    lf = _font(26)
    draw.text((x0 + 6, y0 - 40), "DECLARATIVE PIPELINE", font=lf, fill=FAINT)

    cy = (y0 + y1) // 2

    # the declarative Demo artifact card (taller, stylized JSON)
    demo_w, demo_h = 270, 270
    demo_cx = x0 + demo_w // 2 + 10
    demo_box = [demo_cx - demo_w // 2, cy - demo_h // 2, demo_cx + demo_w // 2, cy + demo_h // 2]
    _panel(draw, demo_box, radius=16, fill=_mix(PANEL_HI, ACCENT, 0.10), outline=ACCENT, width=3)
    hf = _font(26)
    _text_center(draw, demo_cx, demo_box[1] + 16, "Demo (value)", hf, TEXT)
    draw.line([(demo_box[0] + 18, demo_box[1] + 54), (demo_box[2] - 18, demo_box[1] + 54)],
              fill=STROKE, width=2)
    jf = _font(19, mono=True)
    json_lines = [
        ("{", TEXT),
        ('  "scenes": [', _mix(TEXT, ACCENT, 0.5)),
        ('    "chunks": [', DIM),
        ('      type, text,', GREEN),
        ('      action ]]', GREEN),
        ("}", TEXT),
    ]
    jy = demo_box[1] + 66
    for ln, col in json_lines:
        draw.text((demo_box[0] + 22, jy), ln, font=jf, fill=col)
        jy += 26
    _text_center(draw, demo_cx, demo_box[3] - 30, "scenes › chunks › actions", _font(17), FAINT)

    # feed arrows from inputs into the Demo card (aim at upper / lower thirds)
    targets = [demo_box[1] + demo_h // 3, demo_box[3] - demo_h // 3]
    for (fx, fy), ty in zip(feeds, targets, strict=False):
        _arrow_into(draw, fx + 8, fy, demo_box[0] - 12, ty,
                    color=ACCENT_DIM, width=4, head=15)

    # pipeline stages after the Demo card
    stages = [
        ("TTS", "voice synth"),
        ("Sync", "audio = truth"),
        ("Compose", "+ animate"),
        ("Encode", "H.264 + AAC"),
        ("Verify", "content-checked"),
    ]
    n = len(stages)
    spine_x0 = demo_box[2] + 64
    spine_x1 = x1 - 6
    bw = 190
    bh = 128
    # distribute centers evenly
    span = spine_x1 - spine_x0
    step = span / n
    centers = [spine_x0 + step * (i + 0.5) for i in range(n)]

    # arrow from Demo card to first stage
    _arrow_h(draw, demo_box[2] + 10, centers[0] - bw // 2 - 6, cy, color=ACCENT, width=5, head=18)

    boxes = []
    for i, (title, sub) in enumerate(stages):
        emph = title in ("Sync", "Verify")
        b = _pipe_box(draw, int(centers[i]), cy, bw, bh, title=title, sub=sub, emphasize=emph)
        boxes.append(b)
        if i > 0:
            _arrow_h(draw, boxes[i - 1][2] + 8, b[0] - 6, cy, color=ACCENT, width=5, head=18)

    # small annotations under key stages
    af = _font(19)
    _text_center(draw, int(centers[1]), cy + bh // 2 + 18, "TTS→STT", af, GREEN)
    _text_center(draw, int(centers[2]), cy + bh // 2 + 18, "typing · waveform · no-crop", af, DIM)


def _sprocket(draw, x, y, w):
    """Draw a row of small sprocket holes across width w starting at x,y."""
    hole = 12
    gap = 26
    cx = x
    while cx + hole < x + w:
        draw.rounded_rectangle([cx, y, cx + hole, y + hole], radius=3, fill=(0, 0, 0))
        draw.rounded_rectangle([cx, y, cx + hole, y + hole], radius=3, outline=STROKE, width=1)
        cx += gap


def _draw_filmstrip(img, draw, region):
    """Vertical film strip of the four real stills. Returns nothing."""
    x0, y0, x1, y1 = region
    lf = _font(26)
    draw.text((x0 + 6, y0 - 40), "OUTPUTS", font=lf, fill=FAINT)

    strip_w = x1 - x0
    # film backing
    _panel(draw, [x0, y0, x1, y1], radius=16, fill=(6, 8, 12), outline=STROKE, width=2)

    inner_pad = 22
    sprocket_w = 18
    thumb_x = x0 + inner_pad + sprocket_w
    thumb_w = strip_w - 2 * inner_pad - 2 * sprocket_w

    n = len(STILLS)
    label_h = 30
    cell_gap = 18
    avail_h = (y1 - y0) - 2 * inner_pad - (n - 1) * cell_gap
    cell_h = avail_h // n

    cy = y0 + inner_pad
    lblf = _font(22)
    for fname, label in STILLS:
        fp = FRAMES_DIR / fname
        if not fp.exists():
            raise FileNotFoundError(f"required still missing: {fp}")
        still = Image.open(fp).convert("RGB")
        thumb = _fit_contain(still, thumb_w, cell_h - label_h - 6)
        tw, th = thumb.size
        # frame slot background
        slot = [thumb_x - 6, cy - 4, thumb_x + thumb_w + 6, cy + cell_h - 4]
        draw.rounded_rectangle(slot, radius=8, fill=(2, 3, 5), outline=_mix(STROKE, ACCENT, 0.3), width=1)
        # paste thumbnail centered horizontally at top of cell
        px = thumb_x + (thumb_w - tw) // 2
        py = cy + (cell_h - label_h - th) // 2
        img.paste(thumb, (px, py))
        draw.rectangle([px, py, px + tw - 1, py + th - 1], outline=STROKE, width=1)
        # label beneath
        _text_center(draw, thumb_x + thumb_w // 2, cy + cell_h - label_h + 2, label, lblf, _mix(TEXT, ACCENT, 0.3))
        cy += cell_h + cell_gap

    # sprocket holes down both edges
    # left edge
    hole = 14
    step = 34
    yy = y0 + inner_pad
    lx = x0 + 6
    rx = x1 - 6 - hole
    while yy + hole < y1 - inner_pad:
        for hx in (lx, rx):
            draw.rounded_rectangle([hx, yy, hx + hole, yy + hole], radius=3, fill=(0, 0, 0), outline=STROKE, width=1)
        yy += step


def _draw_output_chips(draw, region):
    """Row of output chips beneath the film strip header / beside outputs."""
    x0, y0, x1, y1 = region
    chips = ["4K video + voiceover", "HTML player", "captions + chapters", "signed provenance"]
    cf = _font(21)
    pad = 16
    gap = 12
    # lay out in a 2x2 grid within region
    cw = (x1 - x0 - gap) // 2
    ch = (y1 - y0 - gap) // 2
    positions = [
        (x0, y0), (x0 + cw + gap, y0),
        (x0, y0 + ch + gap), (x0 + cw + gap, y0 + ch + gap),
    ]
    for (cx, cyy), text in zip(positions, chips, strict=False):
        box = [cx, cyy, cx + cw, cyy + ch]
        draw.rounded_rectangle(box, radius=12, fill=_mix(PANEL, ACCENT, 0.10), outline=ACCENT_DIM, width=2)
        # accent dot
        dot_y = (box[1] + box[3]) // 2
        draw.ellipse([cx + pad, dot_y - 7, cx + pad + 14, dot_y + 7], fill=ACCENT)
        tw, th = _measure(draw, text, cf)
        draw.text((cx + pad + 26, dot_y - th // 2), text, font=cf, fill=TEXT)


def _draw_badges(draw, region):
    """Bottom strip of five property badges."""
    x0, y0, x1, y1 = region
    badges = [
        ("Binary-free", "deterministic default"),
        ("Audio-anchored", "TTS→STT sync"),
        ("No-crop", "autosized · dense"),
        ("Themes · 4K", "crf-18 quality"),
        ("Tamper-evident", "signed provenance"),
    ]
    n = len(badges)
    gap = 22
    bw = (x1 - x0 - gap * (n - 1)) // n
    tf = _font(30)
    sf = _font(22)
    for i, (top, bot) in enumerate(badges):
        bx0 = x0 + i * (bw + gap)
        box = [bx0, y0, bx0 + bw, y1]
        draw.rounded_rectangle(box, radius=16, fill=PANEL_HI, outline=ACCENT, width=2)
        # accent top rule
        draw.rounded_rectangle([bx0 + 16, y0 + 12, bx0 + bw - 16, y0 + 18], radius=3, fill=ACCENT)
        cx = (box[0] + box[2]) // 2
        _text_center(draw, cx, y0 + 34, top, tf, TEXT)
        _text_center(draw, cx, y0 + 74, bot, sf, DIM)


# --------------------------------------------------------------------------- #
# Compose
# --------------------------------------------------------------------------- #
def build() -> Image.Image:
    if not FRAMES_DIR.exists():
        raise FileNotFoundError(f"video frames directory missing: {FRAMES_DIR}")

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    band_bottom = _draw_title_band(img, draw)

    pad = 70
    content_top = band_bottom + 64
    badges_h = 116
    content_bottom = H - pad - badges_h - 40

    # column geometry
    inputs_w = 360
    film_w = 470
    chips_h = 132

    inputs_x0 = pad
    inputs_x1 = inputs_x0 + inputs_w

    film_x1 = W - pad
    film_x0 = film_x1 - film_w

    pipe_x0 = inputs_x1 + 70
    pipe_x1 = film_x0 - 70

    # INPUTS
    feeds = _draw_inputs(draw, (inputs_x0, content_top, inputs_x1, content_bottom))

    # PIPELINE (span the full inputs height so its midline matches the inputs)
    _draw_pipeline(draw, (pipe_x0, content_top, pipe_x1, content_bottom), feeds)

    # OUTPUTS: film strip (upper) + chips (lower)
    film_top = content_top
    film_bot = content_bottom - chips_h - 24
    _draw_filmstrip(img, draw, (film_x0, film_top, film_x1, film_bot))
    _draw_output_chips(draw, (film_x0, film_bot + 24, film_x1, content_bottom))

    # BADGES bottom strip
    _draw_badges(draw, (pad, H - pad - badges_h, W - pad, H - pad))

    return img


def main() -> None:
    img = build()
    if img.size != (W, H):
        raise ValueError(f"unexpected canvas size {img.size}, expected {(W, H)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG")
    # Mirror into output/figures/ so the template render pipeline (which resolves
    # figures/x.png to output/figures/) finds the cover natively.
    mirror = _REPO / "output" / "figures" / OUT.name
    mirror.parent.mkdir(parents=True, exist_ok=True)
    img.save(mirror, "PNG")

    # Verify the output is real and non-blank.
    check = Image.open(OUT).convert("RGB")
    if check.size != (W, H):
        raise ValueError(f"saved size {check.size} != {(W, H)}")
    var = sum(ImageStat.Stat(check).var)
    if var <= 0:
        raise ValueError("graphical abstract is blank (zero variance)")
    print(f"wrote {OUT} ({check.size[0]}x{check.size[1]}), variance={var:.1f}")


if __name__ == "__main__":
    main()
