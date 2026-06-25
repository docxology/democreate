"""Tests for browser driving (capture.browser)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from democreate.capture.browser import (
    BrowserDriver,
    NullBrowserDriver,
    PlaywrightBrowserDriver,
    drive_website_scene,
)
from democreate.errors import BackendUnavailableError
from democreate.schema import Action, ActionType, Chunk, Scene, SceneKind


def _is_png(path: Path) -> bool:
    return path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_null_driver_records_calls() -> None:
    drv = NullBrowserDriver()
    drv.navigate("https://a.com")
    drv.click("#btn")
    drv.fill("#q", "hello")
    drv.scroll(100)
    drv.close()
    ops = [m["op"] for m in drv.manifest]
    assert ops == ["navigate", "click", "fill", "scroll", "close"]
    assert drv.current_url == "https://a.com"
    assert drv.manifest[2] == {"op": "fill", "selector": "#q", "text": "hello"}


def test_null_driver_screenshot_writes_png(tmp_path: Path) -> None:
    drv = NullBrowserDriver(size=(320, 200))
    drv.navigate("https://example.com")
    out = drv.screenshot(tmp_path / "shots" / "page.png")
    assert out.exists()
    assert _is_png(out)
    assert {"op": "screenshot", "path": str(out)} in drv.manifest


def test_drive_website_scene_default_driver() -> None:
    scene = Scene(
        id="w",
        title="Site",
        kind=SceneKind.WEBSITE,
        context={"url": "https://example.com"},
        chunks=[
            Chunk(
                id="c1",
                text="navigate and click",
                actions=[
                    Action(ActionType.NAVIGATE, {"url": "https://example.com/docs"}),
                    Action(ActionType.CLICK, {"selector": "a.next"}),
                    Action(ActionType.FILL, {"selector": "#search", "text": "demo"}),
                    Action(ActionType.SCROLL, {"amount": 200}),
                ],
            )
        ],
    )
    manifest = drive_website_scene(scene)
    ops = [m["op"] for m in manifest]
    # base url navigation first, then the four actions
    assert ops == ["navigate", "navigate", "click", "fill", "scroll"]
    assert manifest[0]["url"] == "https://example.com"
    assert manifest[1]["url"] == "https://example.com/docs"


def test_drive_website_scene_no_base_url() -> None:
    scene = Scene(
        id="w",
        kind=SceneKind.WEBSITE,
        chunks=[Chunk(id="c", actions=[Action(ActionType.CLICK, {"selector": "x"})])],
    )
    manifest = drive_website_scene(scene)
    assert [m["op"] for m in manifest] == ["click"]


def test_drive_website_scene_ignores_non_browser_actions() -> None:
    scene = Scene(
        id="w",
        kind=SceneKind.WEBSITE,
        chunks=[
            Chunk(
                id="c",
                actions=[
                    Action(ActionType.OPEN_FILE, {"path": "x.py"}),
                    Action(ActionType.NAVIGATE, {"url": "https://y.com"}),
                ],
            )
        ],
    )
    manifest = drive_website_scene(scene)
    assert [m["op"] for m in manifest] == ["navigate"]


def test_drive_website_scene_scroll_by_alias() -> None:
    scene = Scene(
        id="w",
        kind=SceneKind.WEBSITE,
        chunks=[Chunk(id="c", actions=[Action(ActionType.SCROLL, {"by": 50})])],
    )
    manifest = drive_website_scene(scene)
    assert manifest[0] == {"op": "scroll", "amount": 50}


def test_drive_website_scene_explicit_driver_returns_same_manifest() -> None:
    drv = NullBrowserDriver()
    scene = Scene(id="w", kind=SceneKind.WEBSITE, context={"url": "https://z.com"})
    manifest = drive_website_scene(scene, driver=drv)
    assert manifest is drv.manifest


def test_base_browser_driver_is_abstract() -> None:
    drv = BrowserDriver()
    for call in (
        lambda: drv.navigate("x"),
        lambda: drv.click("x"),
        lambda: drv.fill("x", "y"),
        lambda: drv.screenshot("p"),
        drv.close,
    ):
        with pytest.raises(NotImplementedError):
            call()


def test_playwright_unavailable_when_dep_missing() -> None:
    if importlib.util.find_spec("playwright") is not None:  # pragma: no cover
        pytest.skip("playwright installed; unavailability path not applicable")
    with pytest.raises(BackendUnavailableError) as exc:
        PlaywrightBrowserDriver()
    assert exc.value.backend == "playwright"
    assert exc.value.extra == "browser"
