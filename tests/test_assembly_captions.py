"""Tests for the pure caption/subtitle formatters."""

from __future__ import annotations

import re

from democreate.assembly.captions import (
    to_ass,
    to_srt,
    to_vtt,
    word_timestamps_to_srt,
)
from democreate.schema import Chunk, Demo, Scene, WordTimestamp

_SRT_TS = re.compile(r"\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}")
_VTT_TS = re.compile(r"\d{2}:\d{2}:\d{2}\.\d{3} --> \d{2}:\d{2}:\d{2}\.\d{3}")


def test_to_srt_cue_count_equals_chunks(sample_demo: Demo) -> None:
    srt = to_srt(sample_demo)
    n_chunks = len(sample_demo.iter_chunks())
    # cue indices 1..N present
    assert _SRT_TS.search(srt)
    indices = re.findall(r"^(\d+)$", srt, flags=re.MULTILINE)
    assert indices == [str(i) for i in range(1, n_chunks + 1)]
    assert len(_SRT_TS.findall(srt)) == n_chunks


def test_to_srt_timecode_format(sample_demo: Demo) -> None:
    srt = to_srt(sample_demo)
    assert srt.startswith("1\n")
    assert "00:00:00," in srt
    for chunk in sample_demo.iter_chunks():
        assert chunk.text in srt


def test_to_vtt_header_and_count(sample_demo: Demo) -> None:
    vtt = to_vtt(sample_demo)
    assert vtt.startswith("WEBVTT")
    n_chunks = len(sample_demo.iter_chunks())
    assert len(_VTT_TS.findall(vtt)) == n_chunks
    # VTT uses dot separator, not comma
    assert "00:00:00." in vtt
    assert "," not in vtt.split("\n", 1)[0]


def test_to_ass_sections_and_count(sample_demo: Demo) -> None:
    ass = to_ass(sample_demo)
    assert "[Script Info]" in ass
    assert "[V4+ Styles]" in ass
    assert "[Events]" in ass
    assert "Format: Layer, Start, End" in ass
    dialogues = re.findall(r"^Dialogue:", ass, flags=re.MULTILINE)
    assert len(dialogues) == len(sample_demo.iter_chunks())
    assert sample_demo.title in ass


def test_ass_timecode_centiseconds(sample_demo: Demo) -> None:
    ass = to_ass(sample_demo)
    assert re.search(r"Dialogue: 0,\d:\d{2}:\d{2}\.\d{2},\d:\d{2}:\d{2}\.\d{2},", ass)


def test_cue_windows_use_synced_start_ms() -> None:
    scene = Scene(id="s", title="S")
    scene.chunks.append(Chunk(id="a", text="one two three", start_ms=2000))
    scene.chunks.append(Chunk(id="b", text="four five six"))
    demo = Demo(title="Synced", scenes=[scene])
    srt = to_srt(demo)
    # first cue starts at 2.000s
    assert "00:00:02,000 -->" in srt


def test_empty_demo_produces_minimal_output() -> None:
    demo = Demo(title="Empty")
    assert to_srt(demo) == ""
    assert to_vtt(demo).startswith("WEBVTT")
    ass = to_ass(demo)
    assert "[Events]" in ass
    # no Dialogue lines
    assert "Dialogue:" not in ass


def test_word_timestamps_to_srt() -> None:
    words = [
        WordTimestamp("hello", 0, 400),
        WordTimestamp("world", 400, 900),
    ]
    srt = word_timestamps_to_srt(words)
    indices = re.findall(r"^(\d+)$", srt, flags=re.MULTILINE)
    assert indices == ["1", "2"]
    assert "00:00:00,000 --> 00:00:00,400" in srt
    assert "00:00:00,400 --> 00:00:00,900" in srt
    assert "hello" in srt and "world" in srt


def test_word_timestamps_empty() -> None:
    assert word_timestamps_to_srt([]) == ""


def test_srt_timecode_hours_minutes() -> None:
    # 1h 2m 3s 456ms
    ms = (1 * 3600 + 2 * 60 + 3) * 1000 + 456
    words = [WordTimestamp("late", ms, ms + 100)]
    srt = word_timestamps_to_srt(words)
    assert "01:02:03,456 --> 01:02:03,556" in srt
