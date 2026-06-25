"""Tests for the translation subsystem.

No mocking framework: the deterministic default (:class:`IdentityTranslator`) and a
tiny real test-double translator exercise the pure transforms; the ollama backend's
unavailable path is checked against a closed local port (a real failure, no network
and no server). The heavy synthesis/render path is covered by the CLI/integration.
"""

from __future__ import annotations

from democreate.errors import BackendUnavailableError
from democreate.schema import Action, ActionType, Chunk, Demo, Scene
from democreate.translation import (
    LanguageConfig,
    OllamaTranslator,
    Translator,
    get_translator,
    language_name,
    localized_captions,
    translate_demo,
)


class _UpperTranslator(Translator):
    """A real (non-mock) test double: upper-cases the text as the 'translation'."""

    name = "upper"

    def translate(self, text: str, *, source: str, target: str) -> str:
        return text.upper()


def _demo() -> Demo:
    scene = Scene(id="s1", title="Intro")
    scene.chunks.append(
        Chunk(
            id="c1",
            text="Hello world.",
            actions=[Action(ActionType.OPEN_FILE, {"path": "x.py"}, trigger_word="hello")],
        )
    )
    return Demo(title="t", scenes=[scene])


def test_language_name_and_config_tag() -> None:
    assert language_name("ru") == "Russian"
    assert language_name("xx") == "xx"
    assert LanguageConfig(audio="en", subtitle="ru").tag() == "audio_en-subs_ru"


def test_identity_is_noop() -> None:
    idt = get_translator("identity")
    assert idt.translate("Hello.", source="en", target="ru") == "Hello."
    out = translate_demo(_demo(), idt, source="en", target="ru")
    assert out.iter_chunks()[0].text == "Hello world."


def test_translate_demo_same_language_returns_input() -> None:
    d = _demo()
    assert translate_demo(d, _UpperTranslator(), source="en", target="en") is d


def test_translate_demo_changes_text_preserves_structure() -> None:
    out = translate_demo(_demo(), _UpperTranslator(), source="en", target="ru")
    chunk = out.iter_chunks()[0]
    assert chunk.text == "HELLO WORLD."           # translated
    assert chunk.id == "c1"                         # id preserved
    assert chunk.actions[0].type == ActionType.OPEN_FILE  # actions preserved
    assert out.metadata["language"] == "ru"


def test_localized_captions_keeps_timing() -> None:
    demo = _demo()
    demo.iter_chunks()[0].start_ms = 5000  # pretend this came from real audio sync
    srt = localized_captions(demo, _UpperTranslator(), source="en", target="ru", fmt="srt")
    assert "HELLO WORLD." in srt          # subtitle text is translated
    assert "00:00:05" in srt              # timing carried from the synced demo


def test_get_translator_unknown_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        get_translator("googletrans")


def test_kokoro_audio_langs_map() -> None:
    from democreate.translation.localize import KOKORO_AUDIO_LANGS

    # Audio languages Kokoro can speak map to (lang code, a default voice).
    assert KOKORO_AUDIO_LANGS["en"] == ("en-us", "af_heart")
    assert KOKORO_AUDIO_LANGS["es"][1].startswith("e")  # a Spanish voice
    assert all(code and voice for code, voice in KOKORO_AUDIO_LANGS.values())


def test_clean_llm_output_strips_reasoning() -> None:
    from democreate.translation.translator import _clean_llm_output

    assert _clean_llm_output("<think>plan it</think>Привет мир.") == "Привет мир."
    assert _clean_llm_output("reasoning…</think>\nДобро пожаловать.") == "Добро пожаловать."
    assert _clean_llm_output('"Привет."') == "Привет."
    assert _clean_llm_output("plain text") == "plain text"
    # an unclosed (truncated) think block keeps the clean lead, drops the rest
    assert _clean_llm_output("Привет.<think>oops") == "Привет."


def test_ollama_unavailable_raises() -> None:
    # A closed local port: a real, offline failure — no network, no server.
    tr = OllamaTranslator(model="none", host="http://127.0.0.1:1", timeout=1)
    assert tr.is_available() is False
    import pytest

    with pytest.raises(BackendUnavailableError):
        tr.translate("Hello.", source="en", target="ru")


def test_ollama_passthrough_same_language() -> None:
    # No request is made when source == target, so an unreachable host is fine.
    tr = OllamaTranslator(host="http://127.0.0.1:1", timeout=1)
    assert tr.translate("Hello.", source="en", target="en") == "Hello."
