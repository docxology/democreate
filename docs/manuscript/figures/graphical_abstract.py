"""Render a readable, evidence-bounded overview of Demo compilation.

This is a schematic, not an empirical result or a current-video receipt. It uses
Pillow's bundled font and no historical stills, host fonts or external assets.
Run with ``.venv/bin/python docs/manuscript/figures/graphical_abstract.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageStat

_THIS = Path(__file__).resolve()
_REPO = _THIS.parents[3]
_SRC = _REPO / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))
if str(_THIS.parent) not in sys.path:
    sys.path.insert(0, str(_THIS.parent))

from figure_layout import ACCENT, BG, DIM, FG, arrow, card, text  # noqa: E402

from democreate import __version__  # noqa: E402

__all__ = ["build", "main"]

W, H = 2400, 1350
OUT = _THIS.parent / "graphical_abstract.png"
_MARGIN = 70


def build() -> Image.Image:
    """Compose an authored spine, timed compilation and separate export lanes.

    Returns:
        A 2400 by 1350 RGB schematic; no measured performance is depicted.
    """
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)
    text(draw, (70, 58, W - 70, 158), f"DemoCreate {__version__}: a demo you compile",
         size=72)
    text(draw, (70, 164, W - 70, 232),
         "One authored Demo connects narration, timed actions and visual output.",
         size=40, fill=DIM)
    draw.line((70, 252, W - 70, 252), fill=ACCENT, width=4)

    width, gap = 720, 50
    stages = [
        (
            "DECLARATIVE SPINE", "1  Author the Demo",
            "Scenes > narration chunks > typed actions.\n"
            "Trigger words or explicit action times.\n"
            "Software sources or paper + local assets.",
            "Authoring inputs are not playback evidence.",
        ),
        (
            "DURATION-BASED TIMING", "2  Anchor to audio",
            "Measure WAV clip durations.\n"
            "Estimate word times by character length.\n"
            "Resolve trigger-word action times.",
            "Silent core; system / Kokoro speech optional.",
        ),
        (
            "SCHEDULED COMPILATION", "3  Build the visuals",
            "Actions update a FrameState.\n"
            "The timeline selects what appears at t.\n"
            "Apply theme, captions and animation.",
            "Fixed inputs + assets + config + environment.",
        ),
    ]
    for index, (label, heading, body, foot) in enumerate(stages):
        x = _MARGIN + index * (width + gap)
        card(draw, (x, 292, x + width, 854), label, heading, body,
             foot=foot, size=34)
        if index < 2:
            arrow(draw, (x + width + 8, 570), (x + width + gap - 8, 570))

    draw.rounded_rectangle((70, 894, 1370, 1104), radius=16, fill=BG,
                           outline=ACCENT, width=2)
    draw.rounded_rectangle((1410, 894, 2330, 1104), radius=16, fill=BG,
                           outline=ACCENT, width=2)
    text(draw, (102, 916, 1338, 958), "CORE OUTPUTS", size=28, fill=ACCENT)
    text(draw, (102, 968, 1338, 1022), "PNG + silent WAV + SRT / VTT", size=40)
    text(draw, (102, 1032, 1338, 1084),
         "HTML: timed image preview, not a speech player.", size=32)
    text(draw, (1442, 916, 2298, 958), "OPTIONAL MEDIA PATH", size=28, fill=ACCENT)
    text(draw, (1442, 968, 2298, 1022), "H.264 / AAC MP4", size=40)
    text(draw, (1442, 1032, 2298, 1098),
         "ffmpeg + usable speech for voiced output.", size=30)
    text(draw, (70, 1146, 2330, 1215),
         "Evidence boundary: clip windows are not acoustic word onsets; "
         "unsigned hashes do not authenticate.", size=34, fill=FG)
    text(draw, (70, 1234, 2330, 1320),
         "Blocking research gate: >=30 annotated voiced demos (>=10 per mode); "
         "both median errors <=120 ms. Not established.", size=32, fill=DIM)
    return image


def main() -> None:
    """Write the manuscript schematic and its repository-local output mirror."""
    image = build()
    if image.size != (W, H) or sum(ImageStat.Stat(image).var) <= 0:
        raise ValueError("graphical abstract has invalid geometry or blank content")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    image.save(OUT, "PNG")
    mirror = _REPO / "output" / "figures" / OUT.name
    mirror.parent.mkdir(parents=True, exist_ok=True)
    image.save(mirror, "PNG")
    print(f"wrote {OUT} ({W}x{H}); schematic, not an experimental result")


if __name__ == "__main__":
    main()
