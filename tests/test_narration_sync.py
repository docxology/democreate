"""Tests for the TTS->STT sync subsystem (heuristic transcriber + sync_demo)."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError, SyncError
from democreate.narration.sync import (
    HeuristicTranscriber,
    Transcriber,
    WhisperTranscriber,
    absolute_word_timestamps,
    get_transcriber,
    sync_demo,
)
from democreate.narration.tts import synthesize_demo


def _write_wav(path: Path, duration_ms: int, sample_rate: int = 22050) -> None:
    frames = int(round(sample_rate * duration_ms / 1000))
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"\x00" * (frames * 2))


# --- HeuristicTranscriber -------------------------------------------------


def test_heuristic_returns_empty_for_none_text(tmp_path: Path) -> None:
    p = tmp_path / "a.wav"
    _write_wav(p, 1000)
    assert HeuristicTranscriber().transcribe(p, None) == []


def test_heuristic_returns_empty_for_blank_text(tmp_path: Path) -> None:
    p = tmp_path / "a.wav"
    _write_wav(p, 1000)
    assert HeuristicTranscriber().transcribe(p, "   ") == []


def test_heuristic_one_word_per_input_word(tmp_path: Path) -> None:
    p = tmp_path / "a.wav"
    _write_wav(p, 2000)
    words = HeuristicTranscriber().transcribe(p, "alpha beta gamma delta")
    assert [w.word for w in words] == ["alpha", "beta", "gamma", "delta"]


def test_heuristic_timestamps_monotonic_and_bounded(tmp_path: Path) -> None:
    p = tmp_path / "a.wav"
    _write_wav(p, 3000)
    words = HeuristicTranscriber().transcribe(p, "one two three four five")
    assert words[0].start_ms == 0
    for w in words:
        assert w.start_ms <= w.end_ms
    for prev, nxt in zip(words, words[1:], strict=False):
        assert prev.end_ms <= nxt.start_ms + 1
    # final word ends at the true measured duration
    assert words[-1].end_ms == pytest.approx(3000, abs=2)


def test_heuristic_longer_words_get_longer_spans(tmp_path: Path) -> None:
    p = tmp_path / "a.wav"
    _write_wav(p, 5000)
    words = HeuristicTranscriber().transcribe(p, "a supercalifragilistic b")
    spans = {w.word: w.end_ms - w.start_ms for w in words}
    assert spans["supercalifragilistic"] > spans["a"]


def test_heuristic_reads_true_duration(tmp_path: Path) -> None:
    short_p = tmp_path / "short.wav"
    long_p = tmp_path / "long.wav"
    _write_wav(short_p, 500)
    _write_wav(long_p, 4000)
    short_words = HeuristicTranscriber().transcribe(short_p, "x y")
    long_words = HeuristicTranscriber().transcribe(long_p, "x y")
    assert long_words[-1].end_ms > short_words[-1].end_ms


def test_heuristic_bad_wav_raises_sync_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.wav"
    bad.write_text("not a wav file at all")
    with pytest.raises(SyncError):
        HeuristicTranscriber().transcribe(bad, "hello there")


# --- get_transcriber ------------------------------------------------------


def test_get_transcriber_default() -> None:
    assert isinstance(get_transcriber("auto"), HeuristicTranscriber)
    assert isinstance(get_transcriber("heuristic"), HeuristicTranscriber)


def test_get_transcriber_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_transcriber("bogus")


def test_whisper_unavailable_raises() -> None:
    import importlib.util

    if importlib.util.find_spec("whisper") is None:
        with pytest.raises(BackendUnavailableError) as exc:
            get_transcriber("whisper")
        assert exc.value.backend == "whisper"
        assert exc.value.extra == "whisper"
    else:  # pragma: no cover - whisper installed
        assert isinstance(get_transcriber("whisper"), WhisperTranscriber)


def test_transcriber_base_not_implemented(tmp_path: Path) -> None:
    p = tmp_path / "a.wav"
    _write_wav(p, 500)
    with pytest.raises(NotImplementedError):
        Transcriber().transcribe(p, "hi")


# --- sync_demo ------------------------------------------------------------


def test_sync_demo_sets_cumulative_start_ms(sample_demo, tmp_workspace) -> None:
    clips = synthesize_demo(sample_demo, tmp_workspace)
    sync_demo(sample_demo, clips)

    chunks = sample_demo.iter_chunks()
    assert chunks[0].start_ms == 0
    expected = 0
    by_id = {c.chunk_id: c for c in clips}
    for chunk in chunks:
        assert chunk.start_ms == expected
        expected += by_id[chunk.id].duration_ms


def test_sync_demo_anchors_actions_to_trigger_words(
    sample_demo, tmp_workspace
) -> None:
    clips = synthesize_demo(sample_demo, tmp_workspace)
    sync_demo(sample_demo, clips)
    for action in sample_demo.iter_actions():
        assert action.timestamp_ms is not None
        assert action.timestamp_ms >= 0
        assert action.duration_ms == 600  # default applied


def test_sync_demo_trigger_match_offsets_within_chunk(tmp_workspace) -> None:
    from democreate.schema import Action, ActionType, Chunk, Demo, Scene

    scene = Scene(id="s1", title="t")
    scene.chunks.append(
        Chunk(
            id="c1",
            text="first second third fourth fifth target word here",
            actions=[
                Action(ActionType.CLICK, {}, trigger_word="target"),
                Action(ActionType.WAIT, {}),  # no trigger
            ],
        )
    )
    demo = Demo(title="T", scenes=[scene])
    clips = synthesize_demo(demo, tmp_workspace)
    sync_demo(demo, clips)

    triggered, untriggered = scene.chunks[0].actions
    # the triggered action should fire later than the untriggered one (offset > 0)
    assert triggered.timestamp_ms > untriggered.timestamp_ms
    assert untriggered.timestamp_ms == scene.chunks[0].start_ms


def test_sync_demo_unmatched_trigger_falls_back_to_chunk_start(
    tmp_workspace,
) -> None:
    from democreate.schema import Action, ActionType, Chunk, Demo, Scene

    scene = Scene(id="s1")
    scene.chunks.append(
        Chunk(
            id="c1",
            text="nothing here resembles it",
            actions=[Action(ActionType.ZOOM, {}, trigger_word="zzzzqqq")],
        )
    )
    demo = Demo(title="T", scenes=[scene])
    clips = synthesize_demo(demo, tmp_workspace)
    sync_demo(demo, clips)
    action = scene.chunks[0].actions[0]
    assert action.timestamp_ms == scene.chunks[0].start_ms


def test_sync_demo_preserves_existing_duration(tmp_workspace) -> None:
    from democreate.schema import Action, ActionType, Chunk, Demo, Scene

    scene = Scene(id="s1")
    scene.chunks.append(
        Chunk(
            id="c1",
            text="hello world",
            actions=[Action(ActionType.WAIT, {}, duration_ms=1234)],
        )
    )
    demo = Demo(title="T", scenes=[scene])
    clips = synthesize_demo(demo, tmp_workspace)
    sync_demo(demo, clips)
    assert scene.chunks[0].actions[0].duration_ms == 1234


def test_sync_demo_returns_same_instance(sample_demo, tmp_workspace) -> None:
    clips = synthesize_demo(sample_demo, tmp_workspace)
    assert sync_demo(sample_demo, clips) is sample_demo


def test_sync_demo_missing_audio_uses_fallback(sample_demo) -> None:
    # no clips and no audio files: cumulative falls back to 300 ms per chunk
    sync_demo(sample_demo, [])
    chunks = sample_demo.iter_chunks()
    assert chunks[0].start_ms == 0
    assert chunks[1].start_ms == 300
    for action in sample_demo.iter_actions():
        assert action.timestamp_ms is not None


def test_sync_demo_uses_chunk_audio_path_when_no_clip(
    sample_demo, tmp_workspace
) -> None:
    # synthesize sets chunk.audio_path; pass empty clips so sync uses audio_path
    synthesize_demo(sample_demo, tmp_workspace)
    sync_demo(sample_demo, [])
    chunks = sample_demo.iter_chunks()
    # second chunk starts after first chunk's measured audio (> fallback)
    assert chunks[1].start_ms > 0


# --- absolute_word_timestamps ---------------------------------------------


def test_absolute_word_timestamps_flat_and_increasing(
    sample_demo, tmp_workspace
) -> None:
    clips = synthesize_demo(sample_demo, tmp_workspace)
    words = absolute_word_timestamps(sample_demo, clips)
    total_input_words = sum(c.word_count() for c in sample_demo.iter_chunks())
    assert len(words) == total_input_words
    for prev, nxt in zip(words, words[1:], strict=False):
        assert prev.start_ms <= nxt.start_ms


def test_absolute_word_timestamps_uses_offsets(sample_demo, tmp_workspace) -> None:
    clips = synthesize_demo(sample_demo, tmp_workspace)
    words = absolute_word_timestamps(sample_demo, clips)
    # last word's absolute start should exceed the first chunk's duration
    first_clip = clips[0]
    assert words[-1].start_ms >= first_clip.duration_ms


def test_absolute_word_timestamps_empty_without_audio(sample_demo) -> None:
    assert absolute_word_timestamps(sample_demo, []) == []


def test_absolute_word_timestamps_via_chunk_audio_path(
    sample_demo, tmp_workspace
) -> None:
    synthesize_demo(sample_demo, tmp_workspace)
    words = absolute_word_timestamps(sample_demo, [])
    assert len(words) > 0
