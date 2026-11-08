#!/usr/bin/env python3
"""Generate candidate manuscript illustrations from committed repository inputs.

Run from the repository root with::

    .venv/bin/python docs/manuscript/figures/make_figures.py

Outputs stay in docs/manuscript/figures and root output/figures. paper_fig.png
is the committed local paper-background input, never discovered in a sibling
project. Current timing and decoded-frame figures consume committed, source-bound
engineering records. These observations do not establish acoustic accuracy,
intelligibility, authentication or publication readiness.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import textwrap
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
from democreate.assembly.compositor import Timeline
from democreate.capture.screen import render_frame
from democreate.config import THEMES, MetadataConfig
from democreate.media import FrameState
from democreate.schema import Action, SceneKind

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]

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

# Committed standalone input; external paper refreshes must be explicit.
PAPER_FIG = HERE / "paper_fig.png"

# Separate records preserve historical measurements without relabelling them.
BENCHMARKS = REPO / "data" / "benchmarks-0.8.0.json"
EVIDENCE = REPO / "data" / "release-0.8.0.json"

# Current public timing source, obtained from the installed checkout rather than
# a hand-maintained copy of a removed implementation.
TYPING_CODE_LINES = textwrap.dedent(
    inspect.getsource(Timeline.entry_at_ms)
).splitlines()

# Current serialization source, also obtained verbatim from the live symbol.
CODE_LINES = textwrap.dedent(inspect.getsource(Action.to_dict)).splitlines()

# Schematic (not verbatim source) for small theme-grid cells; the full source
# excerpt is too wide for a ~470px tile.
THEME_CODE = [
    "@dataclass",
    "class Action:",
    "    type: ActionType",
    "    params: dict",
    "    trigger_word: str | None",
]


# --- shared helpers --------------------------------------------------------

def _save(img: Image.Image, name: str) -> Path:
    """Save ``img`` under ``docs/manuscript/figures/``, mirrored into ``output/figures/``.

    Figures are checked in under ``docs/manuscript/figures/`` for the project's own
    ``build_manuscript.py``; they are *also* mirrored into ``output/figures/`` so
    the shared template render pipeline — which resolves a ``figures/x.png``
    reference to ``output/figures/`` — finds them and renders natively.
    """
    out = HERE / name
    img.save(out, format="PNG")
    if not out.is_file() or out.stat().st_size == 0:
        raise RuntimeError(f"figure {name} was not written")
    mirror = REPO / "output" / "figures" / name
    mirror.parent.mkdir(parents=True, exist_ok=True)
    img.save(mirror, format="PNG")
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
        caption="Current source: democreate.schema.Action.to_dict.",
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
    paper_fig = PAPER_FIG
    if not paper_fig.is_file():
        raise FileNotFoundError(f"committed paper figure missing: {paper_fig}")

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
        caption="One frame, five themes - colors and font ratios are configurable.",
    )
    img, draw, content_top = _canvas(
        "Five themes, one frame",
        "the same CODEBASE frame rendered under each preset theme (noir is the "
        "default); every color and font ratio is configurable",
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

    Illustrates character-count reveal with a current public timing excerpt.
    These are synthetic renderer states, not captures of scheduled playback.
    The three panels share a title and per-panel label and are fit-CONTAINed.
    """
    img, draw, content_top = _canvas(
        "Typing reveal: one FrameState, growing cursor_typed",
        "current source: democreate.assembly.compositor.Timeline.entry_at_ms; "
        "synthetic character-count illustration",
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
            file_path="assembly/compositor.py",
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


def make_latency() -> Path:
    """Show observed timing in separate cards without a mixed-unit bar axis."""
    data = json.loads(BENCHMARKS.read_text(encoding="utf-8"))
    build, render = data["build"], data["render"]
    if render is None:
        raise ValueError("current timing figure requires an observed encoded render")
    img, draw, content_top = _canvas(
        "Measured starter workload - 0.8.0 candidate",
        "one host / one synthetic silent input / wall clock; not the voiced corpus",
    )
    width, height = CANVAS
    margin, gap = int(width * 0.04), int(width * 0.025)
    panel_w = (width - 2 * margin - gap) // 2
    top, bottom = content_top + 30, int(height * 0.76)
    cards = [
        (
            "Build wall clock",
            f"{build['median_ms']:g}",
            f"ms, median of {build['runs']} consecutive builds",
            [
                "Validation, TTS, sync, frames and exports.",
                "Input construction and process imports are not timed.",
                f"First timed build: {build['samples_ms'][0]:.1f} ms.",
                "All raw samples retained; no warm-up sample excluded.",
            ],
        ),
        (
            "Whole render wall clock",
            f"{render['ms_per_output_second']:g}",
            "ms per encoded output second",
            [
                "Audio processing, animation, encode and sidecars.",
                f"Video: {render['output_seconds']:.6f} s at "
                f"{render['animation_fps']} fps.",
                f"Planned timeline: {render['timeline_seconds']:.3f} s.",
                "ffprobe duration is measured outside the timer.",
                "Content verification is disabled for this timing.",
            ],
        ),
    ]
    for index, (heading, value, unit, notes) in enumerate(cards):
        x = margin + index * (panel_w + gap)
        draw.rounded_rectangle(
            (x, top, x + panel_w, bottom), radius=14, fill=PANEL,
            outline=ACCENT, width=2,
        )
        draw.text((x + 24, top + 24), heading, font=scaled_font(height, 0.030), fill=FG)
        draw.text((x + 24, top + 80), value, font=scaled_font(height, 0.075), fill=ACCENT)
        draw.text((x + 24, top + 170), unit, font=scaled_font(height, 0.025), fill=FG)
        y = top + 230
        font = scaled_font(height, 0.023)
        for note in notes:
            for line in _wrap(draw, note, font, panel_w - 48):
                draw.text((x + 24, y), line, font=font, fill=DIM)
                y += int(font.size * 1.5)
    font = scaled_font(height, 0.021)
    footer = [
        "Source: data/benchmarks-0.8.0.json; measured "
        + data["identity"]["recorded_at_utc"],
        "Different denominators, no shared scale. No compatible historical "
        "comparison or performance-improvement claim.",
    ]
    y = bottom + 30
    for text in footer:
        for line in _wrap(draw, text, font, width - 2 * margin):
            draw.text((margin, y), line, font=font, fill=DIM)
            y += int(font.size * 1.5)
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
        title="Paper Pipeline: PDF to Narrated Video",
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
    container metadata tags, and (c) an unsigned steganographic payload hidden in
    lossless poster PNGs. Every label is read from a *real*
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
        "One MetadataConfig: three provenance carriers",
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
            "(c) Unsigned steganographic PNG",
            "export/stego.py · embed_provenance (LSB)",
            [
                "unsigned payload -> poster_signed.png",
                "+ provenance.json sidecar",
                "tool / version / author / scenes / chunks",
                "content_sha256 (consistency, not identity)",
            ],
            "lossless PNG only - NOT the H.264 video",
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


def make_video_stills() -> Path:
    """Compose digest-checked decoded frames from the recorded candidate MP4."""
    canonical = json.loads(EVIDENCE.read_text(encoding="utf-8"))["canonical"]
    frames = canonical["decoded_frames"]
    if len(frames) != 6:
        raise ValueError("the current montage requires six recorded decoded frames")
    img, draw, content_top = _canvas(
        "Canonical package showcase - 0.8.0 candidate",
        "Kokoro af_heart / 3840x2160 / 15 fps; representative decoded frames, "
        "not acoustic accuracy",
    )
    width, height = CANVAS
    margin, gap = int(width * 0.04), int(width * 0.02)
    label_h = int(height * 0.035)
    cols, rows = 3, 2
    cell_w = (width - 2 * margin - gap * (cols - 1)) // cols
    bottom = height - margin - 30
    cell_h = (bottom - content_top - label_h * rows - gap) // rows
    for index, frame in enumerate(frames):
        source = (REPO / frame["path"]).resolve(strict=True)
        if not source.is_relative_to(REPO.resolve()):
            raise ValueError("recorded still escapes the repository")
        with source.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != frame["sha256"]:
                raise ValueError(f"recorded still digest mismatch: {frame['path']}")
            stream.seek(0)
            with Image.open(stream) as decoded:
                still = decoded.convert("RGB")
        x = margin + (index % cols) * (cell_w + gap)
        y = content_top + (index // cols) * (cell_h + label_h + gap)
        draw.text(
            (x, y), f"cue {frame['cue']}, seek {frame['seek_seconds']:.3f} s",
            font=scaled_font(height, 0.021), fill=ACCENT,
        )
        _fit_contain(img, still, (x, y + label_h, x + cell_w, y + label_h + cell_h))
    draw.text(
        (margin, height - margin), "MP4 SHA-256: " + canonical["video_sha256"],
        font=scaled_font(height, 0.018), fill=DIM,
    )
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
