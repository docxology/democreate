#!/usr/bin/env python3
"""Generate the manuscript figures for the DemoCreate v0.6.2 write-up.

Every figure is produced by calling the *real* ``democreate`` public APIs — the
same renderers, themes, fonts, waveform, and diagram code the package ships — so
the figures are faithful, deterministic depictions of what the tool actually
draws. The one data-driven figure (``latency.png``) reads its numbers from the
real measured benchmarks file, never from invented constants.

All eleven figures share one visual language: the **noir** near-black background,
white text, and the single refined red accent — matching the v0.6.2 noir videos —
with a consistent title + accent rule, generous margins, and — critically —
nothing clipped. Any pasted bitmap (paper figure, video still, sub-frame) is
fit-CONTAINed (the whole image is always visible, never cropped or stretched).

Run from the project root with the project venv::

    cd /Users/4d/Documents/GitHub/projects/working/demo_create
    .venv/bin/python manuscript/figures/make_figures.py

Outputs (into this directory). Every figure is 1600x900 except the waveform
strip, which is 1600x300:

* ``architecture.png``      (1600x900) — the canonical pipeline diagram.
* ``frame_code.png``        (1600x900) — a CODEBASE editor frame (pygments + fonts).
* ``frame_title.png``       (1600x900) — a SLIDE title card.
* ``frame_paper.png``       (1600x900) — a SLIDE with a real paper figure background.
* ``waveform.png``          (1600x300) — a speech-waveform scrubber strip.
* ``themes.png``            (1600x900) — the same code frame under five themes.
* ``paper_fig.png``         (copied)   — a real paper figure copied in for the background.
* ``typing_filmstrip.png``  (1600x900) — one editor frame at 25/55/100% typed.
* ``latency.png``           (1600x900) — measured latency bars from benchmarks.json.
* ``paper_flow.png``        (1600x900) — the paper-pipeline flow diagram.
* ``provenance.png``        (1600x900) — the three provenance carriers from one
  ``MetadataConfig``: on-screen overlay bars, MP4 container tags, signed PNG poster.
* ``video_stills.png``      (1600x900) — a 2x2 montage of FOUR real stills
  extracted from the two produced demo videos (the package *showcase* +
  research-paper demo), proving the renders are real, content-verified
  deliverables. The package row prefers the v0.6.1 showcase stills (the bullet
  slide, the stat-card slide) when present in ``docs/_videoframes/``, falling back
  to the older intro stills otherwise.

The script is import-safe and deterministic. If any step cannot complete it
raises rather than silently producing a degraded figure.
"""

from __future__ import annotations

import json
import shutil
import wave
from pathlib import Path

from PIL import Image, ImageDraw

from democreate.animation.diagram import (
    DiagramNode,
    democreate_architecture_image,
    render_architecture_diagram,
)
from democreate.animation.fonts import scaled_font
from democreate.animation.waveform import compute_envelope, draw_waveform
from democreate.capture.screen import render_frame
from democreate.config import THEMES, MetadataConfig
from democreate.media import FrameState
from democreate.schema import SceneKind

HERE = Path(__file__).resolve().parent

# --- shared visual language ------------------------------------------------
# Every figure shares this canvas size, NOIR palette, and the single red accent so
# the eleven figures read as one consistent set — matching the noir videos. Black
# and white carry the design; the red is the only chroma, used sparingly (title
# rule, panel outlines, labels).
CANVAS: tuple[int, int] = (1600, 900)
WAVE_CANVAS: tuple[int, int] = (1600, 300)

BG: tuple[int, int, int] = (12, 12, 14)        # noir near-black page background
PANEL: tuple[int, int, int] = (22, 22, 26)     # raised panel surface
FG: tuple[int, int, int] = (242, 242, 244)     # primary text (near-white)
DIM: tuple[int, int, int] = (146, 146, 152)    # secondary text
ACCENT: tuple[int, int, int] = (224, 49, 57)   # noir accent (THEMES["noir"].accent)

# A real, published research-paper figure used to show the paper-as-background
# composition. Copied into the manuscript figures dir so the manuscript is
# self-contained.
PAPER_FIG_SOURCE = Path(
    "/Users/4d/Documents/GitHub/projects/published/"
    "actinf_policy_entanglement_lean/output/figures/coupling_graph.png"
)

# The real, measured benchmark numbers that drive the latency figure. These are
# read at render time so the figure can never drift from the recorded data.
BENCHMARKS = Path(
    "/Users/4d/Documents/GitHub/projects/working/demo_create/data/benchmarks.json"
)

# Real stills extracted from the two *produced* demo videos. These are genuine
# frames lifted out of the encoded MP4s (not re-rendered), so the montage is
# evidence the videos were actually produced and play, not file-existence stubs.
VIDEOFRAMES = Path(
    "/Users/4d/Documents/GitHub/projects/working/demo_create/docs/_videoframes"
)

# A longer snippet of real democreate source — the typing-reveal driver from
# assembly/animator.py — shown being typed in character-by-character so the
# filmstrip's three columns differ visibly.
TYPING_CODE_LINES = [
    "def typed_base(idx: int, t_ms: int):",
    '    """Re-render chunk ``idx`` with code typed to current progress."""',
    "    start, end = windows[idx]",
    "    total = total_chars(idx)",
    "    if total == 0:",
    "        return bases[idx]",
    "    win = max(1, end - start)",
    "    frac = (t_ms - start) / win / cfg.typing_fraction",
    "    typed = int(total * min(1.0, frac))",
    "    state = copy.copy(frame_states[idx])",
    "    state.cursor_typed = typed",
    "    return renderer.render(state, size)",
]

# A short, real snippet of democreate source — the heart of the declarative
# spine (schema.py) — shown verbatim in the editor frame.
CODE_LINES = [
    "@dataclass",
    "class Action:",
    '    """One typed event mutating the virtual environment."""',
    "    type: ActionType",
    "    params: dict[str, Any] = field(default_factory=dict)",
    "    trigger_word: str | None = None",
    "    timestamp_ms: int | None = None",
    "    duration_ms: int | None = None",
]

# A compact snippet for the small theme-grid cells so code never clips the cell
# edge (the full CODE_LINES is too wide for a ~470px tile).
THEME_CODE = [
    "@dataclass",
    "class Action:",
    "    type: ActionType",
    "    params: dict",
    "    trigger_word: str | None",
]


# --- shared helpers --------------------------------------------------------

def _save(img: Image.Image, name: str) -> Path:
    """Save ``img`` as ``name`` in the figures directory and return its path."""
    out = HERE / name
    img.save(out, format="PNG")
    if not out.is_file() or out.stat().st_size == 0:
        raise RuntimeError(f"figure {name} was not written")
    return out


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    """Greedy word-wrap ``text`` to ``max_w`` pixels with ``font``."""
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    cur = words[0]
    for w in words[1:]:
        trial = f"{cur} {w}"
        if draw.textlength(trial, font=font) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    """Linear blend of two RGB colors."""
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))  # type: ignore[return-value]


def _canvas(
    title: str,
    subtitle: str | None = None,
    size: tuple[int, int] = CANVAS,
) -> tuple[Image.Image, ImageDraw.ImageDraw, int]:
    """Build a standard figure canvas: dark bg, title, accent rule.

    Returns ``(img, draw, content_top)`` where ``content_top`` is the first y
    below the title block where figure-specific content may be drawn. Margins are
    generous and proportional so every figure frames its content identically.
    """
    width, height = size
    img = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(img)

    margin = int(width * 0.04)
    title_font = scaled_font(height, 0.052)
    draw.text((margin, int(height * 0.045)), title, fill=FG, font=title_font)

    y = int(height * 0.045) + int(title_font.size * 1.15)
    if subtitle:
        sub_font = scaled_font(height, 0.026)
        for line in _wrap(draw, subtitle, sub_font, width - 2 * margin):
            draw.text((margin, y), line, fill=DIM, font=sub_font)
            y += int(sub_font.size * 1.25)
        y += int(height * 0.006)

    rule_y = y + int(height * 0.01)
    draw.line([(margin, rule_y), (width - margin, rule_y)], fill=ACCENT, width=3)
    content_top = rule_y + int(height * 0.03)
    return img, draw, content_top


def _fit_contain(
    img: Image.Image,
    src: Image.Image,
    box: tuple[int, int, int, int],
    *,
    border: bool = True,
) -> tuple[int, int, int, int]:
    """Paste ``src`` into ``box`` fit-CONTAIN (whole image visible, never cropped).

    Scales ``src`` by the smaller ratio so the entire image fits inside ``box``,
    centers it, optionally frames it with a thin accent-tinted border, and returns
    the actual ``(x0, y0, x1, y1)`` rectangle the image occupies.
    """
    x0, y0, x1, y1 = box
    bw, bh = max(1, x1 - x0), max(1, y1 - y0)
    sw, sh = src.size
    scale = min(bw / sw, bh / sh)  # CONTAIN — never crop, never stretch
    nw, nh = max(1, int(sw * scale)), max(1, int(sh * scale))
    resized = src.resize((nw, nh), Image.LANCZOS)
    px = x0 + (bw - nw) // 2
    py = y0 + (bh - nh) // 2
    img.paste(resized, (px, py))
    if border:
        draw = ImageDraw.Draw(img)
        draw.rectangle([px - 2, py - 2, px + nw + 1, py + nh + 1],
                       outline=_mix(BG, ACCENT, 0.45), width=2)
    return (px, py, px + nw, py + nh)


# --- builders --------------------------------------------------------------

def make_architecture() -> Path:
    """The canonical four-stage architecture diagram (real diagram renderer)."""
    img = democreate_architecture_image(CANVAS, accent=ACCENT, bg=BG, fg=FG)
    return _save(img, "architecture.png")


def make_frame_code() -> Path:
    """A CODEBASE editor frame: big pygments-highlighted code, gutter, caption."""
    state = FrameState(
        scene_kind=SceneKind.CODEBASE,
        file_path="src/democreate/schema.py",
        code_lines=CODE_LINES,
        highlight_lines=[4],
        section="The Spine",
        caption="Each Action carries a trigger_word anchoring it to a spoken word.",
    )
    img = render_frame(state, CANVAS, theme=THEMES["noir"])
    return _save(img, "frame_code.png")


def make_frame_title() -> Path:
    """A SLIDE title card with subtitle and section pill."""
    state = FrameState(
        scene_kind=SceneKind.SLIDE,
        title="DemoCreate",
        subtitle="Declarative, deterministic narrated demos of code and papers",
        section="Intro",
    )
    img = render_frame(state, CANVAS, theme=THEMES["noir"])
    return _save(img, "frame_title.png")


def make_frame_paper() -> Path:
    """A SLIDE composed over a real research-paper figure, in the paper theme."""
    if not PAPER_FIG_SOURCE.is_file():
        raise FileNotFoundError(f"paper figure source missing: {PAPER_FIG_SOURCE}")
    paper_fig = HERE / "paper_fig.png"
    shutil.copyfile(PAPER_FIG_SOURCE, paper_fig)

    state = FrameState(
        scene_kind=SceneKind.SLIDE,
        title="Figure 1",
        section="Figure 1",
        background_image=str(paper_fig),
        caption="A paper figure becomes a full-frame background, narrated in place.",
    )
    img = render_frame(state, CANVAS, theme=THEMES["paper"])
    return _save(img, "frame_paper.png")


def make_waveform() -> Path:
    """A waveform scrubber strip synthesized from a real non-silent WAV."""
    import math

    wav_path = HERE / "_tmp_waveform.wav"
    sample_rate = 22050
    duration_s = 2.0
    n = int(sample_rate * duration_s)
    frames = bytearray()
    for i in range(n):
        # An amplitude-modulated tone: non-silent, with a moving envelope so the
        # bars vary in height like real speech.
        t = i / sample_rate
        env = 0.35 + 0.65 * abs(math.sin(2 * math.pi * 0.9 * t))
        sample = int(env * 12000 * math.sin(2 * math.pi * 180.0 * t))
        sample = max(-32768, min(32767, sample))
        frames += int(sample).to_bytes(2, "little", signed=True)
    with wave.open(str(wav_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(frames))

    envelope = compute_envelope(wav_path, bars=200)
    if max(envelope) <= 0.0:
        raise RuntimeError("synthesized WAV produced a silent envelope")
    img = Image.new("RGB", WAVE_CANVAS, BG)
    _wd = ImageDraw.Draw(img)
    draw_waveform(
        _wd, (0, 0, WAVE_CANVAS[0], WAVE_CANVAS[1]), envelope, progress=0.55,
        bar_color=_mix(BG, FG, 0.30), played_color=ACCENT,
        playhead_color=(245, 245, 250),
    )
    out = _save(img, "waveform.png")
    wav_path.unlink(missing_ok=True)
    return out


def make_themes() -> Path:
    """The same code frame rendered under all five preset themes (titled grid)."""
    state = FrameState(
        scene_kind=SceneKind.CODEBASE,
        file_path="schema.py",
        code_lines=THEME_CODE,
        highlight_lines=[4],
        section="Themes",
        caption="One frame, five themes — colors and font ratios are configurable.",
    )
    img, draw, content_top = _canvas(
        "Five themes, one frame",
        "the same CODEBASE frame rendered under each preset theme (noir is the "
        "default) — every color and font ratio is configurable",
    )
    width, height = CANVAS
    margin = int(width * 0.04)
    label_h = int(height * 0.045)
    gap = int(width * 0.018)
    grid_bottom = height - margin
    cols, rows = 3, 2
    cell_w = (width - 2 * margin - (cols - 1) * gap) // cols
    cell_h = (grid_bottom - content_top - label_h * rows - gap) // rows
    label_font = scaled_font(height, 0.026)
    order = ["noir", "dark", "light", "midnight", "paper"]
    for idx, name in enumerate(order):
        c, r = idx % cols, idx // cols
        cx = margin + c * (cell_w + gap)
        cy = content_top + r * (cell_h + label_h + gap)
        draw.text((cx, cy), name.upper(), fill=ACCENT, font=label_font)
        tile = render_frame(state, (cell_w, cell_h), theme=THEMES[name])
        img.paste(tile, (cx, cy + label_h))
        draw.rectangle([cx, cy + label_h, cx + cell_w - 1, cy + label_h + cell_h - 1],
                       outline=_mix(BG, ACCENT, 0.45), width=2)
    return _save(img, "themes.png")


def make_typing_filmstrip() -> Path:
    """Three columns of the SAME editor frame typed to 25%, 55%, and 100%.

    Demonstrates the character-by-character typing reveal: a single
    :class:`FrameState` re-rendered at progressive ``cursor_typed`` counts — the
    exact mechanism the animator uses per output frame — with pygments coloring
    the code as it appears. The three panels sit under a shared title with a
    per-panel label, fit-CONTAINed so nothing is cropped.
    """
    img, draw, content_top = _canvas(
        "Typing reveal — one FrameState, growing cursor_typed",
        "a single editor frame re-rendered at progressive character counts; "
        "pygments colors the code as it appears",
    )
    width, height = CANVAS
    margin = int(width * 0.04)
    label_h = int(height * 0.045)
    gap = int(width * 0.02)
    bottom = height - margin
    n = 3
    cell_w = (width - 2 * margin - gap * (n - 1)) // n
    cell_h = bottom - content_top - label_h
    label_font = scaled_font(height, 0.028)

    total = sum(len(line) for line in TYPING_CODE_LINES)
    fractions = (0.25, 0.55, 1.0)
    for col, frac in enumerate(fractions):
        typed = int(total * frac)
        state = FrameState(
            scene_kind=SceneKind.CODEBASE,
            file_path="assembly/animator.py",
            code_lines=TYPING_CODE_LINES,
            highlight_lines=[11],
            cursor_typed=typed,
        )
        cx = margin + col * (cell_w + gap)
        draw.text((cx, content_top), f"TYPED {int(frac * 100)}%",
                  fill=ACCENT, font=label_font)
        tile = render_frame(state, (cell_w, cell_h), theme=THEMES["noir"])
        img.paste(tile, (cx, content_top + label_h))
        draw.rectangle([cx, content_top + label_h, cx + cell_w - 1,
                        content_top + label_h + cell_h - 1],
                       outline=_mix(BG, ACCENT, 0.45), width=2)
    return _save(img, "typing_filmstrip.png")


def _load_latency_metrics() -> list[tuple[str, float, str]]:
    """Read measured latency metrics from ``benchmarks.json``.

    Returns ``(label, milliseconds, value_text)`` triples for the bars, taken
    verbatim from the real benchmark file — never invented.
    """
    if not BENCHMARKS.is_file():
        raise FileNotFoundError(f"benchmarks file missing: {BENCHMARKS}")
    data = json.loads(BENCHMARKS.read_text(encoding="utf-8"))
    build_ms = float(data["build"]["median_ms"])
    render_ms = float(data["render"]["ms_per_output_second"])
    fps = int(data["render"]["animation_fps"])
    return [
        ("Build pipeline (median)", build_ms, f"{build_ms:g} ms"),
        (
            f"Animated render (compute per output second @ {fps}fps)",
            render_ms,
            f"{render_ms:g} ms",
        ),
    ]


def make_latency() -> Path:
    """A pure-Pillow horizontal bar chart of the measured latency numbers.

    Bars are scaled to the largest measured value and labelled with the exact
    millisecond figures read from ``benchmarks.json``. No matplotlib; the chart
    is drawn directly, matching the manuscript's zero-extra-dependency stance.
    Axis labels and value labels are kept fully inside the canvas with generous
    margins so nothing is clipped.
    """
    width, height = CANVAS
    metrics = _load_latency_metrics()
    img, draw, content_top = _canvas(
        "Measured latency (lower is better)",
        "read at render time from data/benchmarks.json — never hardcoded",
    )

    margin = int(width * 0.04)
    label_font = scaled_font(height, 0.030)
    value_font = scaled_font(height, 0.034, mono=True)

    # Reserve a fixed right gutter wide enough for the longest value label so the
    # value text always lands inside the canvas.
    value_gutter = int(max(draw.textlength(v, font=value_font)
                           for _, _, v in metrics)) + int(width * 0.03)
    bar_left = margin
    bar_max_w = width - margin - value_gutter - bar_left

    n = len(metrics)
    region_top = content_top + int(height * 0.04)
    region_bottom = height - int(height * 0.08)
    slot_h = (region_bottom - region_top) // n
    bar_h = int(slot_h * 0.42)
    label_gap = int(height * 0.012)
    max_ms = max(ms for _, ms, _ in metrics)

    for i, (label, ms, value_text) in enumerate(metrics):
        slot_top = region_top + i * slot_h
        draw.text((bar_left, slot_top), label, fill=DIM, font=label_font)
        y = slot_top + label_font.size + label_gap
        # Track (full width) then filled bar, both rounded.
        radius = int(bar_h * 0.18)
        draw.rounded_rectangle([bar_left, y, bar_left + bar_max_w, y + bar_h],
                               radius=radius, fill=_mix(BG, FG, 0.08))
        w = max(6, int(bar_max_w * (ms / max_ms)))
        draw.rounded_rectangle([bar_left, y, bar_left + w, y + bar_h],
                               radius=radius, fill=ACCENT)
        # Value label in the reserved right gutter, vertically centered on the bar.
        vx = bar_left + bar_max_w + int(width * 0.02)
        vy = y + (bar_h - value_font.size) // 2
        draw.text((vx, vy), value_text, fill=FG, font=value_font)
    return _save(img, "latency.png")


def make_paper_flow() -> Path:
    """A left-to-right flow diagram of the paper pipeline (real diagram renderer).

    Uses :func:`render_architecture_diagram` — the same renderer the package
    ships — to draw the PDF -> poppler -> structure/figures/pages/codebase ->
    ``build_paper_demo`` -> narrated video flow under the academic ``paper`` theme.
    """
    paper = THEMES["paper"]
    columns: list[tuple[str, list[DiagramNode]]] = [
        ("Source", [DiagramNode("PDF", ["paper + figures + code"])]),
        (
            "poppler (zero-pip)",
            [
                DiagramNode("pdfinfo", ["metadata"]),
                DiagramNode("pdftotext", ["text"]),
                DiagramNode("pdftoppm", ["page rasters"]),
            ],
        ),
        (
            "Extract",
            [
                DiagramNode("structure", ["abstract / captions", "sections (skip TOC)"]),
                DiagramNode("figures", ["collected PNGs"]),
                DiagramNode("pages", ["rendered"]),
                DiagramNode("codebase", ["ast summary"]),
            ],
        ),
        ("Compose", [DiagramNode("build_paper_demo", ["Demo value"])]),
        ("Render", [DiagramNode("Narrated video", ["content-verified"])]),
    ]
    img = render_architecture_diagram(
        CANVAS,
        title="Paper Pipeline — PDF to Narrated Video",
        columns=columns,
        bg=paper.bg_slide,
        accent=paper.accent,
        fg=paper.text,
    )
    return _save(img, "paper_flow.png")


def make_provenance() -> Path:
    """A labelled diagram of the THREE provenance carriers from one config.

    Draws, in pure Pillow, the three ways a single :class:`MetadataConfig` stamps
    provenance onto a render: (a) on-screen top/bottom overlay bars, (b) MP4
    container metadata tags, and (c) a signed steganographic payload hidden in
    lossless poster/bookend PNGs. Every label is read from a *real*
    ``MetadataConfig`` instance, so the figure cannot drift from the package's
    own field names and defaults.
    """
    # One real config drives every label below — the same dataclass the renderer,
    # the animator, the metadata embedder, and the stego encoder all consume.
    meta = MetadataConfig(
        author="Daniel Ari Friedman",
        source="democreate (repo)",
        url="https://github.com/...",
        watermark="democreate",
        title="DemoCreate",
        date="2026-06-04",
        header=True,
        footer=True,
        show_clock=True,
        container_tags=True,
        steganography=True,
    )

    width, height = CANVAS
    img, draw, content_top = _canvas(
        "One MetadataConfig — three provenance carriers",
        "the same author / source / url / title fields are stamped on screen, "
        "into the container, and hidden in lossless PNGs",
    )
    margin = int(width * 0.04)

    # Distinct accent per carrier so the three columns read apart at a glance.
    c_overlay = (124, 214, 124)   # on-screen
    c_tags = (224, 175, 104)      # container
    c_stego = (197, 134, 232)     # steganographic

    head_font = scaled_font(height, 0.028)
    body_font = scaled_font(height, 0.0215)
    mono_font = scaled_font(height, 0.0195, mono=True)
    note_font = scaled_font(height, 0.019)

    # Source chip: the single config every carrier is fed from.
    chip_w, chip_h = int(width * 0.30), int(height * 0.066)
    chip_x = (width - chip_w) // 2
    chip_y = content_top
    draw.rounded_rectangle([chip_x, chip_y, chip_x + chip_w, chip_y + chip_h],
                           radius=12, fill=_mix(BG, ACCENT, 0.18), outline=ACCENT, width=2)
    chip_label = "MetadataConfig (config.py)"
    cl_w = draw.textlength(chip_label, font=head_font)
    draw.text((chip_x + (chip_w - cl_w) // 2, chip_y + int(chip_h * 0.30)),
              chip_label, fill=FG, font=head_font)

    cols = [
        (
            c_overlay,
            "(a) On-screen overlay bars",
            "export/overlay.py · draw_header / draw_footer",
            [
                f"header (top): title · section   [header={str(meta.header).lower()}]",
                "footer (bottom edge): author · source · url",
                f"running clock + watermark   [show_clock={str(meta.show_clock).lower()}]",
                "burned into every video frame (_draw_overlays)",
            ],
            "survives H.264 (it IS the pixels)",
        ),
        (
            c_tags,
            "(b) MP4 container tags",
            "export/metadata.py · build_tags / embed_tags",
            [
                f"title = {meta.title!r}",
                f"artist = {meta.author!r}",
                "comment = 'made with DemoCreate …'",
                f"date = {meta.date!r}   [via ffmpeg -metadata]",
            ],
            "read by players / ffprobe",
        ),
        (
            c_stego,
            "(c) Steganographic signed PNG",
            "export/stego.py · embed_provenance (LSB)",
            [
                "signed payload → poster_signed.png",
                "+ transmission-bookend PNG sidecars",
                "tool / version / author / scenes / chunks",
                "content_sha256 (excludes render state)",
            ],
            "lossless PNG only — NOT the H.264 video",
        ),
    ]

    gap = int(width * 0.025)
    col_top = chip_y + chip_h + int(height * 0.07)
    col_bottom = height - margin
    n = len(cols)
    avail = width - 2 * margin - gap * (n - 1)
    col_w = avail // n

    for i, (caccent, header, srcline, bullets, foot) in enumerate(cols):
        cx = margin + i * (col_w + gap)
        # Connector from the central config chip down into each column header.
        src_cx = chip_x + chip_w // 2
        draw.line([(src_cx, chip_y + chip_h), (cx + col_w // 2, col_top)],
                  fill=caccent, width=2)
        draw.polygon(
            [(cx + col_w // 2, col_top),
             (cx + col_w // 2 - 7, col_top - 12),
             (cx + col_w // 2 + 7, col_top - 12)],
            fill=caccent,
        )

        draw.rounded_rectangle([cx, col_top, cx + col_w, col_bottom],
                               radius=14, fill=PANEL, outline=caccent, width=2)
        pad = int(col_w * 0.06)
        # Carrier title.
        ty = col_top + pad
        for line in _wrap(draw, header, head_font, col_w - 2 * pad):
            draw.text((cx + pad, ty), line, fill=caccent, font=head_font)
            ty += int(head_font.size * 1.25)
        # Source module (mono).
        ty += int(height * 0.006)
        for line in _wrap(draw, srcline, mono_font, col_w - 2 * pad):
            draw.text((cx + pad, ty), line, fill=DIM, font=mono_font)
            ty += int(mono_font.size * 1.35)
        # Bullets.
        ty += int(height * 0.012)
        for b in bullets:
            draw.ellipse([cx + pad, ty + int(body_font.size * 0.35),
                          cx + pad + 7, ty + int(body_font.size * 0.35) + 7],
                         fill=caccent)
            bx = cx + pad + 18
            for line in _wrap(draw, b, body_font, col_w - 2 * pad - 18):
                draw.text((bx, ty), line, fill=FG, font=body_font)
                ty += int(body_font.size * 1.32)
            ty += int(body_font.size * 0.22)
        # Survivability footer note, pinned near the bottom of the panel.
        note_y = col_bottom - pad - int(note_font.size * 2.2)
        draw.line([(cx + pad, note_y - 8), (cx + col_w - pad, note_y - 8)],
                  fill=_mix(PANEL, caccent, 0.4), width=1)
        for line in _wrap(draw, foot, note_font, col_w - 2 * pad):
            draw.text((cx + pad, note_y), line, fill=caccent, font=note_font)
            note_y += int(note_font.size * 1.25)

    return _save(img, "provenance.png")


def _package_still_cells() -> list[tuple[str, str]]:
    """Pick the two package-row stills, preferring the v0.6.1 showcase frames.

    The canonical package demo is now the *showcase* (``democreate_showcase.json``),
    which exercises the new bullet- and stat-card surfaces. When its refreshed
    stills are present in ``docs/_videoframes/`` we use them so the montage shows
    the definitive demo; otherwise we fall back to the older intro stills. Returns
    ``(filename, label)`` pairs for the two top-row cells.
    """
    # Preferred showcase still: the stat-card slide (a new v0.6.1 surface). The
    # second package cell is a code-typing scene, reused under either lineage.
    if (VIDEOFRAMES / "showcase_stats.png").is_file():
        first = ("showcase_stats.png", "Showcase: by the numbers")
    elif (VIDEOFRAMES / "package_title.png").is_file():
        first = ("package_title.png", "Package: bullets")
    else:
        raise FileNotFoundError(
            f"no package-row still found in {VIDEOFRAMES} "
            "(expected showcase_stats.png or package_title.png)"
        )
    return [first, ("package_typing.png", "Package: typing")]


def make_video_stills() -> Path:
    """A 2x2 montage of FOUR real stills from the two produced demo videos.

    The frames are extracted from the actual encoded MP4s — the canonical package
    *showcase* (``output/video/demo.mp4``) and the research-paper demo
    (``output/paper_demo/video/demo.mp4``) — so the montage is direct evidence
    that the renders are real, playable, content-verified deliverables. The
    package row prefers the v0.6.1 showcase stills (the stat-card slide, a code
    scene) when present, falling back to the older intro stills. Each source still
    is fit-CONTAINed into its cell (no crop, no stretch) under a titled header
    with a per-cell label. If any source still is missing the build raises rather
    than producing a degraded figure.
    """
    img, draw, content_top = _canvas(
        "Real stills from the two produced demos",
        "frames lifted directly out of the encoded MP4s — the package showcase "
        "and the research-paper demo",
    )
    width, height = CANVAS
    margin = int(width * 0.04)
    label_h = int(height * 0.045)
    gap = int(width * 0.02)
    bottom = height - margin
    cols, rows = 2, 2
    cell_w = (width - 2 * margin - gap) // cols
    cell_h = (bottom - content_top - label_h * rows - gap) // rows
    label_font = scaled_font(height, 0.028)

    # (filename, label, (col, row)) — order reads package row then paper row. The
    # package row prefers the v0.6.1 showcase stills when present.
    (pkg0, pkg1) = _package_still_cells()
    cells = [
        (pkg0[0], pkg0[1], (0, 0)),
        (pkg1[0], pkg1[1], (1, 0)),
        ("paper_abstract.png", "Paper: abstract", (0, 1)),
        ("paper_figure.png", "Paper: figure", (1, 1)),
    ]

    for name, label, (col, row) in cells:
        src = VIDEOFRAMES / name
        if not src.is_file():
            raise FileNotFoundError(f"video still source missing: {src}")
        still = Image.open(src).convert("RGB")
        cx = margin + col * (cell_w + gap)
        cy = content_top + row * (cell_h + label_h + gap)
        draw.text((cx, cy), label, fill=ACCENT, font=label_font)
        _fit_contain(img, still, (cx, cy + label_h, cx + cell_w, cy + label_h + cell_h))

    return _save(img, "video_stills.png")


def main() -> None:
    """Generate every manuscript figure, raising on any failure."""
    HERE.mkdir(parents=True, exist_ok=True)
    builders = [
        make_architecture,
        make_frame_code,
        make_frame_title,
        make_frame_paper,
        make_waveform,
        make_themes,
        make_typing_filmstrip,
        make_latency,
        make_paper_flow,
        make_provenance,
        make_video_stills,
    ]
    written: list[Path] = []
    for build in builders:
        path = build()
        written.append(path)
        print(f"wrote {path.relative_to(HERE.parent.parent)}")
    print(f"\nDone: {len(written)} figures in {HERE}")


if __name__ == "__main__":
    main()
