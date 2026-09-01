"""Frame rendering — the synthetic virtual renderer at the heart of capture.

The default :class:`SyntheticRenderer` (implemented in
:mod:`democreate.capture._screen_renderer`) *draws* a clean, deterministic
representation of the editor, terminal, browser, or slide implied by the frame
state; a frame may use a full-frame ``background_image`` and the renderer
reserves a bottom band for the animated speech waveform
(:func:`waveform_band_box`).

The real :class:`MssScreenCapture` is provided behind the ``capture`` extra; it is
never required. This module remains the stable import surface for the subsystem.
"""

from __future__ import annotations

import importlib.util
from typing import TYPE_CHECKING

from ..config import Theme
from ..errors import BackendUnavailableError
from ..media import FrameState
from ..schema import Demo, SceneKind
from ._screen_renderer import (  # noqa: F401 (re-exports)
    WAVEFORM_BAND_FRAC,
    FrameSource,
    SyntheticRenderer,
    waveform_band_box,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from PIL import Image as _ImageModule

__all__ = [
    "FrameSource",
    "SyntheticRenderer",
    "MssScreenCapture",
    "render_frame",
    "render_demo_thumbnail",
    "waveform_band_box",
    "WAVEFORM_BAND_FRAC",
]

def _have(dep: str) -> bool:
    """Return ``True`` if an optional dependency is importable."""
    return importlib.util.find_spec(dep) is not None


class MssScreenCapture(FrameSource):
    """Real screen-pixel capture via the ``mss`` library (extra: ``capture``)."""

    def __init__(self, monitor: int = 1) -> None:
        """Store the monitor index and verify the backend is installed.

        Args:
            monitor: 1-based monitor index understood by ``mss``.

        Raises:
            BackendUnavailableError: If ``mss`` is not installed.
        """
        if not _have("mss"):
            raise BackendUnavailableError("mss", extra="capture")
        self.monitor = monitor

    def render(self, state: FrameState, size: tuple[int, int]) -> _ImageModule.Image:  # pragma: no cover - requires real display
        """Capture the current screen and resize it to ``size``."""
        import mss
        from PIL import Image

        with mss.mss() as sct:
            grab = sct.grab(sct.monitors[self.monitor])
            img = Image.frombytes("RGB", grab.size, grab.bgra, "raw", "BGRX")
        return img.resize(size)


def render_frame(
    state: FrameState,
    size: tuple[int, int] = (1920, 1080),
    *,
    theme: Theme | None = None,
) -> _ImageModule.Image:
    """Render a single frame with the default synthetic renderer.

    Args:
        state: The frame state to render.
        size: Output ``(width, height)`` in pixels.
        theme: Optional theme; defaults to the built-in dark theme.

    Returns:
        A rendered :class:`PIL.Image.Image`.
    """
    return SyntheticRenderer(theme).render(state, size)


def render_demo_thumbnail(
    demo: Demo, size: tuple[int, int] = (1280, 720), *, theme: Theme | None = None
) -> _ImageModule.Image:
    """Render a thumbnail from the opening frame of a demo's first scene.

    Args:
        demo: The demo to summarize visually.
        size: Output ``(width, height)`` in pixels.
        theme: Optional theme.

    Returns:
        A rendered :class:`PIL.Image.Image`.
    """
    if not demo.scenes:
        state = FrameState(scene_kind=SceneKind.SLIDE, title=demo.title)
        return render_frame(state, size, theme=theme)
    scene = demo.scenes[0]
    caption = scene.chunks[0].text if scene.chunks else ""
    state = FrameState(
        scene_kind=scene.kind,
        title=scene.title,
        caption=caption,
        file_path=str(scene.context.get("repo", "")),
        terminal_lines=[scene.title] if scene.kind == SceneKind.TERMINAL else [],
        url=str(scene.context.get("url", "")),
    )
    return render_frame(state, size, theme=theme)
