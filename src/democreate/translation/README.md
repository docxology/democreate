# `democreate.translation`

Localizes a demo so a render can carry **audio in one language and subtitles in
another** (e.g. English audio with Russian subtitles, or vice-versa). Translation
is **local and configurable** — it drives an `ollama` server over its HTTP API
with no pip dependency — and sits behind an interface with a pure, deterministic
default so the whole path is import-safe and offline-testable.

## Modules

| Module | Responsibility |
|--------|----------------|
| `translator.py` | The `Translator` interface + backends, language helpers, and the pure demo/caption transforms. |
| `localize.py` | Orchestration: render one (or a batch of) audio/subtitle language pairs to MP4 + subtitle sidecars. |

## How it works

The narration is translated to the **audio** language and synthesized — that drives
the audio, the frames, and the timing. The **subtitle** track is translated
separately against that *same* (audio-derived) timing, so two different languages
stay in lock-step. The output filename encodes both, e.g.
`demo-audio_en-subs_ru.mp4`.

> Subtitles work for any language (text only). *Audio* in a language needs a TTS
> voice for it — Kokoro's languages (en/es/fr/it/ja/zh/hi/pt) or an installed
> system voice. So "English audio + Russian subtitles" works out of the box;
> Russian *audio* needs a Russian voice present.

## Public API

### `translator.py`
- `Translator` (ABC): `name`, `is_available()`, `translate(text, *, source, target)`.
- `IdentityTranslator` — **default**, a deterministic no-op (returns text unchanged).
- `OllamaTranslator(model="smollm2", host="http://localhost:11434")` — guarded local
  backend; raises `BackendUnavailableError` from `translate` when the server is down.
- `get_translator(name="auto") -> Translator` — `auto`/`identity`/`none` → no-op;
  `ollama` → `OllamaTranslator`.
- `LanguageConfig(source, audio, subtitle)` — with `.tag()` → `audio_en-subs_ru`.
- `translate_demo(demo, translator, *, source, target) -> Demo` — pure copy with
  translated chunk narration (structure/ids/actions preserved).
- `localized_captions(timed_demo, translator, *, source, target, fmt) -> str` —
  subtitle text in `target` against the demo's existing (synced) timing.

### `localize.py`
- `localize_render(demo, workspace, *, languages, translator, …) -> LocalizedResult`.
- `localize_batch(demo, workspace, *, pairs=[(audio, subtitle), …], …) -> list[LocalizedResult]`
  — one video per pair; a failing pair is isolated, not fatal.

## CLI

```bash
# English audio (Kokoro) + Russian subtitles (ollama), one video
democreate localize demo.json --audio-lang en --subtitle-lang ru --model lfm2.5

# a batch of combinations
democreate localize demo.json --pairs "en:ru,ru:en,en:es" --model lfm2.5
```

## Optional backend

| Backend | Dependency | Notes |
|---------|-----------|-------|
| `OllamaTranslator` | a running `ollama` server (no pip dep) | `ollama serve` + `ollama pull <model>` |
