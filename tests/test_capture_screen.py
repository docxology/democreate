"""Tests for the synthetic frame renderer (capture.screen)."""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.capture.screen import (
    FrameSource,
    MssScreenCapture,
    SyntheticRenderer,
    render_demo_thumbnail,
    render_frame,
)
from democreate.errors import BackendUnavailableError
from democreate.media import FrameState
from democreate.schema import Demo, Scene, SceneKind


def _is_png(path: Path) -> bool:
    """Return True if ``path`` begins with the PNG magic signature."""
    return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def _editor_state() -> FrameState:
    return FrameState(
        scene_kind=SceneKind.CODEBASE,
        title="main.py",
        file_path="src/main.py",
        caption="Opening the entry point",
        code_lines=["import os", "", "def main():", "    return 0"],
        highlight_lines=[3],
        cursor_typed=5,
    )


def _terminal_state() -> FrameState:
    return FrameState(
        scene_kind=SceneKind.TERMINAL,
        title="zsh",
        caption="Running the build",
        terminal_lines=["$ democreate build", "built 3 scenes"],
    )


def _browser_state() -> FrameState:
    return FrameState(
        scene_kind=SceneKind.WEBSITE,
        title="Example",
        caption="The landing page",
        url="https://example.com",
    )


def _slide_state() -> FrameState:
    return FrameState(scene_kind=SceneKind.SLIDE, title="Welcome", caption="Intro slide")


@pytest.mark.parametrize(
    "state",
    [_editor_state(), _terminal_state(), _browser_state(), _slide_state()],
    ids=["editor", "terminal", "browser", "slide"],
)
def test_render_each_scene_kind_writes_valid_png(state: FrameState, tmp_path: Path) -> None:
    size = (640, 360)
    img = render_frame(state, size)
    assert img.size == size
    assert img.mode == "RGB"
    out = tmp_path / f"{state.scene_kind.value}.png"
    img.save(out)
    assert out.stat().st_size > 0
    assert _is_png(out)


def test_render_default_size_is_full_hd() -> None:
    img = render_frame(_slide_state())
    assert img.size == (1920, 1080)


def test_synthetic_renderer_is_deterministic() -> None:
    state = _editor_state()
    a = SyntheticRenderer().render(state, (320, 200))
    b = SyntheticRenderer().render(state, (320, 200))
    assert a.tobytes() == b.tobytes()


def test_caption_changes_pixels() -> None:
    with_caption = FrameState(scene_kind=SceneKind.SLIDE, title="X", caption="hello world")
    without = FrameState(scene_kind=SceneKind.SLIDE, title="X", caption="")
    a = render_frame(with_caption, (400, 300))
    b = render_frame(without, (400, 300))
    assert a.tobytes() != b.tobytes()


def test_long_caption_is_truncated_not_crashing() -> None:
    state = FrameState(scene_kind=SceneKind.SLIDE, title="X", caption="word " * 80)
    img = render_frame(state, (500, 300))
    assert img.size == (500, 300)


def test_editor_cursor_at_zero_typed() -> None:
    state = FrameState(
        scene_kind=SceneKind.CODEBASE,
        code_lines=["abc", "def"],
        cursor_typed=0,
    )
    img = render_frame(state, (300, 200))
    assert img.size == (300, 200)


def test_empty_state_renders() -> None:
    img = render_frame(FrameState(), (200, 120))
    assert img.size == (200, 120)


def test_tiny_size_is_clamped() -> None:
    img = render_frame(_slide_state(), (0, 0))
    assert img.size == (1, 1)


def test_render_demo_thumbnail(sample_demo: Demo, tmp_path: Path) -> None:
    img = render_demo_thumbnail(sample_demo)
    assert img.size == (1280, 720)
    out = tmp_path / "thumb.png"
    img.save(out)
    assert _is_png(out)


def test_render_demo_thumbnail_custom_size(sample_demo: Demo) -> None:
    img = render_demo_thumbnail(sample_demo, size=(320, 180))
    assert img.size == (320, 180)


def test_render_demo_thumbnail_empty_demo() -> None:
    img = render_demo_thumbnail(Demo(title="Empty"), size=(200, 120))
    assert img.size == (200, 120)


def test_render_demo_thumbnail_website_scene() -> None:
    scene = Scene(id="w", title="Site", kind=SceneKind.WEBSITE, context={"url": "https://x.io"})
    demo = Demo(title="Web", scenes=[scene])
    img = render_demo_thumbnail(demo, size=(300, 200))
    assert img.size == (300, 200)


def test_frame_source_base_is_abstract() -> None:
    with pytest.raises(NotImplementedError):
        FrameSource().render(FrameState(), (10, 10))


def test_mss_backend_unavailable_when_dep_missing() -> None:
    import importlib.util

    if importlib.util.find_spec("mss") is not None:  # pragma: no cover - dep installed
        pytest.skip("mss installed; unavailability path not applicable")
    with pytest.raises(BackendUnavailableError) as exc:
        MssScreenCapture()
    assert exc.value.backend == "mss"
    assert exc.value.extra == "capture"
