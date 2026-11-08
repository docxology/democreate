"""Render the candidate capability schematic with the shared Pillow renderer.

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

from democreate import __version__  # noqa: E402
from democreate.animation.diagram import (  # noqa: E402
    DiagramNode,
    render_architecture_diagram,
)
from democreate.animation.fonts import load_font  # noqa: E402
from democreate.config import THEMES  # noqa: E402

__all__ = ["build", "main"]

W, H = 2400, 1350
OUT = _THIS.parent / "graphical_abstract.png"
_BG = (10, 10, 12)
_FG = (242, 242, 244)
_DIM = (170, 170, 176)


def build() -> Image.Image:
    """Compose the schematic without implying acoustic or authenticity results.

    Returns:
        A 2400 by 1350 RGB image using the package's shared diagram layout.
    """
    columns = [
        ("Inputs", [
            DiagramNode("Python repository", ["README + AST", "No inspected-code execution"]),
            DiagramNode("Paper + assets", ["Poppler text / metadata", "Heuristic structure", "Local figure images"]),
        ]),
        ("Authored artifact", [
            DiagramNode("Demo", ["Scenes / chunks / actions", "Narration + trigger words", "Assets + configuration"]),
        ]),
        ("Compile", [
            DiagramNode("Narration", ["Silent core default", "System / Kokoro optional"]),
            DiagramNode("Timing", ["Measured clip windows", "Character-weighted words"]),
            DiagramNode("Composition", ["Scheduled action frames", "Theme / camera / waveform"]),
        ]),
        ("Outputs", [
            DiagramNode("Core exports", ["PNG + WAV", "SRT / VTT / HTML preview"]),
            DiagramNode("Optional MP4", ["ffmpeg + usable speech", "H.264 / AAC"]),
            DiagramNode("Basic verification", ["Streams / energy / picture", "Not acoustic accuracy"]),
        ]),
    ]
    diagram = render_architecture_diagram(
        (W, H - 200),
        title=f"DemoCreate {__version__} candidate",
        columns=columns,
        bg=_BG,
        accent=THEMES["noir"].accent,
        fg=_FG,
    )
    image = Image.new("RGB", (W, H), _BG)
    image.paste(diagram, (0, 0))
    draw = ImageDraw.Draw(image)
    draw.line([(70, H - 180), (W - 70, H - 180)], fill=THEMES["noir"].accent, width=3)
    notes = [
        "Byte comparisons require fixed inputs, assets, configuration and runtime.",
        "Clip-duration timing is not acoustic word detection. Unsigned hashes do not authenticate.",
        "Research gate pending: independently annotated >=30-demo voiced corpus and <=120 ms result.",
    ]
    font = load_font(30)
    for index, note in enumerate(notes):
        draw.text((70, H - 150 + index * 48), note, font=font, fill=_DIM)
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
