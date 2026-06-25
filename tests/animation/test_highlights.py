"""Tests for democreate.animation.highlights (pure, core-deps-only)."""

from __future__ import annotations

import pytest

from democreate.animation import highlights


def test_highlight_to_svg_contains_svg_tag(sample_python_source: str) -> None:
    svg = highlights.highlight_to_svg(sample_python_source, language="python")
    assert "<svg" in svg
    assert isinstance(svg, str)
    assert len(svg) > 100


def test_highlight_to_svg_deterministic(sample_python_source: str) -> None:
    a = highlights.highlight_to_svg(sample_python_source)
    b = highlights.highlight_to_svg(sample_python_source)
    assert a == b


def test_highlight_to_svg_no_line_numbers(sample_python_source: str) -> None:
    svg = highlights.highlight_to_svg(sample_python_source, line_numbers=False)
    assert "<svg" in svg


def test_highlight_to_svg_theme_changes_output(sample_python_source: str) -> None:
    monokai = highlights.highlight_to_svg(sample_python_source, theme="monokai")
    dracula = highlights.highlight_to_svg(sample_python_source, theme="dracula")
    assert monokai != dracula


def test_highlight_to_text_non_empty(sample_python_source: str) -> None:
    text = highlights.highlight_to_text(sample_python_source)
    assert text.strip()
    assert "greet" in text


def test_highlight_to_text_empty_code() -> None:
    text = highlights.highlight_to_text("")
    assert isinstance(text, str)


def test_render_code_image_size(sample_python_source: str) -> None:
    img = highlights.render_code_image(sample_python_source, size=(640, 480))
    assert img.size == (640, 480)
    assert img.mode == "RGB"


def test_render_code_image_default_size(sample_python_source: str) -> None:
    img = highlights.render_code_image(sample_python_source)
    assert img.size == (1280, 720)


def test_render_code_image_highlight_band_changes_pixels() -> None:
    code = "line one\nline two\nline three\n"
    plain = highlights.render_code_image(code, size=(400, 200))
    banded = highlights.render_code_image(
        code, size=(400, 200), highlight_lines=(2,)
    )
    assert plain.tobytes() != banded.tobytes()


def test_render_code_image_highlight_band_color_present() -> None:
    code = "a\nb\nc\n"
    img = highlights.render_code_image(code, size=(400, 200), highlight_lines=(2,))
    # The highlight band color must appear somewhere in the image.
    band_colors = {c for _, c in (img.getcolors(maxcolors=1 << 20) or [])}
    assert highlights._HIGHLIGHT_BAND in band_colors


def test_render_code_image_empty_code() -> None:
    img = highlights.render_code_image("", size=(200, 100))
    assert img.size == (200, 100)


def test_render_code_image_clips_overflow() -> None:
    # Many lines into a short frame must not raise and must keep size.
    code = "\n".join(f"line {i}" for i in range(200))
    img = highlights.render_code_image(code, size=(300, 120))
    assert img.size == (300, 120)


def test_render_code_image_deterministic() -> None:
    code = "x = 1\ny = 2\n"
    a = highlights.render_code_image(code, size=(200, 100), highlight_lines=(1,))
    b = highlights.render_code_image(code, size=(200, 100), highlight_lines=(1,))
    assert a.tobytes() == b.tobytes()


@pytest.mark.parametrize("lang", ["python", "javascript", "json"])
def test_highlight_to_svg_languages(lang: str) -> None:
    svg = highlights.highlight_to_svg("a = 1", language=lang)
    assert "<svg" in svg
