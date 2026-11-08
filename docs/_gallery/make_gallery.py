#!/usr/bin/env python3
"""Generate synthetic renderer illustrations for the documentation gallery.

Every image in ``docs/gallery.md`` is produced here from the package's own
synthetic renderer (:func:`democreate.capture.screen.render_frame`) and the
architecture-diagram renderer — no screenshots, no hand-drawn mockups. The
output is deterministic for fixed source, assets, configuration and Pillow/FreeType
environment; regenerate whenever those inputs change.

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

# An illustrative, executable public-API example; not a current source excerpt.
_CODE = [
    "from democreate import Demo, Workspace, build_demo",
    "",
    "def build(demo: Demo) -> None:",
    '    """Build silent core outputs in a workspace."""',
    '    result = build_demo(demo, Workspace("output"))',
    "    print(result.player_path)",
]


def typing_frame() -> None:
    """An editor frame mid-typing: code revealed up to ``cursor_typed`` with a cursor."""
    state = FrameState(
        scene_kind=SceneKind.CODEBASE,
        title="illustrative_build.py",
        file_path="illustrative_build.py",
        caption="Synthetic character-count preview, not captured playback or current source.",
        code_lines=_CODE,
        highlight_lines=[5],
        cursor_typed=int(sum(map(len, _CODE)) * 0.62),
        cursor_xy=(int(HD[0] * 0.46), int(HD[1] * 0.52)),
    )
    render_frame(state, HD, theme=THEMES["dark"]).save(OUT / "typing.png")


def paper_figure_frame() -> None:
    """A synthetic diagram/caption illustration of the paper-theme layout."""
    # Compose an authored stand-in diagram; no external PDF is read.
    fig = render_architecture_diagram(
        HD,
        title="Synthetic illustration",
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
        title="Synthetic illustration",
        section="Illustration",
        caption="Synthetic illustration: authored diagram and caption, not PDF evidence.",
        background_image=str(fig_path),
    )
    render_frame(state, HD, theme=THEMES["paper"]).save(OUT / "paper_figure.png")


def title_slide_frame() -> None:
    """A synthetic midnight-theme title, with no external-paper claims."""
    state = FrameState(
        scene_kind=SceneKind.SLIDE,
        title="From paper notes to editable scenes",
        subtitle="Synthetic title layout; no external PDF",
        section="Illustration",
        caption="Authored title slide, not paper-extraction or narration evidence.",
    )
    render_frame(state, HD, theme=THEMES["midnight"]).save(OUT / "title_slide.png")


def architecture_frame() -> None:
    """Illustrate authored compilation stages, not inferred module dependencies."""
    columns = [
        ("Authored inputs", [
            DiagramNode(label="Demo"),
            DiagramNode(label="assets + configuration"),
        ]),
        ("Narration + timing", [
            DiagramNode(label="silent / optional speech"),
            DiagramNode(label="measured clip windows"),
            DiagramNode(label="estimated word times"),
        ]),
        ("Visual states", [
            DiagramNode(label="scheduled actions"),
            DiagramNode(label="FrameState"),
            DiagramNode(label="synthetic frames"),
        ]),
        ("Exports", [
            DiagramNode(label="PNG / SRT / VTT"),
            DiagramNode(label="timed image HTML"),
            DiagramNode(label="optional MP4"),
        ]),
    ]
    render_architecture_diagram(
        HD, title="Demo compilation: core and optional outputs", columns=columns
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
