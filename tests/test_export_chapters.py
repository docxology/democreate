"""Tests for :mod:`democreate.export.chapters`.

Builds chapter exports from the shared ``sample_demo`` fixture and asserts the
YouTube and ffmetadata formats are well-formed, deterministic, and monotonic,
that files are written, and that the guarded ffmpeg embed step raises when the
binary is absent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError
from democreate.export import chapters as ch
from democreate.export.interactive import build_timeline
from democreate.schema import Demo


def _parse_youtube_seconds(timestamp: str) -> int:
    """Parse a ``M:SS`` / ``H:MM:SS`` timestamp into total seconds."""
    parts = [int(p) for p in timestamp.split(":")]
    total = 0
    for part in parts:
        total = total * 60 + part
    return total


def test_youtube_starts_at_zero_and_one_line_per_scene(sample_demo: Demo) -> None:
    text = ch.to_youtube_chapters(sample_demo)
    lines = text.splitlines()

    assert len(lines) == len(sample_demo.scenes)
    assert lines[0].startswith("0:00 ")


def test_youtube_titles_match_scene_titles(sample_demo: Demo) -> None:
    text = ch.to_youtube_chapters(sample_demo)
    lines = text.splitlines()

    for line, scene in zip(lines, sample_demo.scenes, strict=True):
        timestamp, _, title = line.partition(" ")
        assert title == (scene.title or scene.id)


def test_youtube_timestamps_monotonic_and_formatted(sample_demo: Demo) -> None:
    lines = ch.to_youtube_chapters(sample_demo).splitlines()
    seconds = []
    for line in lines:
        timestamp = line.split(" ", 1)[0]
        # M:SS or H:MM:SS — at least one colon, two-digit trailing fields.
        assert ":" in timestamp
        tail = timestamp.split(":")[1:]
        assert all(len(field) == 2 for field in tail)
        seconds.append(_parse_youtube_seconds(timestamp))

    assert seconds == sorted(seconds)


def test_youtube_pure_and_deterministic(sample_demo: Demo) -> None:
    assert ch.to_youtube_chapters(sample_demo) == ch.to_youtube_chapters(sample_demo)


def test_ffmetadata_header_and_chapter_count(sample_demo: Demo) -> None:
    doc = ch.to_ffmetadata(sample_demo)

    assert doc.startswith(";FFMETADATA1")
    assert doc.count("[CHAPTER]") == len(sample_demo.scenes)
    assert doc.count("TIMEBASE=1/1000") == len(sample_demo.scenes)
    assert doc.endswith("\n")


def test_ffmetadata_monotonic_start_lt_end(sample_demo: Demo) -> None:
    doc = ch.to_ffmetadata(sample_demo)
    starts = [
        int(line.split("=", 1)[1])
        for line in doc.splitlines()
        if line.startswith("START=")
    ]
    ends = [
        int(line.split("=", 1)[1])
        for line in doc.splitlines()
        if line.startswith("END=")
    ]
    total_ms = build_timeline(sample_demo)["total_ms"]

    assert len(starts) == len(ends) == len(sample_demo.scenes)
    for start, end in zip(starts, ends, strict=True):
        assert start < end
    # Each chapter's END is the next chapter's START; last END is total length.
    assert ends[:-1] == starts[1:]
    assert ends[-1] == total_ms


def test_ffmetadata_pure_and_deterministic(sample_demo: Demo) -> None:
    assert ch.to_ffmetadata(sample_demo) == ch.to_ffmetadata(sample_demo)


def test_write_chapters_writes_both_files(sample_demo: Demo, tmp_path: Path) -> None:
    out_dir = tmp_path / "chapters"
    result = ch.write_chapters(sample_demo, out_dir)

    assert set(result) == {"youtube", "ffmetadata"}
    assert result["youtube"] == out_dir / "youtube_chapters.txt"
    assert result["ffmetadata"] == out_dir / "ffmetadata.txt"
    assert result["youtube"].is_file()
    assert result["ffmetadata"].is_file()

    youtube_text = result["youtube"].read_text(encoding="utf-8")
    assert youtube_text.startswith("0:00 ")
    ffmetadata_text = result["ffmetadata"].read_text(encoding="utf-8")
    assert ffmetadata_text.startswith(";FFMETADATA1")


def test_write_chapters_creates_missing_directory(
    sample_demo: Demo, tmp_path: Path
) -> None:
    out_dir = tmp_path / "deep" / "nested" / "out"
    ch.write_chapters(sample_demo, out_dir)
    assert (out_dir / "youtube_chapters.txt").is_file()


def test_embed_chapters_raises_when_ffmpeg_absent(
    sample_demo: Demo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ch, "which", lambda _name: None)

    files = ch.write_chapters(sample_demo, tmp_path)
    mp4_in = tmp_path / "in.mp4"
    mp4_in.write_bytes(b"not really an mp4")

    with pytest.raises(BackendUnavailableError) as excinfo:
        ch.embed_chapters(mp4_in, files["ffmetadata"], tmp_path / "out.mp4")

    assert excinfo.value.backend == "ffmpeg"
    assert excinfo.value.extra == "video"
