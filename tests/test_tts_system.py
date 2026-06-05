"""Tests for system TTS + the audio-measurement primitive (narration.tts)."""

from __future__ import annotations

import shutil
import wave
from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError, DemoCreateError
from democreate.narration.tts import (
    SystemTTSBackend,
    _system_tts_command,
    get_tts_backend,
    measure_wav_duration_ms,
)


def _mkwav(path: Path, ms: int) -> None:
    n = int(22050 * ms / 1000)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"\x00\x00" * n)


def test_measure_wav_duration(tmp_path: Path) -> None:
    _mkwav(tmp_path / "a.wav", 750)
    assert abs(measure_wav_duration_ms(tmp_path / "a.wav") - 750) < 5


def test_measure_wav_duration_rejects_non_wav(tmp_path: Path) -> None:
    bad = tmp_path / "x.wav"
    bad.write_text("not a wav", encoding="utf-8")
    with pytest.raises(DemoCreateError):
        measure_wav_duration_ms(bad)


def test_get_tts_backend_system_or_unavailable() -> None:
    if _system_tts_command() is not None:
        backend = get_tts_backend("system")
        assert isinstance(backend, SystemTTSBackend)
        assert backend.is_available()
    else:  # pragma: no cover - depends on host
        with pytest.raises(BackendUnavailableError):
            get_tts_backend("system")


def test_unknown_backend_name_raises() -> None:
    with pytest.raises(ValueError, match="unknown TTS backend"):
        get_tts_backend("nope")


@pytest.mark.skipif(
    _system_tts_command() is None, reason="no system TTS binary on this host"
)
@pytest.mark.backend
def test_system_tts_speaks_real_audio(tmp_path: Path) -> None:
    """Integration: synthesize real speech and assert non-trivial measured duration.

    Skipped automatically when neither ``say`` nor ``espeak`` is present. Requires
    a transcoder (ffmpeg/afconvert) too; tolerate its absence by skipping.
    """
    if not (shutil.which("ffmpeg") or shutil.which("afconvert")):  # pragma: no cover
        pytest.skip("no audio transcoder available")
    backend = SystemTTSBackend()
    out = tmp_path / "speech.wav"
    clip = backend.synthesize(
        "DemoCreate turns a declarative demo into a real video.", out
    )
    assert out.exists() and out.stat().st_size > 1000
    # real speech of ~9 words should be well over half a second
    assert clip.duration_ms > 500
    assert abs(measure_wav_duration_ms(out) - clip.duration_ms) < 5


@pytest.mark.skipif(
    _system_tts_command() is None, reason="no system TTS binary on this host"
)
@pytest.mark.backend
def test_system_tts_empty_text_is_silent_beat(tmp_path: Path) -> None:
    out = tmp_path / "empty.wav"
    clip = SystemTTSBackend().synthesize("   ", out)
    assert out.exists()
    assert clip.duration_ms >= 300  # minimum beat from silent fallback
