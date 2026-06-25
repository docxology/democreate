"""Translation subsystem: localize a demo's narration and subtitles.

Translates a :class:`~democreate.schema.Demo`'s narration so a render can carry
**audio in one language and subtitles in another** (e.g. English audio with
Russian subtitles, or vice-versa). Every translator sits behind the
:class:`~democreate.translation.translator.Translator` interface with a pure,
deterministic default (:class:`IdentityTranslator`, a no-op) so the package stays
import-safe and offline-testable; :class:`OllamaTranslator` is a guarded local
backend driving an `ollama` server.

The render orchestration lives in :mod:`democreate.translation.localize`.
"""

from __future__ import annotations

from .localize import LocalizedResult, localize_batch, localize_render
from .translator import (
    LANGUAGES,
    IdentityTranslator,
    LanguageConfig,
    OllamaTranslator,
    Translator,
    get_translator,
    language_name,
    localized_captions,
    translate_demo,
)

__all__ = [
    "Translator",
    "IdentityTranslator",
    "OllamaTranslator",
    "get_translator",
    "LanguageConfig",
    "LANGUAGES",
    "language_name",
    "translate_demo",
    "localized_captions",
    "localize_render",
    "localize_batch",
    "LocalizedResult",
]
