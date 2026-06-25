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
    assert excinfo.value.extra == "video"
