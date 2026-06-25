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
