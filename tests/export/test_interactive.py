"""Tests for the interactive HTML player export."""

from __future__ import annotations

from pathlib import Path

from democreate.export.interactive import build_timeline, export_html_player
from democreate.schema import Demo, Scene


def test_export_html_player_basic(sample_demo: Demo, tmp_path: Path) -> None:
    out = tmp_path / "player.html"
    result = export_html_player(sample_demo, None, out)
    assert result == out
    assert out.exists()
    html = out.read_text(encoding="utf-8")

    # title present
    assert sample_demo.title in html
    # every scene title present as a chapter
    for scene in sample_demo.scenes:
        assert scene.title in html
    # has the JS player
    assert "<script" in html
    # self-contained: no external network asset references
    assert "http://" not in html
    assert "https://" not in html
    # JSON embedded in <script> must not contain HTML entities (would break JS)
    script_block = html.split("<script>", 1)[1]
    assert "&#34;" not in script_block
    assert "&amp;" not in script_block


def test_export_html_player_with_frames_dir(sample_demo: Demo, tmp_path: Path) -> None:
    out = tmp_path / "player.html"
    export_html_player(sample_demo, None, out, frames_dir="frames")
    html = out.read_text(encoding="utf-8")
    assert "<img" in html
    assert '"frames"' in html


def test_export_html_player_uses_passed_timeline(
    sample_demo: Demo, tmp_path: Path
) -> None:
    timeline = {
        "captions": [
            {
                "chunk_id": "x",
                "scene_id": "intro",
                "text": "CUSTOM CAPTION TEXT",
                "start_ms": 0,
                "end_ms": 5000,
                "frame": "x.png",
            }
        ],
        "chapters": [{"title": "Custom Chapter", "scene_id": "intro", "start_ms": 0}],
        "total_ms": 5000,
    }
    out = tmp_path / "player.html"
    export_html_player(sample_demo, timeline, out)
    html = out.read_text(encoding="utf-8")
    assert "CUSTOM CAPTION TEXT" in html
    assert "Custom Chapter" in html
    assert "5000" in html


def test_export_html_player_escapes_title(tmp_path: Path) -> None:
    demo = Demo(title="Tour <b>&</b> More", scenes=[Scene(id="s", title="Only")])
    out = tmp_path / "player.html"
    export_html_player(demo, None, out)
    html = out.read_text(encoding="utf-8")
    # autoescape turns the raw < into &lt; in HTML body context
    assert "&lt;b&gt;" in html


def test_build_timeline_structure(sample_demo: Demo) -> None:
    tl = build_timeline(sample_demo)
    assert set(tl) == {"captions", "chapters", "total_ms"}
    # one chapter per scene, one caption per chunk
    assert len(tl["chapters"]) == len(sample_demo.scenes)
    assert len(tl["captions"]) == len(sample_demo.iter_chunks())
    # cues are monotonically non-decreasing in start_ms
    starts = [c["start_ms"] for c in tl["captions"]]
    assert starts == sorted(starts)
    assert tl["total_ms"] > 0


def test_build_timeline_respects_synced_start(sample_demo: Demo) -> None:
    sample_demo.scenes[0].chunks[0].start_ms = 1234
    tl = build_timeline(sample_demo)
    assert tl["captions"][0]["start_ms"] == 1234
    assert tl["chapters"][0]["start_ms"] == 1234


def test_build_timeline_empty_scene(tmp_path: Path) -> None:
    demo = Demo(title="Empty", scenes=[Scene(id="s1", title="Lonely")])
    tl = build_timeline(demo)
    assert len(tl["chapters"]) == 1
    assert tl["captions"] == []
    assert tl["total_ms"] == 0


def test_timeline_preserves_measured_durations_and_explicit_windows(
    tmp_path: Path,
) -> None:
    from democreate.schema import Chunk

    demo = Demo(
        title="Measured",
        scenes=[
            Scene(
                id="first",
                chunks=[
                    Chunk(id="a", text="short", start_ms=100, duration_ms=2100),
                    Chunk(id="b", text="short", start_ms=3000, duration_ms=700),
                ],
            ),
            Scene(id="second", chunks=[Chunk(id="c", text="short", duration_ms=1250)]),
        ],
    )
    timeline = build_timeline(demo)
    assert [cue["start_ms"] for cue in timeline["captions"]] == [100, 3000, 3700]
    assert [cue["end_ms"] for cue in timeline["captions"]] == [2200, 3700, 4950]
    assert [chapter["start_ms"] for chapter in timeline["chapters"]] == [100, 3700]
    assert timeline["total_ms"] == 4950
    out = export_html_player(
        demo, {"captions": [], "chapters": []}, tmp_path / "p.html"
    )
    assert "const TOTAL_MS = 4950;" in out.read_text(encoding="utf-8")


def test_timeline_zero_measured_duration_does_not_fall_back_to_estimate() -> None:
    from democreate.schema import Chunk

    demo = Demo(
        title="Zero",
        scenes=[
            Scene(
                id="s",
                chunks=[
                    Chunk(
                        id="a",
                        text="many words are not a measured clip",
                        duration_ms=0,
                    ),
                    Chunk(id="b", text="two words"),
                ],
            )
        ],
    )
    timeline = build_timeline(demo)
    assert [cue["start_ms"] for cue in timeline["captions"]] == [0, 0]
    assert timeline["total_ms"] == 800


def test_native_browser_clears_captions_outside_measured_windows(
    tmp_path: Path,
) -> None:
    import pytest

    from democreate.schema import Chunk

    playwright = pytest.importorskip("playwright.sync_api")
    first_text = "first </script><script>window.injected=true</script>"
    second_text = "second & < > " + chr(0x2028) + chr(0x2029)
    demo = Demo(
        title="Measured browser",
        scenes=[
            Scene(
                id="s",
                chunks=[
                    Chunk(id="a", text=first_text, start_ms=300, duration_ms=700),
                    Chunk(id="b", text=second_text, start_ms=1700, duration_ms=600),
                ],
            )
        ],
    )
    timeline = build_timeline(demo)
    timeline["total_ms"] = 5000
    out = export_html_player(demo, timeline, tmp_path / "player.html")
    with playwright.sync_playwright() as runtime:
        if not Path(runtime.chromium.executable_path).is_file():
            pytest.skip("requires a real Playwright Chromium installation")
        browser = runtime.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(out.as_uri())
            for time_ms, expected in [
                (0, ""), (299, ""), (300, first_text), (999, first_text),
                (1000, ""), (1699, ""), (1700, second_text), (2299, second_text),
                (2300, ""), (4999, ""),
            ]:
                page.evaluate("(ms) => seek(ms)", time_ms)
                assert page.locator("#caption").text_content() == expected
            assert page.evaluate("typeof window.injected") == "undefined"
        finally:
            browser.close()
