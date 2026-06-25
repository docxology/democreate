"""Translators and language helpers for localized demos.

A :class:`Translator` maps narration text from a source language to a target
language. The default :class:`IdentityTranslator` is pure and deterministic (a
no-op — it returns the text unchanged), so the whole localization path is
import-safe and testable with no server. :class:`OllamaTranslator` is a guarded
backend that drives a local `ollama` server over its HTTP API using only the
standard library (``urllib``) — no pip dependency.

Localizing a demo is a pure transform on the spine: :func:`translate_demo`
returns a copy whose chunk narration is translated; :func:`localized_captions`
emits subtitle text in a target language against the *existing* (audio-derived)
timing, so audio in one language and subtitles in another stay in lock-step.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from .._logging import get_logger
from ..errors import BackendUnavailableError
from ..schema import Chunk, Demo, Scene

__all__ = [
    "LANGUAGES",
    "language_name",
    "LanguageConfig",
    "Translator",
    "IdentityTranslator",
    "OllamaTranslator",
    "get_translator",
    "translate_demo",
    "localized_captions",
]

logger = get_logger(__name__)

# Common language codes → display name (for prompts, filenames are the code).
LANGUAGES: dict[str, str] = {
    "en": "English",
    "ru": "Russian",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "hi": "Hindi",
    "ar": "Arabic",
    "nl": "Dutch",
    "pl": "Polish",
    "uk": "Ukrainian",
    "tr": "Turkish",
}


def _clean_llm_output(text: str) -> str:
    """Strip reasoning blocks / wrappers from a model response.

    Reasoning models (e.g. ``lfm2.5``) emit a ``<think>…</think>`` chain-of-thought
    before the answer; keep only what follows the final ``</think>``, remove any
    remaining think blocks, and strip surrounding quotes/whitespace so only the
    clean translation reaches the subtitle/voice.
    """
    import re

    if "</think>" in text:
        text = text.rsplit("</think>", 1)[1]
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # An unclosed think block (truncated) — drop everything from it onward.
    if "<think>" in text:
        text = text.split("<think>", 1)[0]
    return text.strip().strip('"').strip()


def language_name(code: str) -> str:
    """Return a human language name for a code (falls back to the code itself)."""
    return LANGUAGES.get(code.lower().split("-")[0], code)


@dataclass
class LanguageConfig:
    """Which language the audio is spoken in and which the subtitles are written in.

    Attributes:
        source: The language the demo's narration is authored in.
        audio: The spoken (TTS) language. When it differs from ``source`` the
            narration is translated before synthesis (a TTS voice for that language
            must exist — Kokoro langs or an installed system voice).
        subtitle: The subtitle-track language (always available — text only).
    """

    source: str = "en"
    audio: str = "en"
    subtitle: str = "en"

    def tag(self) -> str:
        """A filename tag making the audio/subtitle languages explicit."""
        return f"audio_{self.audio}-subs_{self.subtitle}"


class Translator:
    """Abstract translator: source-language text → target-language text."""

    name: str = "abstract"

    def is_available(self) -> bool:
        """Whether this translator can run."""
        return True

    def translate(self, text: str, *, source: str, target: str) -> str:
        """Translate ``text`` from ``source`` to ``target``."""
        raise NotImplementedError


class IdentityTranslator(Translator):
    """Deterministic default: returns text unchanged (a no-op translation)."""

    name = "identity"

    def translate(self, text: str, *, source: str, target: str) -> str:
        """Return ``text`` unchanged."""
        return text


class OllamaTranslator(Translator):
    """Translate via a local `ollama` server (guarded; needs a running server).

    Args:
        model: The ollama model tag to use (e.g. ``"smollm2"``, ``"lfm2.5"``).
        host: The ollama base URL.
        timeout: Per-request timeout in seconds.

    Raises:
        BackendUnavailableError: From :meth:`translate` if the server is
            unreachable. Construction is cheap and never blocks.
    """

    name = "ollama"

    def __init__(
        self,
        *,
        model: str = "smollm2",
        host: str = "http://localhost:11434",
        timeout: int = 180,
    ) -> None:
        self.model = model
        self.host = host.rstrip("/")
        self.timeout = timeout

    def is_available(self) -> bool:
        """Whether the ollama server answers its tags endpoint."""
        try:
            with urllib.request.urlopen(f"{self.host}/api/tags", timeout=5) as resp:
                return resp.status == 200
        except (urllib.error.URLError, OSError, ValueError):  # pragma: no cover - host-dependent
            return False

    def translate(self, text: str, *, source: str, target: str) -> str:
        """Translate ``text`` via ollama; passthrough on empty or same-language."""
        if not text.strip() or source == target:
            return text
        prompt = (
            f"Translate the text below from {language_name(source)} to "
            f"{language_name(target)}. Preserve technical terms, code identifiers, "
            "and product names verbatim. Output ONLY the translation — no notes, no "
            "quotes, no preamble.\n\nTEXT:\n" + text
        )
        payload = json.dumps(
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.0},
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, OSError, ValueError) as exc:
            raise BackendUnavailableError(
                f"ollama server at {self.host} (model {self.model!r}) — "
                "start it with `ollama serve` and `ollama pull <model>`"
            ) from exc
        out = _clean_llm_output(str(data.get("response", "")))
        return out or text


def get_translator(name: str = "auto", **kwargs: object) -> Translator:
    """Return a translator by name.

    Args:
        name: ``"auto"``/``"identity"``/``"none"`` → the no-op default;
            ``"ollama"`` → :class:`OllamaTranslator`.
        **kwargs: Forwarded to the backend constructor (e.g. ``model``, ``host``).

    Raises:
        ValueError: If ``name`` is not recognized.
    """
    key = name.lower()
    if key in ("auto", "identity", "none"):
        return IdentityTranslator()
    if key == "ollama":
        return OllamaTranslator(**kwargs)  # type: ignore[arg-type]
    raise ValueError(f"unknown translator {name!r}; choose identity|ollama")


def _translate_chunk_text(
    translator: Translator, text: str, *, source: str, target: str, cache: dict[str, str]
) -> str:
    """Translate one chunk's text, memoized so identical lines hit the model once."""
    if not text.strip() or source == target:
        return text
    if text not in cache:
        cache[text] = translator.translate(text, source=source, target=target)
    return cache[text]


def translate_demo(
    demo: Demo, translator: Translator, *, source: str, target: str
) -> Demo:
    """Return a copy of ``demo`` with every chunk's narration translated.

    The structure (scenes, actions, ids, geometry) is preserved; only chunk
    ``text`` changes. ``trigger_word`` anchors are left as-is (they reference the
    source wording); when they no longer match the translated text the sync engine
    falls back to chunk-start timing, which keeps the render correct.

    A no-op (returns ``demo`` unchanged) when ``source == target``.
    """
    if source == target:
        return demo
    cache: dict[str, str] = {}
    new_scenes: list[Scene] = []
    for scene in demo.scenes:
        new_chunks = [
            Chunk(
                id=c.id,
                text=_translate_chunk_text(
                    translator, c.text, source=source, target=target, cache=cache
                ),
                actions=list(c.actions),
                voice=c.voice,
            )
            for c in scene.chunks
        ]
        new_scenes.append(
            Scene(id=scene.id, title=scene.title, kind=scene.kind,
                  chunks=new_chunks, context=dict(scene.context))
        )
    return Demo(
        title=demo.title,
        scenes=new_scenes,
        width=demo.width,
        height=demo.height,
        fps=demo.fps,
        voice=demo.voice,
        metadata={**demo.metadata, "language": target},
    )


def localized_captions(
    demo: Demo,
    translator: Translator,
    *,
    source: str,
    target: str,
    fmt: str = "srt",
    timing_demo: Demo | None = None,
) -> str:
    """Emit subtitles in ``target`` from the **source** demo, with audio timing.

    ``demo`` must carry the *source-language* narration (the original), so the
    subtitle text is translated source→target — never from an already-translated
    audio demo (which would mislabel one language as another). ``timing_demo``
    (default: ``demo``) supplies each chunk's ``start_ms`` (from real audio), so a
    subtitle track in one language lines up with audio in another.
    """
    from ..assembly import captions as captions_mod

    timing = timing_demo or demo
    subtitle_demo = translate_demo(demo, translator, source=source, target=target)
    # Carry the (audio-derived) timing across (translate_demo rebuilds chunks fresh).
    for time_chunk, sub_chunk in zip(
        timing.iter_chunks(), subtitle_demo.iter_chunks(), strict=True
    ):
        sub_chunk.start_ms = time_chunk.start_ms
    emitters = {"srt": captions_mod.to_srt, "vtt": captions_mod.to_vtt}
    if fmt not in emitters:
        raise ValueError(f"unknown caption format {fmt!r}; choose srt|vtt")
    return emitters[fmt](subtitle_demo)
