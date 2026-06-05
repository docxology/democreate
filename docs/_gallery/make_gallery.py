#!/usr/bin/env python3
"""Render a handful of REAL DemoCreate frames for the docs gallery.

Every image in ``docs/gallery.md`` is produced here from the package's own
synthetic renderer (:func:`democreate.capture.screen.render_frame`) and the
architecture-diagram renderer — no screenshots, no hand-drawn mockups. The
output is deterministic for a given source tree, so the gallery can be checked in
and regenerated whenever the look changes.

Run it with the project virtualenv::

    .venv/bin/python docs/_gallery/make_gallery.py
"""

from __future__ import annotations

from pathlib import Path

from democreate.animation.diagram import DiagramNode, render_architecture_diagram
from democreate.capture.screen import render_frame
from democreate.config import THEMES
from democreate.media import FrameState
from democreate.schema import SceneKind

OUT = Path(__file__).resolve().parent
HD = (1920, 1080)
STRIP = (1920, 360)

# A small, realistic block of code to show being typed into the editor.
_CODE = [
    "from democreate import Pipeline, Demo",
    "",
    "def render(demo: Demo) -> None:",
    '    """Render a demo end-to-end."""',
    "    result = Pipeline(strict=False).run(demo)",
    "    print(result.summary())",
]


def typing_frame() -> None:
    """An editor frame mid-typing: code revealed up to ``cursor_typed`` with a cursor."""
    full = "\n".join(_CODE)
    state = FrameState(
        scene_kind=SceneKind.CODEBASE,
        title="render.py",
        file_path="src/democreate/render.py",
        caption="DemoCreate types code in character-by-character, highlighting as it goes.",
        code_lines=_CODE,
        highlight_lines=[5],
        cursor_typed=int(len(full) * 0.62),  # ~62% typed
        cursor_xy=(int(HD[0] * 0.46), int(HD[1] * 0.52)),
    )
    render_frame(state, HD, theme=THEMES["dark"]).save(OUT / "typing.png")


def paper_figure_frame() -> None:
    """A paper-figure background slide narrating a real figure caption (paper theme)."""
    # Render a stand-in "figure" image, then use it as a full-frame background so
    # the frame looks exactly like a paper-demo figure scene.
    fig = render_architecture_diagram(
        HD,
        title="Figure 3",
        columns=[
            ("Inputs", [DiagramNode(label="observations"), DiagramNode(label="priors")]),
            ("Model", [DiagramNode(label="generative model"), DiagramNode(label="free energy")]),
            ("Outputs", [DiagramNode(label="beliefs"), DiagramNode(label="actions")]),
        ],
        bg=THEMES["paper"].bg_slide,
        accent=THEMES["paper"].accent,
        fg=THEMES["paper"].text,
    )
    fig_path = OUT / "_figure_bg.png"
    fig.save(fig_path)
    state = FrameState(
        scene_kind=SceneKind.SLIDE,
        title="Figure 3",
        section="Figure 3",
        caption="Figure 3. The agent minimizes expected free energy over a planning horizon.",
        background_image=str(fig_path),
    )
    render_frame(state, HD, theme=THEMES["paper"]).save(OUT / "paper_figure.png")


def title_slide_frame() -> None:
    """A title slide with a headline + subtitle (midnight theme)."""
    state = FrameState(
        scene_kind=SceneKind.SLIDE,
        title="Policy Entanglement in Active Inference",
        subtitle="A 170-page paper · narrated demo",
        section="Paper",
        caption="A 170-page paper by the authors.",
    )
    render_frame(state, HD, theme=THEMES["midnight"]).save(OUT / "title_slide.png")


def architecture_frame() -> None:
    """The standalone architecture diagram (as a paper demo would embed it)."""
    columns = [
        ("narration", [DiagramNode(label="tts"), DiagramNode(label="sync"), DiagramNode(label="script")]),
        ("capture", [DiagramNode(label="screen"), DiagramNode(label="browser")]),
        ("assembly", [DiagramNode(label="animator"), DiagramNode(label="audio"), DiagramNode(label="captions")]),
        ("export", [DiagramNode(label="video"), DiagramNode(label="verify"), DiagramNode(label="chapters")]),
        ("paper", [DiagramNode(label="pdf"), DiagramNode(label="structure"), DiagramNode(label="script")]),
    ]
    render_architecture_diagram(
        HD, title="Codebase Architecture", columns=columns
    ).save(OUT / "architecture.png")


def themes_strip() -> None:
    """A horizontal strip of the same slide across all four preset themes."""
    from PIL import Image

    tile = (STRIP[0] // 4, STRIP[1])
    strip = Image.new("RGB", STRIP, (0, 0, 0))
    for i, name in enumerate(("dark", "light", "midnight", "paper")):
        state = FrameState(
            scene_kind=SceneKind.SLIDE,
            title=name.title(),
            subtitle="theme preset",
            section=name,
        )
        img = render_frame(state, tile, theme=THEMES[name])
        strip.paste(img, (i * tile[0], 0))
    strip.save(OUT / "themes_strip.png")


def main() -> None:
    """Render every gallery image into ``docs/_gallery/``."""
    OUT.mkdir(parents=True, exist_ok=True)
    typing_frame()
    paper_figure_frame()
    title_slide_frame()
    architecture_frame()
    themes_strip()
    pngs = sorted(p.name for p in OUT.glob("*.png") if not p.name.startswith("_"))
    print(f"wrote {len(pngs)} gallery image(s): {', '.join(pngs)}")


if __name__ == "__main__":
    main()
