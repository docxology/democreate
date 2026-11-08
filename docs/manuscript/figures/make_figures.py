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
import sys
import textwrap
import wave
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))


from figure_layout import ACCENT, BG, DIM, FG, PANEL, arrow, card, text  # noqa: E402

from democreate.animation.fonts import load_font, scaled_font  # noqa: E402
from democreate.animation.waveform import (  # noqa: E402
    compute_envelope,
    draw_waveform,
)
from democreate.assembly.compositor import Timeline  # noqa: E402
from democreate.capture.screen import render_frame  # noqa: E402
from democreate.config import THEMES, MetadataConfig  # noqa: E402
from democreate.media import FrameState  # noqa: E402
from democreate.schema import Action, SceneKind  # noqa: E402

# --- shared visual language ------------------------------------------------
# The schematics share a bounded text layout and the package's bundled font.
# Synthetic renderer states, measured timing and decoded stills remain separate.
CANVAS: tuple[int, int] = (1600, 900)
WAVE_CANVAS: tuple[int, int] = (1600, 300)


# Committed standalone input; external paper refreshes must be explicit.
PAPER_FIG = HERE / "paper_fig.png"

# Separate records preserve historical measurements without relabelling them.
BENCHMARKS = REPO / "data" / "benchmarks-0.8.0.json"
EVIDENCE = REPO / "data" / "release-0.8.0.json"
MEDIA_EVIDENCE = REPO / "data" / "visual-refresh-2026-11-08.json"

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
    title_size = int(height * 0.052)
    title_height = text(
        draw, (margin, int(height * 0.045), width - margin, int(height * 0.20)),
        title, size=title_size,
    )
    y = int(height * 0.045) + title_height + 14
    if subtitle:
        y += text(
            draw, (margin, y, width - margin, y + int(height * 0.17)),
            subtitle, size=int(height * 0.029), fill=DIM,
        )
        y += 10
    rule_y = y + 6
    draw.line([(margin, rule_y), (width - margin, rule_y)], fill=ACCENT, width=3)
    content_top = rule_y + 26
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


def _source(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    lines: list[str],
) -> None:
    """Draw every source character, preserving spaces and marking visual wraps."""
    x0, y0, x1, y1 = box
    for size in range(26, 21, -1):
        font = load_font(size, mono=True)
        rows: list[tuple[str, str]] = []
        for number, line in enumerate(lines, start=1):
            current = ""
            label = str(number)
            for char in line:
                if current and draw.textlength(current + char, font=font) > x1 - x0 - 84:
                    rows.append((label, current))
                    label, current = ">", ""
                current += char
            rows.append((label, current))
        step = int(size * 1.36)
        if len(rows) * step <= y1 - y0 - 32:
            break
    else:
        raise ValueError("complete source does not fit the figure's reading panel")
    draw.rounded_rectangle(box, radius=12, fill=PANEL, outline=ACCENT, width=1)
    for index, (label, row) in enumerate(rows):
        y = y0 + 16 + index * step
        draw.text((x0 + 12, y), label, font=load_font(size - 4), fill=DIM,
                  anchor="lt")
        draw.text((x0 + 64, y), row, font=font, fill=FG, anchor="lt")


# --- builders --------------------------------------------------------------

def make_architecture() -> Path:
    """Show the spine, timing and scheduled state flow with dependency boundaries."""
    img, draw, top = _canvas(
        "From authored Demo to timed visual states",
        "Schematic: inputs and assets are authored; clip durations are measured; "
        "word times are estimated.",
    )
    stages = [
        ("AUTHOR", "Demo", "Scenes / chunks / actions\n"
         "Narration + trigger words\nAssets + RenderConfig",
         "Caller input stays reusable."),
        ("RESOLVE TIME", "AudioClip + timeline", "Silent WAVs in the core\n"
         "Measured clip windows\nCharacter-weighted words\nAuthored times preserved",
         "Not detected acoustic onsets."),
        ("COMPILE", "FrameState at time t", "Scheduled action updates\n"
         "Synthetic editor / slides\nCaptions + timed image HTML",
         "HTML does not play speech."),
    ]
    for index, (label, heading, body, foot) in enumerate(stages):
        x = 64 + index * 504
        card(draw, (x, top, x + 464, 716), label, heading, body,
             foot=foot, size=28)
        if index < 2:
            arrow(draw, (x + 472, 460), (x + 496, 460))
    text(draw, (64, 752, 1536, 852),
         "Optional path: system / Kokoro speech + ffmpeg -> voiced MP4. "
         "Whisper / Chatterbox / Manim are unwired slots.\n"
         "Deterministic comparisons require fixed input, assets, config "
         "and environment.", size=27, fill=DIM)
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
        caption="Committed paper figure, contain-fit inside the slide content area.",
    )
    img = render_frame(state, CANVAS, theme=THEMES["paper"])
    return _save(img, "frame_paper.png")


def make_waveform() -> Path:
    """Render a labelled synthetic tone envelope, never a speech measurement."""
    import math

    wav_path = HERE / "_tmp_waveform.wav"
    sample_rate = 22050
    duration_s = 2.0
    n = int(sample_rate * duration_s)
    frames = bytearray()
    for i in range(n):
        # Deterministic amplitude-modulated tone; this is not sampled speech.
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
        _wd, (64, 72, WAVE_CANVAS[0] - 128, 162), envelope, progress=0.55,
        bar_color=_mix(BG, FG, 0.30), played_color=ACCENT,
        playhead_color=(245, 245, 250),
    )
    text(_wd, (64, 16, 1536, 60),
         "Synthetic tone envelope | 55% illustrative progress", size=30)
    text(_wd, (64, 250, 1536, 292),
         "2.0 s amplitude-modulated 180 Hz tone; not speech or onset evidence.",
         size=25, fill=DIM)
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
        caption="",
    )
    img, draw, content_top = _canvas(
        "Theme presets change appearance, not content",
        "Five synthetic CODEBASE renders of one schematic Action model "
        "(not a verbatim source excerpt). NOIR is the default.",
    )
    width, height = CANVAS
    margin = int(width * 0.04)
    label_h = int(height * 0.045)
    gap = int(width * 0.018)
    grid_bottom = height - margin
    cols, rows = 3, 2
    cell_w = (width - 2 * margin - (cols - 1) * gap) // cols
    cell_h = (grid_bottom - content_top - label_h * rows - gap) // rows
    label_font = scaled_font(height, 0.031)
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
    cx = margin + 2 * (cell_w + gap)
    cy = content_top + cell_h + label_h + gap
    text(draw, (cx, cy, cx + cell_w, cy + label_h), "COMPARISON KEY",
         size=27, fill=ACCENT)
    text(draw, (cx, cy + label_h + 16, cx + cell_w, grid_bottom),
         "Same schematic code and highlight.\n"
         "Only the Theme preset changes.\n\n"
         "Surfaces, syntax colors, accents and captions are configurable.",
         size=27, minimum=25, fill=DIM)
    return _save(img, "themes.png")


def make_typing_filmstrip() -> Path:
    """Pair complete current source with three synthetic reveal-state previews."""
    img, draw, top = _canvas(
        "Character-count reveal, not speech recognition",
        "Complete current source: "
        "democreate.assembly.compositor.Timeline.entry_at_ms",
    )
    text(draw, (64, top, 1048, top + 40), "LIVE SOURCE / COMPLETE METHOD",
         size=25, fill=ACCENT)
    _source(draw, (64, top + 44, 1048, 810), TYPING_CODE_LINES)
    total = sum(len(line) for line in TYPING_CODE_LINES)
    for index, fraction in enumerate((0.25, 0.55, 1.0)):
        typed = int(total * fraction)
        y = top + index * 204
        text(draw, (1090, y, 1536, y + 36),
             f"{int(fraction * 100)}% | {typed} / {total} characters",
             size=25, fill=FG)
        draw.rectangle((1090, y + 40, 1536, y + 48), fill=PANEL)
        draw.rectangle((1090, y + 40, 1090 + int(446 * fraction), y + 48),
                       fill=ACCENT)
        state = FrameState(
            scene_kind=SceneKind.CODEBASE,
            file_path="assembly/compositor.py",
            code_lines=TYPING_CODE_LINES,
            highlight_lines=[11],
            cursor_typed=typed,
        )
        # Render at a source-legible geometry, then contain-fit the miniature.
        # The complete source above is the reading surface, not these previews.
        tile = render_frame(state, (900, 600), theme=THEMES["noir"])
        _fit_contain(img, tile, (1090, y + 62, 1536, y + 190))
    text(draw, (64, 836, 1536, 884),
         "Counts exclude newline separators, matching cursor_typed. "
         "Previews are synthetic states, not scheduled playback.", size=25, fill=DIM)
    return _save(img, "typing_filmstrip.png")


def make_latency() -> Path:
    """Show source-bound timing with independent units, never a shared bar axis."""
    record = json.loads(EVIDENCE.read_text(encoding="utf-8"))["benchmark"]
    raw = BENCHMARKS.read_bytes()
    if (record["path"] != BENCHMARKS.relative_to(REPO).as_posix()
            or hashlib.sha256(raw).hexdigest() != record["sha256"]):
        raise ValueError("timing record does not match the recorded benchmark digest")
    data = json.loads(raw)
    if data["identity"]["source_sha256"] != record["source_sha256"]:
        raise ValueError("benchmark source identity does not match its release record")
    build, render = data["build"], data["render"]
    if render is None:
        raise ValueError("timing figure requires an observed encoded render")
    img, draw, top = _canvas(
        "Observed wall clock for one silent workload",
        "Historical source-bound observation: one host / synthetic silent input; "
        "not the annotated voiced corpus.",
    )
    cards = [
        (
            "BUILD WALL CLOCK", f"{build['median_ms']:g}",
            f"ms | median of {build['runs']} consecutive builds",
            "Validation, TTS, sync, frames and exports.\n"
            "Input construction and process imports are not timed.\n"
            f"First timed build: {build['samples_ms'][0]:.1f} ms.\n"
            "All samples retained; no warm-up sample excluded.",
        ),
        (
            "WHOLE RENDER WALL CLOCK", f"{render['ms_per_output_second']:g}",
            "ms per encoded output second",
            "Audio processing, animation, encode and sidecars.\n"
            f"Video: {render['output_seconds']:.6f} s at "
            f"{render['animation_fps']} fps.\n"
            f"Planned timeline: {render['timeline_seconds']:.3f} s.\n"
            "ffprobe duration is outside the timer.\n"
            "Content verification disabled for this timing.",
        ),
    ]
    for index, (heading, value, unit, notes) in enumerate(cards):
        x = 64 + index * 756
        draw.rounded_rectangle((x, top, x + 716, 694), radius=16,
                               fill=PANEL, outline=ACCENT, width=2)
        text(draw, (x + 28, top + 24, x + 688, top + 70), heading,
             size=28, fill=FG)
        text(draw, (x + 28, top + 86, x + 688, top + 204), value,
             size=86, fill=ACCENT)
        text(draw, (x + 28, top + 214, x + 688, top + 260), unit, size=27)
        text(draw, (x + 28, top + 278, x + 688, 674), notes,
             size=26, minimum=24, fill=DIM)
    text(draw, (64, 726, 1536, 862),
         "Source: data/benchmarks-0.8.0.json | "
         + data["identity"]["recorded_at_utc"] + "\n"
         + "Recorded source SHA-256: " + data["identity"]["source_sha256"] + "\n"
         + "Different denominators, no shared scale or speedup comparison. "
         "This record does not measure the edited checkout.", size=23, fill=DIM)
    return _save(img, "latency.png")


def make_paper_flow() -> Path:
    """Separate PDF tooling and supplied assets from the ordinary Demo compiler."""
    img, draw, top = _canvas(
        "Paper inputs become an inspectable Demo",
        "Schematic workflow, not a measured paper-demo result. "
        "PDF extraction uses separately installed Poppler binaries.",
    )
    stages = [
        (
            "EXTRACT / SUPPLY", "PDF + local assets",
            "pdfinfo: metadata\npdftotext: text\npdftoppm: page images\n"
            "Supply figure images separately.\nOptional repository: AST summary.",
            "Text structure is heuristic.",
        ),
        (
            "AUTHOR", "build_paper_demo",
            "PaperSummary + selected assets\nTitle and abstract chunks\n"
            "Figure / page slides\nOptional code architecture",
            "Output: an ordinary Demo.",
        ),
        (
            "COMPILE / EXPORT", "Shared timed pipeline",
            "Measured clip durations\nEstimated word timestamps\n"
            "Scheduled visual states\nCaptions and timed image preview",
            "Silent core, not narrated evidence.",
        ),
    ]
    for index, (label, heading, body, foot) in enumerate(stages):
        x = 64 + index * 504
        card(draw, (x, top, x + 464, 736), label, heading, body,
             foot=foot, size=27)
        if index < 2:
            arrow(draw, (x + 472, 460), (x + 496, 460))
    text(draw, (64, 772, 1536, 866),
         "Voiced MP4 is optional: usable system / Kokoro speech + ffmpeg. "
         "Basic stream, energy and picture checks do not assess scientific "
         "content, intelligibility or acoustic word alignment.", size=28, fill=DIM)
    return _save(img, "paper_flow.png")


def make_provenance() -> Path:
    """Explain distinct, unsigned carriers without implying shared identity.

    A real illustrative MetadataConfig supplies overlapping labels, not one
    identical payload. The stable-content digest does not bind image pixels.
    """
    meta = MetadataConfig(
        author="Daniel Ari Friedman",
        source="democreate (repo)",
        url="https://github.com/docxology/democreate",
        watermark="democreate",
        title="DemoCreate",
        header=True,
    )
    img, draw, top = _canvas(
        "Three carriers, no authenticated identity",
        "Illustrative MetadataConfig + Demo: selected overlapping fields, "
        "different representations. No publication date is asserted.",
    )
    columns = [
        (
            "VISIBLE PIXELS", "Overlay bars",
            f"Title: {meta.title}\nAuthor: {meta.author}\n"
            f"Source: {meta.source}\nURL / clock / watermark\n"
            "export/overlay.py",
            "Readable in frames; labels can be copied.",
        ),
        (
            "CONTAINER FIELDS", "MP4 tags",
            f"title = {meta.title}\nartist = {meta.author}\n"
            "comment / description: tool credit + source + URL\n"
            "export/metadata.py",
            "ffmpeg tags; editable container metadata.",
        ),
        (
            "LOSSLESS PNG + JSON", "Unsigned association",
            "tool / version / author\nscene and chunk counts\n"
            "content_sha256: authored content\n"
            "poster_signed.png + provenance.json\nexport/stego.py",
            "LSB payload is not preserved by H.264.",
        ),
    ]
    for index, (label, heading, body, foot) in enumerate(columns):
        x = 64 + index * 504
        card(draw, (x, top, x + 464, 736), label, heading, body,
             foot=foot, size=27)
    text(draw, (64, 774, 1536, 874),
         "Trust boundary: an unsigned content hash checks consistency only. "
         "It authenticates neither author nor carrier image/video; copied "
         "payloads and pixel changes can still pass.", size=29, fill=FG)
    return _save(img, "provenance.png")


def make_video_stills() -> Path:
    """Compose digest-checked decoded frames from the recorded candidate MP4."""
    canonical = json.loads(MEDIA_EVIDENCE.read_text(encoding="utf-8"))["canonical"]
    frames = canonical["decoded_frames"]
    if len(frames) != 6:
        raise ValueError("the current montage requires six recorded decoded frames")
    img, draw, content_top = _canvas(
        "Decoded frames from the identified package MP4",
        f"Recorded {canonical['voice_backend']} / {canonical['voice']} | "
        f"{canonical['width']}x{canonical['height']} | "
        f"{canonical['animation_fps']} fps. "
        "Decoded synthetic visuals, not paper-demo evidence.",
    )
    width, height = CANVAS
    margin, gap = int(width * 0.04), int(width * 0.02)
    label_h = 38
    cols, rows = 3, 2
    cell_w = (width - 2 * margin - gap * (cols - 1)) // cols
    bottom = 740
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
            (x, y), f"Cue {frame['cue']} | seek {frame['seek_seconds']:.3f} s",
            font=scaled_font(height, 0.029), fill=ACCENT,
        )
        _fit_contain(img, still, (x, y + label_h, x + cell_w, y + label_h + cell_h))
    text(draw, (64, 768, 1536, 806),
         "Recorded MP4 SHA-256: " + canonical["video_sha256"], size=22, fill=DIM)
    text(draw, (64, 816, 1536, 882),
         "Source: data/visual-refresh-2026-11-08.json; six PNG digests checked. "
         "Seek labels are requested offsets, not decoded PTS or annotated onsets. "
         "No listening / alignment validation.", size=24, fill=DIM)
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
