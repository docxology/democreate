"""Tests for the optional LLM narration backend (no network).

These tests exercise the pure payload builder, env-driven availability, config
resolution, and the guard that makes the network methods raise when no API key
is configured. No real HTTP calls are made.
"""

from __future__ import annotations

import pytest

from democreate.errors import BackendUnavailableError
from democreate.narration.llm import (
    LLMNarrator,
    build_chat_payload,
    get_narrator,
    llm_available,
)

_KEY_VARS = ("OPENAI_API_KEY", "DEMOCREATE_LLM_API_KEY")
_BASE_URL_VAR = "DEMOCREATE_LLM_BASE_URL"


@pytest.fixture(autouse=True)
def _clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no LLM env vars leak in from the host environment."""
    for var in (*_KEY_VARS, _BASE_URL_VAR):
        monkeypatch.delenv(var, raising=False)


def test_build_chat_payload_shape() -> None:
    messages = [
        {"role": "system", "content": "be brief"},
        {"role": "user", "content": "hello"},
    ]
    payload = build_chat_payload(messages, model="gpt-4o-mini", temperature=0.3)

    assert set(payload) >= {"model", "messages", "temperature"}
    assert payload["model"] == "gpt-4o-mini"
    assert payload["temperature"] == 0.3
    assert payload["messages"] == messages


def test_build_chat_payload_default_temperature() -> None:
    payload = build_chat_payload(
        [{"role": "user", "content": "x"}], model="m"
    )
    assert payload["temperature"] == 0.7


def test_build_chat_payload_copies_messages() -> None:
    messages = [{"role": "user", "content": "hi"}]
    payload = build_chat_payload(messages, model="m")
    payload["messages"][0]["content"] = "mutated"

    # The original input must be untouched (defensive copy).
    assert messages[0]["content"] == "hi"


def test_llm_available_false_when_unset() -> None:
    assert llm_available() is False


def test_llm_available_true_with_openai_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert llm_available() is True


def test_llm_available_true_with_democreate_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMOCREATE_LLM_API_KEY", "sk-test")
    assert llm_available() is True


def test_llm_available_false_when_key_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "")
    assert llm_available() is False


def test_constructor_builds_without_key() -> None:
    narrator = LLMNarrator()
    assert isinstance(narrator, LLMNarrator)
    assert narrator.api_key is None
    assert narrator.is_available() is False
    # Default base url, no trailing slash, correct endpoint.
    assert narrator.base_url == "https://api.openai.com/v1"
    assert narrator.endpoint == "https://api.openai.com/v1/chat/completions"
    assert narrator.model == "gpt-4o-mini"


def test_constructor_resolves_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    narrator = LLMNarrator()
    assert narrator.api_key == "sk-env"
    assert narrator.is_available() is True


def test_constructor_arg_key_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")
    narrator = LLMNarrator(api_key="sk-arg")
    assert narrator.api_key == "sk-arg"


def test_base_url_resolves_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_BASE_URL_VAR, "https://proxy.example/v1/")
    narrator = LLMNarrator()
    # Trailing slash stripped.
    assert narrator.base_url == "https://proxy.example/v1"
    assert narrator.endpoint == "https://proxy.example/v1/chat/completions"


def test_base_url_arg_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(_BASE_URL_VAR, "https://env.example/v1")
    narrator = LLMNarrator(base_url="https://arg.example/v1")
    assert narrator.base_url == "https://arg.example/v1"


def test_narrate_raises_backend_unavailable_without_key() -> None:
    narrator = LLMNarrator()
    with pytest.raises(BackendUnavailableError) as excinfo:
        narrator.narrate("describe this scene")
    assert excinfo.value.backend == "llm"
    assert excinfo.value.extra == "llm"


def test_rewrite_chunks_raises_backend_unavailable_without_key() -> None:
    narrator = LLMNarrator()
    with pytest.raises(BackendUnavailableError):
        narrator.rewrite_chunks(["a", "b"])


def test_get_narrator_returns_configured_instance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DEMOCREATE_LLM_API_KEY", "sk-x")
    narrator = get_narrator(model="custom-model", temperature=0.1)
    assert isinstance(narrator, LLMNarrator)
    assert narrator.model == "custom-model"
    assert narrator.temperature == 0.1
    assert narrator.api_key == "sk-x"
