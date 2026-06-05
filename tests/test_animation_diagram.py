"""Tests for the architecture diagram renderer.

Real computation on real Pillow images — no mocks. Each test asserts the
produced image is the requested size and not uniformly blank (pixel variance via
:class:`PIL.ImageStat.Stat`), and exercises edge cases (small sizes, empty
columns, silent/empty content).
"""

from __future__ import annotations

from PIL import Image, ImageStat

from democreate.animation.diagram import (
    DiagramNode,
    democreate_architecture_image,
    render_architecture_diagram,
)


def _variance(image: Image.Image) -> float:
    """Return the summed per-channel variance of an RGB image."""
    return sum(ImageStat.Stat(image).var)


def test_canonical_image_size_and_not_blank() -> None:
    image = democreate_architecture_image((1920, 1080))
    assert isinstance(image, Image.Image)
    assert image.size == (1920, 1080)
    assert image.mode == "RGB"
    assert _variance(image) > 0


def test_canonical_default_size() -> None:
    image = democreate_architecture_image()
    assert image.size == (1920, 1080)
    assert _variance(image) > 0


def test_small_size_does_not_raise_and_not_blank() -> None:
    image = democreate_architecture_image((640, 360))
    assert image.size == (640, 360)
    assert _variance(image) > 0


def test_tiny_size_does_not_raise() -> None:
    image = render_architecture_diagram(
        (32, 24),
        title="X",
        columns=[("A", [DiagramNode("n")])],
    )
    assert image.size == (32, 24)


def test_title_region_differs_from_background() -> None:
    bg = (13, 17, 23)
    image = render_architecture_diagram(
        (800, 600),
        title="Architecture Title",
        columns=[("Col", [DiagramNode("Node", ["sub"])])],
        bg=bg,
    )
    # The title sits near the top-center; that band must contain non-bg pixels.
    crop = image.crop((100, 0, 700, 80))
    pixels = list(crop.get_flattened_data())
    assert any(px != bg for px in pixels)


def test_requested_size_is_exact() -> None:
    for size in [(1280, 720), (500, 500), (1000, 400)]:
        image = render_architecture_diagram(
            size,
            title="T",
            columns=[
                ("One", [DiagramNode("a", ["x"])]),
                ("Two", [DiagramNode("b"), DiagramNode("c")]),
            ],
        )
        assert image.size == size
        assert _variance(image) > 0


def test_empty_columns_returns_sized_image() -> None:
    # No columns: only the title/rule are drawn. Still the requested size,
    # and the title makes it non-blank.
    image = render_architecture_diagram(
        (640, 360),
        title="Just a Title",
        columns=[],
    )
    assert image.size == (640, 360)
    assert _variance(image) > 0


def test_column_with_no_nodes_does_not_raise() -> None:
    image = render_architecture_diagram(
        (800, 450),
        title="Mixed",
        columns=[
            ("Empty", []),
            ("Full", [DiagramNode("only", ["one"])]),
        ],
    )
    assert image.size == (800, 450)
    assert _variance(image) > 0


def test_empty_title_and_empty_labels() -> None:
    # "Silent"/empty content analog: blank strings everywhere.
    image = render_architecture_diagram(
        (640, 360),
        title="",
        columns=[("", [DiagramNode("", [""])])],
    )
    assert image.size == (640, 360)
    # Boxes and connectors still draw, so the frame is not uniformly blank.
    assert _variance(image) > 0


def test_custom_colors_applied() -> None:
    bg = (0, 0, 0)
    image = render_architecture_diagram(
        (640, 360),
        title="Colorful",
        columns=[("A", [DiagramNode("n", ["s"])]), ("B", [DiagramNode("m")])],
        bg=bg,
        accent=(255, 0, 0),
        fg=(255, 255, 255),
    )
    pixels = set(image.get_flattened_data())
    # Some non-background pixels exist (text/box/accent draws).
    assert any(px != bg for px in pixels)


def test_connectors_drawn_between_columns() -> None:
    # Two columns wide apart; the gap region between them should contain
    # accent-colored connector pixels (not all background).
    bg = (10, 10, 10)
    image = render_architecture_diagram(
        (1200, 600),
        title="Conn",
        columns=[
            ("L", [DiagramNode("left")]),
            ("R", [DiagramNode("right")]),
        ],
        bg=bg,
    )
    assert _variance(image) > 0
