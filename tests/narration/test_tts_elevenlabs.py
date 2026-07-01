"""Tests for the ElevenLabs cloud-TTS backend.

Every test here runs with **no network and no API key**: the guard paths are
exercised by unsetting ``ELEVENLABS_API_KEY`` with ``monkeypatch.delenv`` and
never calling the real API, mirroring the sibling LectureCreate project. The real
synthesis path is thin and marked ``# pragma: no cover`` (it needs the package,
a key, and the network), so it is not exercised in CI. No mocks are used — only
``monkeypatch`` on the environment, per the project's no-mock contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.errors import BackendUnavailableError, DemoCreateError
from democreate.narration.tts import (
    _DEFAULT_SAMPLE_RATE,
    _ELEVENLABS_DEFAULT_MODEL,
    _ELEVENLABS_FORMAT_MAP,
    _ELEVENLABS_MODELS,
    ElevenLabsTTSBackend,
    _resolve_elevenlabs_voice_id,
    get_tts_backend,
)

# ---------------------------------------------------------------------------
# constructor + validation


def test_default_construction() -> None:
    b = ElevenLabsTTSBackend()
    assert b.name == "elevenlabs"
    assert b.voice_id  # defaults to a real stock voice id, never empty
    assert b.model == _ELEVENLABS_DEFAULT_MODEL
    assert b.sample_rate == _DEFAULT_SAMPLE_RATE
    assert b._output_format == f"wav_{_DEFAULT_SAMPLE_RATE}"


def test_model_alias_resolution() -> None:
    b = ElevenLabsTTSBackend(model="turbo_v2_5")
    assert b.model == _ELEVENLABS_MODELS["turbo_v2_5"]


def test_unknown_model_passthrough() -> None:
    b = ElevenLabsTTSBackend(model="custom-model-id")
    assert b.model == "custom-model-id"


def test_explicit_voice_id_kept() -> None:
    b = ElevenLabsTTSBackend(voice_id="abc123")
    assert b.voice_id == "abc123"


def test_invalid_sample_rate_raises() -> None:
    with pytest.raises(ValueError, match="unsupported sample_rate"):
        ElevenLabsTTSBackend(sample_rate=11025)


def test_valid_sample_rates() -> None:
    for rate in sorted(_ELEVENLABS_FORMAT_MAP):
        b = ElevenLabsTTSBackend(sample_rate=rate)
        assert b._output_format == f"wav_{rate}"


def test_custom_api_key_env_is_honored(monkeypatch) -> None:
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    monkeypatch.setenv("MY_EL_KEY", "sk_dummy")
    b = ElevenLabsTTSBackend(api_key_env="MY_EL_KEY")
    assert b._api_key() == "sk_dummy"


# ---------------------------------------------------------------------------
# availability — no network


def test_not_available_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    b = ElevenLabsTTSBackend()
    # Even if the elevenlabs package is installed, no key ⇒ not available.
    assert b.is_available() is False


def test_is_available_matches_dep_and_key(monkeypatch) -> None:
    from democreate.narration.tts import _dep_available

    monkeypatch.setenv("ELEVENLABS_API_KEY", "sk_test_dummy")
    b = ElevenLabsTTSBackend()
    assert b.is_available() is _dep_available("elevenlabs")


# ---------------------------------------------------------------------------
# synthesize guard — clear, typed error; no silent WAV, no network


def test_synthesize_raises_typed_error_without_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    b = ElevenLabsTTSBackend(voice_id="v1")
    out = tmp_path / "out.wav"
    # Missing package OR missing key both raise a DemoCreateError subclass —
    # never a generic Exception, and never a silently-written empty WAV.
    with pytest.raises((BackendUnavailableError, DemoCreateError)):
        b.synthesize("some narration text", out)
    assert not out.exists()  # no silent-WAV fallback on the failure path


def test_resolve_voice_id_treats_default_sentinel_as_no_override() -> None:
    """`Demo.voice`/chunk `voice` default to the literal "default" sentinel
    (schema.py) meaning "no override" for every backend. ElevenLabs must not
    forward it to the real API as a voice_id (regression: it 404s as
    voice_not_found — reproduced live via `democreate tour --tts elevenlabs`
    on 2026-07-01). Pure function, no network, no stand-ins."""
    assert _resolve_elevenlabs_voice_id("default", "configured-voice") == "configured-voice"


def test_resolve_voice_id_treats_empty_string_as_no_override() -> None:
    """An unset per-chunk voice override can also arrive as "" (not just the
    "default" sentinel) — RedTeam-found gap, 2026-07-01: the original fix only
    checked `== "default"` and would have forwarded "" to the real API."""
    assert _resolve_elevenlabs_voice_id("", "configured-voice") == "configured-voice"


def test_resolve_voice_id_treats_none_as_no_override() -> None:
    assert _resolve_elevenlabs_voice_id(None, "configured-voice") == "configured-voice"


def test_resolve_voice_id_keeps_explicit_override() -> None:
    assert _resolve_elevenlabs_voice_id("explicit-voice", "configured-voice") == "explicit-voice"


def test_synthesize_empty_text_writes_silence_without_network(
    tmp_path: Path, monkeypatch
) -> None:
    """Whitespace-only text short-circuits to a silent clip before any API/key check."""
    monkeypatch.delenv("ELEVENLABS_API_KEY", raising=False)
    b = ElevenLabsTTSBackend(voice_id="v1")
    out = tmp_path / "silent.wav"
    clip = b.synthesize("   ", out)
    assert out.exists() and out.stat().st_size > 0
    assert clip.duration_ms > 0
    assert clip.sample_rate == _DEFAULT_SAMPLE_RATE


# ---------------------------------------------------------------------------
# factory wiring


def test_factory_returns_elevenlabs_backend() -> None:
    b = get_tts_backend("elevenlabs")
    assert isinstance(b, ElevenLabsTTSBackend)


def test_factory_forwards_voice_id() -> None:
    b = get_tts_backend("elevenlabs", voice="v123")
    assert isinstance(b, ElevenLabsTTSBackend)
    assert b.voice_id == "v123"


def test_factory_unknown_backend_still_raises() -> None:
    with pytest.raises(ValueError, match="unknown TTS backend"):
        get_tts_backend("not-a-backend")


# ---------------------------------------------------------------------------
# format map coverage


def test_format_map_complete() -> None:
    assert _ELEVENLABS_FORMAT_MAP[22050] == "wav_22050"
    assert _ELEVENLABS_FORMAT_MAP[44100] == "wav_44100"
    assert len(_ELEVENLABS_FORMAT_MAP) == 7
