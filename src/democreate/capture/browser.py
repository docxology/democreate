"""Browser driving for WEBSITE scenes — deterministic by default.

A :class:`BrowserDriver` is the small surface the demo pipeline uses to drive a
web page: navigate, selector/coordinate click, fill, scroll, and screenshot. The default
:class:`NullBrowserDriver` performs no real automation — it records every call
into a manifest and renders synthetic browser frames — so a website demo can be
built and tested with zero browser binaries. The real
:class:`PlaywrightBrowserDriver` lives behind the ``browser`` extra.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from ..errors import BackendUnavailableError
from ..media import FrameState
from ..schema import ActionType, Scene, SceneKind

__all__ = [
    "BrowserDriver",
    "NullBrowserDriver",
    "PlaywrightBrowserDriver",
    "drive_website_scene",
]


def _have(dep: str) -> bool:
    """Return ``True`` if an optional dependency is importable."""
    return importlib.util.find_spec(dep) is not None


def _scroll_delta(direction: str, amount: int) -> tuple[int, int]:
    """Resolve a nonnegative pixel amount into horizontal/vertical wheel deltas."""
    axes = {"up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0)}
    if direction not in axes:
        raise ValueError(f"unsupported scroll direction: {direction!r}")
    if amount < 0:
        raise ValueError("scroll amount must be nonnegative")
    x, y = axes[direction]
    return x * amount, y * amount


class BrowserDriver:
    """Abstract browser automation surface.

    Concrete drivers translate these primitive operations into either recorded
    manifest entries (the null driver) or real browser actions (Playwright).
    """

    def navigate(self, url: str) -> None:
        """Load ``url`` in the browser."""
        raise NotImplementedError

    def click(self, selector: str) -> None:
        """Click the first element matching ``selector``."""
        raise NotImplementedError

    def click_xy(self, x: int, y: int, *, button: str = "left") -> None:
        """Click viewport coordinates using the requested mouse button."""
        raise NotImplementedError

    def fill(self, selector: str, value: str) -> None:
        """Fill the field matching ``selector`` with ``value``."""
        raise NotImplementedError

    def scroll(self, direction: str, amount: int) -> None:
        """Scroll ``amount`` pixels up, down, left, or right."""
        raise NotImplementedError

    def screenshot(self, path: Path | str) -> Path:
        """Capture the current page to ``path``.

        Returns:
            The path written.
        """
        raise NotImplementedError

    def close(self) -> None:
        """Release any browser resources."""
        raise NotImplementedError


class NullBrowserDriver(BrowserDriver):
    """Deterministic, dependency-free browser driver.

    Every operation is appended to :attr:`manifest` as a plain dict. The current
    URL is tracked so :meth:`screenshot` can render a faithful synthetic browser
    frame via the synthetic renderer — no browser binary required.

    Attributes:
        manifest: Ordered record of every driver operation.
        current_url: The most recently navigated URL.
    """

    def __init__(self, *, size: tuple[int, int] = (1280, 720)) -> None:
        """Initialize an empty manifest.

        Args:
            size: Pixel ``(width, height)`` used when rendering screenshots.
        """
        self.manifest: list[dict[str, Any]] = []
        self.current_url: str = ""
        self._size = size

    def navigate(self, url: str) -> None:
        """Record a navigation and update the tracked URL.

        Args:
            url: The URL to "load".
        """
        self.current_url = url
        self.manifest.append({"op": "navigate", "url": url})

    def click(self, selector: str) -> None:
        """Record a click on ``selector``.

        Args:
            selector: The CSS/text selector clicked.
        """
        self.manifest.append({"op": "click", "selector": selector})

    def click_xy(self, x: int, y: int, *, button: str = "left") -> None:
        """Record a coordinate click without inventing an element selector."""
        self.manifest.append({"op": "click", "xy": [x, y], "button": button})

    def fill(self, selector: str, value: str) -> None:
        """Record filling ``selector`` with the canonical ``value``."""
        self.manifest.append({"op": "fill", "selector": selector, "value": value})

    def scroll(self, direction: str, amount: int) -> None:
        """Record a directional scroll after validating its pixel delta."""
        _scroll_delta(direction, amount)
        self.manifest.append(
            {"op": "scroll", "direction": direction, "amount": amount}
        )

    def screenshot(self, path: Path | str) -> Path:
        """Render a synthetic browser frame to ``path``.

        Args:
            path: Destination image path.

        Returns:
            The path written, as a :class:`~pathlib.Path`.
        """
        from .screen import SyntheticRenderer

        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        state = FrameState(
            scene_kind=SceneKind.WEBSITE,
            title=self.current_url,
            url=self.current_url,
        )
        SyntheticRenderer().render(state, self._size).save(out)
        self.manifest.append({"op": "screenshot", "path": str(out)})
        return out

    def close(self) -> None:
        """Record that the driver was closed (idempotent)."""
        self.manifest.append({"op": "close"})


class PlaywrightBrowserDriver(BrowserDriver):
    """Real browser automation via Playwright (extra: ``browser``).

    Requires the ``playwright`` package and an installed browser binary. Provided
    only behind the ``browser`` extra; the default pipeline never needs it.
    """

    def __init__(self, *, headless: bool = True) -> None:
        """Launch a Playwright browser, verifying the backend is installed.

        Args:
            headless: Whether to run without a visible window.

        Raises:
            BackendUnavailableError: If Playwright or its browser binary is absent.
        """
        if not _have("playwright"):
            raise BackendUnavailableError("playwright", extra="browser")
        self._launch(headless)  # pragma: no cover - requires browser binary

    def _launch(self, headless: bool) -> None:  # pragma: no cover - requires browser binary
        from playwright.sync_api import Error, sync_playwright

        self._pw = sync_playwright().start()
        browser = None
        try:
            browser = self._pw.chromium.launch(headless=headless)
            self._page = browser.new_page()
        except Exception as exc:
            try:
                if browser is not None:
                    browser.close()
            finally:
                self._pw.stop()
            message = str(exc).lower()
            if isinstance(exc, Error) and (
                "executable doesn't exist" in message or "playwright install" in message
            ):
                raise BackendUnavailableError(
                    "playwright Chromium (run `playwright install chromium`)",
                    extra="browser",
                ) from exc
            raise
        self._browser = browser

    def navigate(self, url: str) -> None:  # pragma: no cover - requires browser binary
        """Load ``url`` in the real page."""
        self._page.goto(url)

    def click(self, selector: str) -> None:  # pragma: no cover - requires browser binary
        """Click the element matching ``selector``."""
        self._page.click(selector)

    def click_xy(  # pragma: no cover - requires browser binary
        self, x: int, y: int, *, button: str = "left"
    ) -> None:
        """Click actual viewport coordinates with the requested mouse button."""
        self._page.mouse.click(x, y, button=button)

    def fill(self, selector: str, value: str) -> None:  # pragma: no cover - requires browser binary
        """Fill the field matching ``selector`` with ``value``."""
        self._page.fill(selector, value)

    def scroll(self, direction: str, amount: int) -> None:  # pragma: no cover - requires browser binary
        """Apply directional pixel scrolling to the real page."""
        x, y = _scroll_delta(direction, amount)
        self._page.mouse.wheel(x, y)

    def screenshot(self, path: Path | str) -> Path:  # pragma: no cover - requires browser binary
        """Capture the real page to ``path`` and return it."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(out))
        return out

    def close(self) -> None:  # pragma: no cover - requires browser binary
        """Close the page, browser, and Playwright context."""
        try:
            self._browser.close()
        finally:
            self._pw.stop()


def drive_website_scene(
    scene: Scene, driver: BrowserDriver | None = None
) -> list[dict[str, Any]]:
    """Translate a WEBSITE scene's actions into driver calls.

    Walks every action in the scene's chunks and dispatches the browser-relevant
    ones (``NAVIGATE``, ``CLICK``, ``SCROLL``, ``FILL``) to the driver. A base URL
    in ``scene.context["url"]`` seeds an initial navigation. With the default
    :class:`NullBrowserDriver` this is fully deterministic and the returned value
    is the driver's manifest.

    Args:
        scene: The scene whose actions to replay. Need not be a WEBSITE scene, but
            only browser-relevant actions are dispatched.
        driver: The driver to use; defaults to a fresh :class:`NullBrowserDriver`.

    Returns:
        The ordered manifest of operations performed.
    """
    drv = driver if driver is not None else NullBrowserDriver()

    base_url = scene.context.get("url")
    if base_url:
        drv.navigate(str(base_url))

    for chunk in scene.chunks:
        for action in chunk.actions:
            params = action.params
            if action.type == ActionType.NAVIGATE:
                drv.navigate(str(params.get("url", "")))
            elif action.type == ActionType.CLICK:
                if "xy" in params:
                    x, y = params["xy"]
                    drv.click_xy(x, y, button=str(params.get("button", "left")))
                else:
                    drv.click(str(params["selector"]))
            elif action.type == ActionType.FILL:
                drv.fill(str(params["selector"]), str(params["value"]))
            elif action.type == ActionType.SCROLL:
                drv.scroll(str(params["direction"]), int(params.get("amount", 100)))

    return getattr(drv, "manifest", [])
