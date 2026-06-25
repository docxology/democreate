"""Tests for the Kokoro neural-TTS backend.

The heavy synthesis path (loading a ~340 MB ONNX model) is gated behind the
``backend`` marker and an availability check, matching the project convention.
The model-file *resolution* logic is pure and tested with real temp files +
``monkeypatch`` on the environment (no mocks of any backend output).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError
from democreate.narration.tts import (
    KokoroTTSBackend,
    _kokoro_cache_dir,
    _kokoro_model_paths,
)


def _clear_kokoro_env(monkeypatch) -> None:
    monkeypatch.delenv("KOKORO_MODEL_PATH", raising=False)
    monkeypatch.delenv("KOKORO_VOICES_PATH", raising=False)


def test_split_for_tts_keeps_short_text_whole() -> None:
    from democreate.narration.tts import _split_for_tts

    assert _split_for_tts("Short sentence.") == ["Short sentence."]
    assert _split_for_tts("") == []


def test_split_for_tts_bounds_long_text() -> None:
    from democreate.narration.tts import _split_for_tts

    text = " ".join(f"Sentence number {i} about modules." for i in range(60))
    segments = _split_for_tts(text, max_chars=200)
    assert len(segments) > 1
    assert all(len(s) <= 200 for s in segments)
    assert " ".join(segments).split() == text.split()  # no words lost


def test_split_for_tts_splits_one_overlong_sentence() -> None:
    from democreate.narration.tts import _split_for_tts

    text = "word " * 200  # a single ~1000-char run with no sentence terminator
    segments = _split_for_tts(text, max_chars=120)
    assert len(segments) > 1
    assert all(len(s) <= 120 for s in segments)


def test_cache_dir_override(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEMOCREATE_KOKORO_DIR", str(tmp_path))
    assert _kokoro_cache_dir() == tmp_path


def test_model_paths_none_when_absent(monkeypatch, tmp_path: Path) -> None:
    _clear_kokoro_env(monkeypatch)
    monkeypatch.setenv("DEMOCREATE_KOKORO_DIR", str(tmp_path))  # empty dir
    assert _kokoro_model_paths() is None


def test_model_paths_from_env(monkeypatch, tmp_path: Path) -> None:
    model = tmp_path / "m.onnx"
    voices = tmp_path / "v.bin"
    model.write_bytes(b"x")
    voices.write_bytes(b"y")
    monkeypatch.setenv("KOKORO_MODEL_PATH", str(model))
    monkeypatch.setenv("KOKORO_VOICES_PATH", str(voices))
    assert _kokoro_model_paths() == (model, voices)


def test_model_paths_from_cache_names(monkeypatch, tmp_path: Path) -> None:
    _clear_kokoro_env(monkeypatch)
    (tmp_path / "kokoro-v1.0.onnx").write_bytes(b"x")
    (tmp_path / "voices-v1.0.bin").write_bytes(b"y")
    monkeypatch.setenv("DEMOCREATE_KOKORO_DIR", str(tmp_path))
    paths = _kokoro_model_paths()
    assert paths is not None
    assert paths[0].name == "kokoro-v1.0.onnx"
    assert paths[1].name == "voices-v1.0.bin"


def test_backend_unavailable_without_model(monkeypatch, tmp_path: Path) -> None:
    _clear_kokoro_env(monkeypatch)
    monkeypatch.setenv("DEMOCREATE_KOKORO_DIR", str(tmp_path))  # empty → no files
    with pytest.raises(BackendUnavailableError):
        KokoroTTSBackend()


def _kokoro_ready() -> bool:
    import importlib.util

    return (
        importlib.util.find_spec("kokoro_onnx") is not None
        and _kokoro_model_paths() is not None
    )


@pytest.mark.backend
@pytest.mark.skipif(not _kokoro_ready(), reason="kokoro-onnx + model files not present")
def test_kokoro_real_synthesis(tmp_path: Path) -> None:
    """A real neural synth produces a canonical, non-empty, measured WAV clip."""
    backend = KokoroTTSBackend(voice="af_heart")
    assert backend.is_available()
    out = tmp_path / "clip.wav"
    clip = backend.synthesize("DemoCreate speaks with a neural voice.", out)
    assert out.exists() and out.stat().st_size > 1000
    assert clip.duration_ms > 0
    assert clip.sample_rate == 22050


@pytest.mark.backend
@pytest.mark.skipif(not _kokoro_ready(), reason="kokoro-onnx + model files not present")
def test_kokoro_unknown_voice_falls_back(tmp_path: Path) -> None:
    """A system voice name (e.g. a demo's 'Samantha') must not crash Kokoro."""
    backend = KokoroTTSBackend(voice="af_heart")
    out = tmp_path / "clip.wav"
    clip = backend.synthesize("Fallback test.", out, voice="Samantha")
    assert out.exists() and clip.duration_ms > 0
