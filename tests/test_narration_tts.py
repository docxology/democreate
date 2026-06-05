"""Tests for the TTS subsystem (deterministic silent backend + guards)."""

from __future__ import annotations

import wave
from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError
from democreate.media import AudioClip
from democreate.narration.tts import (
    ChatterboxTTSBackend,
    KokoroTTSBackend,
    SilentTTSBackend,
    TTSBackend,
    get_tts_backend,
    synthesize_demo,
)


def _read_wav(path: Path) -> tuple[int, int, int, int]:
    with wave.open(str(path), "rb") as wav:
        return (
            wav.getnchannels(),
            wav.getsampwidth(),
            wav.getframerate(),
            wav.getnframes(),
        )


# --- SilentTTSBackend -----------------------------------------------------


def test_silent_backend_is_available() -> None:
    assert SilentTTSBackend().is_available() is True
    assert SilentTTSBackend().name == "silent"


def test_silent_backend_writes_valid_wav(tmp_path: Path) -> None:
    backend = SilentTTSBackend()
    out = tmp_path / "clip.wav"
    clip = backend.synthesize("hello world this is a test", out)

    assert isinstance(clip, AudioClip)
    assert out.exists()
    channels, width, rate, frames = _read_wav(out)
    assert channels == 1
    assert width == 2
    assert rate == 22050
    assert frames > 0


def test_silent_backend_writes_only_silence(tmp_path: Path) -> None:
    out = tmp_path / "silence.wav"
    SilentTTSBackend().synthesize("some words here", out)
    with wave.open(str(out), "rb") as wav:
        data = wav.readframes(wav.getnframes())
    assert set(data) == {0}


def test_silent_backend_duration_matches_frames(tmp_path: Path) -> None:
    backend = SilentTTSBackend(sample_rate=8000)
    out = tmp_path / "c.wav"
    clip = backend.synthesize("one two three four five six", out)
    _, _, rate, frames = _read_wav(out)
    expected_ms = int(round(frames / rate * 1000))
    assert clip.duration_ms == expected_ms
    assert clip.sample_rate == 8000


def test_silent_backend_empty_text_uses_minimum(tmp_path: Path) -> None:
    backend = SilentTTSBackend(min_duration_ms=300)
    assert backend.estimate_duration_ms("") == 300
    clip = backend.synthesize("", tmp_path / "e.wav")
    # measured ms is computed from frames; should be close to the 300ms floor
    assert clip.duration_ms >= 290
    assert clip.text == ""


def test_silent_backend_longer_text_longer_duration() -> None:
    backend = SilentTTSBackend()
    short = backend.estimate_duration_ms("one two")
    long = backend.estimate_duration_ms(" ".join(["word"] * 200))
    assert long > short


def test_silent_backend_carries_text_and_unset_chunk_id(tmp_path: Path) -> None:
    clip = SilentTTSBackend().synthesize("carry me", tmp_path / "t.wav")
    assert clip.text == "carry me"
    assert clip.chunk_id is None


def test_silent_backend_creates_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "nested" / "deep" / "clip.wav"
    SilentTTSBackend().synthesize("hi", out)
    assert out.exists()


def test_silent_backend_custom_wpm_affects_duration() -> None:
    slow = SilentTTSBackend(wpm=60)
    fast = SilentTTSBackend(wpm=300)
    text = " ".join(["w"] * 60)
    assert slow.estimate_duration_ms(text) > fast.estimate_duration_ms(text)


@pytest.mark.parametrize(
    "kwargs",
    [{"wpm": 0}, {"wpm": -5}, {"sample_rate": 0}, {"min_duration_ms": -1}],
)
def test_silent_backend_rejects_bad_params(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        SilentTTSBackend(**kwargs)


# --- get_tts_backend ------------------------------------------------------


def test_get_tts_backend_auto_and_silent() -> None:
    assert isinstance(get_tts_backend("auto"), SilentTTSBackend)
    assert isinstance(get_tts_backend("silent"), SilentTTSBackend)
    assert isinstance(get_tts_backend("AUTO"), SilentTTSBackend)


def test_get_tts_backend_unknown_raises() -> None:
    with pytest.raises(ValueError):
        get_tts_backend("nope")


# --- guarded backends -----------------------------------------------------


def test_kokoro_unavailable_raises() -> None:
    import importlib.util

    if importlib.util.find_spec("kokoro") is None:
        with pytest.raises(BackendUnavailableError) as exc:
            get_tts_backend("kokoro")
        assert exc.value.backend == "kokoro"
        assert exc.value.extra == "tts"
    else:  # pragma: no cover - kokoro installed
        assert isinstance(get_tts_backend("kokoro"), KokoroTTSBackend)


def test_chatterbox_unavailable_raises() -> None:
    import importlib.util

    if importlib.util.find_spec("chatterbox") is None:
        with pytest.raises(BackendUnavailableError) as exc:
            get_tts_backend("chatterbox")
        assert exc.value.backend == "chatterbox"
        assert exc.value.extra == "tts"
    else:  # pragma: no cover - chatterbox installed
        assert isinstance(get_tts_backend("chatterbox"), ChatterboxTTSBackend)


def test_base_class_methods_not_implemented() -> None:
    base = TTSBackend()
    with pytest.raises(NotImplementedError):
        base.is_available()
    with pytest.raises(NotImplementedError):
        base.synthesize("x", Path("y.wav"))


# --- synthesize_demo ------------------------------------------------------


def test_synthesize_demo_writes_per_chunk_audio(sample_demo, tmp_workspace) -> None:
    clips = synthesize_demo(sample_demo, tmp_workspace)
    chunks = sample_demo.iter_chunks()
    assert len(clips) == len(chunks)
    for clip, chunk in zip(clips, chunks, strict=True):
        assert clip.chunk_id == chunk.id
        assert chunk.audio_path is not None
        assert Path(chunk.audio_path).exists()
        assert clip.path == Path(tmp_workspace.audio) / f"{chunk.id}.wav"
        assert clip.duration_ms > 0


def test_synthesize_demo_order_matches_chunks(sample_demo, tmp_workspace) -> None:
    clips = synthesize_demo(sample_demo, tmp_workspace)
    assert [c.chunk_id for c in clips] == [c.id for c in sample_demo.iter_chunks()]


def test_synthesize_demo_custom_backend(sample_demo, tmp_workspace) -> None:
    backend = SilentTTSBackend(sample_rate=8000)
    clips = synthesize_demo(sample_demo, tmp_workspace, backend=backend)
    assert all(c.sample_rate == 8000 for c in clips)


def test_synthesize_demo_empty_demo(tmp_workspace) -> None:
    from democreate.schema import Demo

    clips = synthesize_demo(Demo(title="Empty"), tmp_workspace)
    assert clips == []
