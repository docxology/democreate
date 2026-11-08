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
    drv.scroll("down", 100)
    drv.close()
    ops = [m["op"] for m in drv.manifest]
    assert ops == ["navigate", "click", "fill", "scroll", "close"]
    assert drv.current_url == "https://a.com"
    assert drv.manifest[2] == {"op": "fill", "selector": "#q", "value": "hello"}


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
                    Action(ActionType.FILL, {"selector": "#search", "value": "demo"}),
                    Action(ActionType.SCROLL, {"direction": "down", "amount": 200}),
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
    assert manifest[3] == {"op": "fill", "selector": "#search", "value": "demo"}
    assert manifest[4] == {"op": "scroll", "direction": "down", "amount": 200}


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


@pytest.mark.parametrize("direction", ["up", "down", "left", "right"])
def test_drive_website_scene_directional_scroll(direction: str) -> None:
    from democreate.schema import Demo

    scene = Scene(
        id="w",
        kind=SceneKind.WEBSITE,
        chunks=[
            Chunk(
                id="c",
                actions=[
                    Action(ActionType.SCROLL, {"direction": direction, "amount": 50})
                ],
            )
        ],
    )
    assert Demo(title="Scroll", scenes=[scene]).validate() == []
    manifest = drive_website_scene(scene)
    assert manifest[0] == {"op": "scroll", "direction": direction, "amount": 50}


def test_scroll_default_amount_is_not_discarded() -> None:
    scene = Scene(
        id="w",
        kind=SceneKind.WEBSITE,
        chunks=[
            Chunk(id="c", actions=[Action(ActionType.SCROLL, {"direction": "down"})])
        ],
    )
    assert drive_website_scene(scene) == [
        {"op": "scroll", "direction": "down", "amount": 100}
    ]


@pytest.mark.parametrize(
    ("direction", "amount"), [("diagonal", 100), ("up", -10)]
)
def test_invalid_scroll_is_explicit(direction: str, amount: int) -> None:
    with pytest.raises(ValueError):
        NullBrowserDriver().scroll(direction, amount)


@pytest.mark.parametrize(
    ("direction", "delta"),
    [
        ("up", (0, -50)),
        ("down", (0, 50)),
        ("left", (-50, 0)),
        ("right", (50, 0)),
    ],
)
def test_scroll_deltas_used_by_real_driver(
    direction: str, delta: tuple[int, int]
) -> None:
    from democreate.capture.browser import _scroll_delta

    assert _scroll_delta(direction, 50) == delta


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
        lambda: drv.click_xy(10, 20, button="right"),
        lambda: drv.fill("x", "y"),
        lambda: drv.scroll("up", 100),
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


def test_playwright_missing_binary_is_typed_and_unwinds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if importlib.util.find_spec("playwright") is None:
        pytest.skip("playwright package not installed")
    monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(tmp_path / "absent-browsers"))
    # A leaked sync context makes the second start fail with an event-loop error.
    for _ in range(2):
        with pytest.raises(BackendUnavailableError, match="playwright install chromium"):
            PlaywrightBrowserDriver()


def test_real_browser_consumes_fill_click_and_directional_scroll(tmp_path: Path) -> None:
    if importlib.util.find_spec("playwright") is None:
        pytest.skip("playwright package not installed")
    try:
        driver = PlaywrightBrowserDriver()
    except BackendUnavailableError as exc:
        pytest.skip(str(exc))
    page = tmp_path / "page.html"
    page.write_text(
        "<!doctype html><style>body{margin:0;width:4000px;height:4000px}"
        "#target{position:absolute;left:10px;top:10px;width:100px;height:50px}"
        "#field{position:absolute;left:10px;top:80px}</style>"
        '<button id="target">Click</button><input id="field">'
        "<script>document.querySelector('#target').addEventListener('contextmenu',"
        "e=>{e.preventDefault();document.body.dataset.button=e.button});</script>",
        encoding="utf-8",
    )
    try:
        scene = Scene(
            id="real",
            kind=SceneKind.WEBSITE,
            context={"url": page.as_uri()},
            chunks=[
                Chunk(
                    id="c",
                    actions=[
                        Action(ActionType.FILL, {"selector": "#field", "value": "kept"}),
                        Action(ActionType.CLICK, {"xy": [30, 30], "button": "right"}),
                        Action(ActionType.SCROLL, {"direction": "down", "amount": 200}),
                        Action(ActionType.SCROLL, {"direction": "right", "amount": 200}),
                    ],
                )
            ],
        )
        drive_website_scene(scene, driver)
        driver._page.wait_for_function("scrollX === 200 && scrollY === 200")
        assert driver._page.locator("#field").input_value() == "kept"
        assert driver._page.locator("body").get_attribute("data-button") == "2"
        drive_website_scene(
            Scene(
                id="back",
                kind=SceneKind.WEBSITE,
                chunks=[
                    Chunk(
                        id="back",
                        actions=[
                            Action(ActionType.SCROLL, {"direction": "up", "amount": 100}),
                            Action(ActionType.SCROLL, {"direction": "left", "amount": 100}),
                        ],
                    )
                ],
            ),
            driver,
        )
        driver._page.wait_for_function("scrollX === 100 && scrollY === 100")
    finally:
        driver.close()
