"""Tests for :mod:`democreate.export.metadata` — MP4 container metadata tags."""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.config import MetadataConfig
from democreate.errors import BackendUnavailableError
from democreate.export import metadata as md
from democreate.schema import Demo


def test_build_tags_from_demo_only(sample_demo: Demo) -> None:
    """With no config, only non-empty tags (notably title) are present."""
    tags = md.build_tags(sample_demo)
    assert tags["title"] == "DemoCreate Self Tour"
    # author/date are empty without a config → dropped entirely.
    assert "artist" not in tags
    assert "date" not in tags
    # the credit always populates comment/description.
    assert "made with DemoCreate" in tags["comment"]
    assert tags["comment"] == tags["description"]
    # no blank values ever leak through.
    assert all(v for v in tags.values())


def test_build_tags_with_config_maps_fields(sample_demo: Demo) -> None:
    """author→artist, date→date, source/url fold into comment; title override wins."""
    meta = MetadataConfig(
        author="Ada Lovelace",
        title="Override Title",
        date="2026-06-04",
        source="github.com/acme/repo",
        url="https://example.com/demo",
    )
    tags = md.build_tags(sample_demo, meta, version="0.6.0")
    assert tags["title"] == "Override Title"
    assert tags["artist"] == "Ada Lovelace"
    assert tags["date"] == "2026-06-04"
    assert "made with DemoCreate 0.6.0" in tags["comment"]
    assert "github.com/acme/repo" in tags["comment"]
    assert "https://example.com/demo" in tags["comment"]


def test_build_tags_drops_empty_config_fields(sample_demo: Demo) -> None:
    """A blank/whitespace config field does not emit a tag; demo title fills in."""
    meta = MetadataConfig(author="   ", title="", source="", url="")
    tags = md.build_tags(sample_demo, meta)
    assert tags["title"] == "DemoCreate Self Tour"
    assert "artist" not in tags
    assert tags["comment"] == "made with DemoCreate"


def test_to_ffmetadata_header_and_escaping(sample_demo: Demo) -> None:
    """Document starts with ;FFMETADATA1 and escapes special characters."""
    meta = MetadataConfig(author="A;B=C#D\\E", source="x")
    tags = md.build_tags(sample_demo, meta)
    doc = md.to_ffmetadata(tags)
    assert doc.startswith(";FFMETADATA1\n")
    assert doc.endswith("\n")
    # the artist value's specials must be backslash-escaped on its line.
    assert "artist=A\\;B\\=C\\#D\\\\E" in doc


def test_to_ffmetadata_roundtrip_shape() -> None:
    """Splitting each line on the first unescaped '=' recovers keys and values."""
    tags = {"title": "Hello = World", "artist": "Jane;Doe"}
    doc = md.to_ffmetadata(tags)
    body = [ln for ln in doc.splitlines() if ln and not ln.startswith(";")]

    def unescape(text: str) -> str:
        out: list[str] = []
        i = 0
        while i < len(text):
            if text[i] == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 2
            else:
                out.append(text[i])
                i += 1
        return "".join(out)

    recovered: dict[str, str] = {}
    for line in body:
        # find first unescaped '='
        idx = 0
        while idx < len(line):
            if line[idx] == "\\":
                idx += 2
                continue
            if line[idx] == "=":
                break
            idx += 1
        key, value = line[:idx], line[idx + 1 :]
        recovered[unescape(key)] = unescape(value)
    assert recovered == tags


def test_ffmpeg_metadata_args_sorted_and_alternating(sample_demo: Demo) -> None:
    """The argv fragment alternates -metadata with k=v and is key-sorted."""
    meta = MetadataConfig(author="Ada", date="2026-06-04")
    tags = md.build_tags(sample_demo, meta)
    args = md.ffmpeg_metadata_args(tags)
    assert len(args) == 2 * len(tags)
    flags = args[0::2]
    pairs = args[1::2]
    assert set(flags) == {"-metadata"}
    keys = [p.split("=", 1)[0] for p in pairs]
    assert keys == sorted(tags)
    # each pair faithfully carries the tag value.
    for pair in pairs:
        key, value = pair.split("=", 1)
        assert tags[key] == value


def test_ffmpeg_metadata_args_empty() -> None:
    """No tags → empty argv fragment."""
    assert md.ffmpeg_metadata_args({}) == []


def test_embed_tags_raises_when_ffmpeg_missing(
    sample_demo: Demo, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """embed_tags raises BackendUnavailableError when ffmpeg is absent."""
    monkeypatch.setattr(md.shutil, "which", lambda _name: None)
    tags = md.build_tags(sample_demo)
    mp4_in = tmp_path / "in.mp4"
    mp4_in.write_bytes(b"\x00")
    with pytest.raises(BackendUnavailableError) as excinfo:
        md.embed_tags(mp4_in, tmp_path / "out.mp4", tags)
    assert excinfo.value.backend == "ffmpeg"
    assert excinfo.value.extra is None


def _native_multitrack_source(tmp_path: Path) -> Path:
    """Create two differently tagged AAC tracks, subtitles and existing chapters."""
    import shutil
    import subprocess

    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("requires native ffmpeg/ffprobe with libx264 and AAC")
    subtitles = tmp_path / "source.srt"
    subtitles.write_text(
        "1\n00:00:00,000 --> 00:00:00,900\nOriginal subtitle\n", encoding="utf-8"
    )
    chapters = tmp_path / "old.ffmeta"
    chapters.write_text(
        ";FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\n"
        "START=0\nEND=1000\ntitle=Old chapter\n", encoding="utf-8",
    )
    source = tmp_path / "source.mp4"
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-y",
            "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=10:duration=1",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-f", "lavfi", "-i", "sine=frequency=880:duration=1",
            "-i", str(subtitles), "-i", str(chapters),
            "-map", "0:v", "-map", "1:a", "-map", "2:a", "-map", "3:s",
            "-map_chapters", "4", "-c:v", "libx264", "-preset", "ultrafast",
            "-threads", "1", "-c:a", "aac", "-c:s", "mov_text",
            "-metadata:s:a:0", "language=eng",
            "-metadata:s:a:1", "language=fra", "-metadata", "title=Original",
            str(source),
        ],
        capture_output=True, check=True,
    )
    return source


def _native_media_identity(path: Path) -> tuple[list, dict]:
    """Read native stream identities and per-stream encoded packet hashes."""
    import json
    import subprocess

    probe = json.loads(subprocess.run(
        [
            "ffprobe", "-v", "error", "-of", "json",
            "-show_streams", "-show_packets", "-show_data_hash", "sha256",
            str(path),
        ],
        capture_output=True, text=True, check=True,
    ).stdout)
    streams = [
        stream for stream in probe["streams"]
        if stream["codec_type"] in {"video", "audio", "subtitle"}
    ]
    identity = [
        (
            stream["codec_type"], stream["codec_name"],
            stream.get("tags", {}).get("language"),
        )
        for stream in streams
    ]
    packets = {
        index: [
            packet["data_hash"] for packet in probe["packets"]
            if packet["stream_index"] == stream["index"]
        ]
        for index, stream in enumerate(streams)
    }
    assert all(packets.values())
    return identity, packets


@pytest.mark.parametrize("replace_chapters", [False, True])
def test_native_tags_retain_all_media_and_selected_chapters(
    tmp_path: Path, replace_chapters: bool
) -> None:
    import json
    import subprocess

    from democreate.export.chapters import embed_chapters

    source = _native_multitrack_source(tmp_path)
    expected = _native_media_identity(source)
    assert [stream[2] for stream in expected[0] if stream[0] == "audio"] == [
        "eng", "fra",
    ]
    assert sum(stream[0] == "subtitle" for stream in expected[0]) == 1
    if replace_chapters:
        metadata = tmp_path / "new.ffmeta"
        metadata.write_text(
            ";FFMETADATA1\n[CHAPTER]\nTIMEBASE=1/1000\n"
            "START=0\nEND=500\ntitle=First\n"
            "[CHAPTER]\nTIMEBASE=1/1000\nSTART=500\nEND=1000\ntitle=Second\n",
            encoding="utf-8",
        )
        chaptered = tmp_path / "chaptered.mp4"
        assert embed_chapters(source, metadata, chaptered) == chaptered
        assert _native_media_identity(chaptered) == expected
        source = chaptered
    # In-place publication must also work without ffmpeg truncating its input.
    assert md.embed_tags(source, source, {"title": "Updated"}) == source
    assert _native_media_identity(source) == expected
    probe = json.loads(subprocess.run(
        [
            "ffprobe", "-v", "error", "-of", "json",
            "-show_chapters", "-show_format", str(source),
        ],
        capture_output=True, text=True, check=True,
    ).stdout)
    assert probe["format"]["tags"]["title"] == "Updated"
    assert [chapter["tags"]["title"] for chapter in probe["chapters"]] == (
        ["First", "Second"] if replace_chapters else ["Old chapter"]
    )
    subprocess.run(
        [
            "ffmpeg", "-v", "error", "-xerror", "-err_detect", "explode",
            "-i", str(source), "-map", "0:v", "-map", "0:a", "-f", "null", "-",
        ],
        capture_output=True, check=True,
    )


def test_native_tags_preserve_destination_on_real_write_failure(tmp_path: Path) -> None:
    import subprocess
    import sys

    pytest.importorskip("resource", reason="requires POSIX RLIMIT_FSIZE")
    source = _native_multitrack_source(tmp_path)
    output = tmp_path / "final.mp4"
    previous = source.read_bytes()
    assert len(previous) > 2048
    output.write_bytes(previous)
    before = set(tmp_path.iterdir())
    child = """
import resource
import sys
from pathlib import Path
from democreate.errors import RenderError
from democreate.export.metadata import embed_tags
root = Path(sys.argv[1])
resource.setrlimit(resource.RLIMIT_FSIZE, (2048, 2048))
try:
    embed_tags(root / "source.mp4", root / "final.mp4", {"title": "Replacement"})
except RenderError:
    pass
else:
    raise AssertionError("native remux unexpectedly succeeded under RLIMIT_FSIZE")
"""
    completed = subprocess.run(
        [sys.executable, "-B", "-c", child, str(tmp_path)],
        capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert output.read_bytes() == previous
    assert set(tmp_path.iterdir()) == before
