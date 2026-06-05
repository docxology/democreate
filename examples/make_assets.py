#!/usr/bin/env python
"""Regenerate the visual assets used by the intro demo.

* ``assets/architecture.png`` — the generated architecture diagram (pure Python,
  always reproducible).
* ``assets/dashboard.png``    — a real browser screenshot of the exported HTML
  player. This needs a browser; if Playwright (the ``browser`` extra) is
  installed it is captured automatically, otherwise this script prints the manual
  capture command and leaves any existing screenshot in place.

Usage::

    python examples/make_assets.py
"""

from __future__ import annotations

import importlib.util
import tempfile
from pathlib import Path

from democreate.animation.diagram import democreate_architecture_image

_ASSETS = Path(__file__).resolve().parent / "assets"


def make_architecture() -> Path:
    """Render the architecture diagram asset and return its path."""
    _ASSETS.mkdir(parents=True, exist_ok=True)
    out = _ASSETS / "architecture.png"
    democreate_architecture_image((1920, 1080)).save(out)
    print(f"wrote {out}")
    return out


def make_dashboard() -> Path | None:
    """Build the intro player and screenshot it with Playwright, if available.

    Returns the screenshot path, or ``None`` when no browser backend is present
    (the manual `chrome-devtools-axi` command is printed instead).
    """
    out = _ASSETS / "dashboard.png"
    if importlib.util.find_spec("playwright") is None:
        print(
            "playwright not installed — capture the dashboard manually:\n"
            "  democreate build examples/democreate_intro.json -o /tmp/intro\n"
            "  chrome-devtools-axi resize 1920 1080\n"
            "  chrome-devtools-axi open file:///tmp/intro/web/player.html\n"
            f"  chrome-devtools-axi screenshot {out}"
        )
        return None

    from playwright.sync_api import sync_playwright  # type: ignore  # noqa: PLC0415

    from democreate.cli import _starter_demo  # noqa: PLC0415
    from democreate.pipeline import build_demo  # noqa: PLC0415
    from democreate.project_paths import Workspace  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:  # pragma: no cover - needs browser
        result = build_demo(_starter_demo(), Workspace(tmp), strict=False)
        url = f"file://{result.player_path.resolve()}"
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(url)
            page.wait_for_timeout(800)
            page.screenshot(path=str(out))
            browser.close()
    print(f"wrote {out}")
    return out


def main() -> None:
    """Regenerate all assets."""
    make_architecture()
    make_dashboard()


if __name__ == "__main__":
    main()
