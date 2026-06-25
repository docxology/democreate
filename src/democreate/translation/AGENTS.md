# AGENTS — `democreate.translation`

Guidance for agents editing this subsystem. Read alongside `README.md`.

## What this subsystem is

The localization layer: translate a demo's narration so a render carries audio in
one language and subtitles in another. It consumes the spine (`Demo/Scene/Chunk`)
and emits a translated `Demo` (for audio) and subtitle text against an existing
timing (for subtitles); it never redefines spine types.

## Hard rules

1. **Deterministic default, always.** `IdentityTranslator` (the default from
   `get_translator`) is a pure no-op — it must need no server and no network, so
   the whole localization path is import-safe and testable. `translate_demo` /
   `localized_captions` are pure transforms over the spine.
2. **No top-level heavy imports / no pip translation dep.** `OllamaTranslator`
   talks to the server with the stdlib `urllib` only. A missing/unreachable server
   raises `BackendUnavailableError` from `translate` (never at import or
   construction). Mark unrunnable real-server paths `# pragma: no cover` only where
   they cannot run offline.
3. **Audio vs subtitles.** Subtitles are text and work for any language. *Audio*
   in a language requires a TTS voice for it (Kokoro langs or an installed system
   voice) — do not claim arbitrary audio languages.
4. **Timing stays audio-derived.** Subtitles are generated against the synced
   (audio-language) timing so the two languages line up; never re-time from the
   translated text.
5. **Scope.** Only edit files under `src/democreate/translation/` and
   `tests/translation/test_*.py`. Never touch the spine, the package-root
   `__init__.py`, `pyproject.toml`, or `conftest.py`.

## Verify before returning

```sh
.venv/bin/python -m pytest tests/translation/ -q
```

No mocks — use `IdentityTranslator` or a tiny real `Translator` subclass as a test
double, and test the unavailable backend against a closed local port (offline).
Keep ruff (line-length 88) and mypy clean.
