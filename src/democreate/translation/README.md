# `democreate.translation`: explicit language transforms and localized media

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
separately against resolved audio-language clip windows; that shared nominal
timebase is not an acoustic-alignment or translation-quality proof. The output
filename encodes both, e.g. `demo-audio_en-subs_ru.mp4`.

> A subtitle language needs appropriate glyph coverage and reviewed model output;
> audio additionally needs a suitable TTS voice. English audio with Russian
> subtitles is a provisioned workflow, not an out-of-box core result. Russian
> audio requires a suitable installed voice; Kokoro has no Russian language map.

## Public API

### `translator.py`
- `Translator` (ABC): `name`, `is_available()`, `translate(text, *, source, target)`.
- `IdentityTranslator` — **default**, a deterministic no-op (returns text unchanged).
- `OllamaTranslator(model="smollm2", host="http://localhost:11434")` — guarded local
  backend; raises `BackendUnavailableError` from `translate` when the server is down.
- `get_translator(name="auto") -> Translator` — `auto`/`identity`/`none` → no-op;
  `ollama` → `OllamaTranslator`.
- `LanguageConfig(source, audio, subtitle)` — with `.tag()` → `audio_en-subs_ru`.
- `translate_demo(demo, translator, *, source, target) -> Demo` — translated
  narration in a copy (structure/ids/actions preserved); same-language requests
  return the untouched input.
- `localized_captions(demo, translator, *, source, target, fmt, timing_demo=None) -> str`
  — source-derived subtitle text using the selected timing Demo's clip windows;
  neither input is mutated. Use `PipelineResult.demo` for measured, padded timing.

### `localize.py`
- `localize_render(demo, workspace, *, languages, translator, …) -> LocalizedResult`.
- `localize_batch(demo, workspace, *, pairs=[(audio, subtitle), …], …) -> list[LocalizedResult]`
  — one video per pair; a failing pair is isolated, not fatal.
  Language-specific default voice ids apply only to Kokoro. A blank system voice
  uses the native OS default. An explicit `voice` (or configured audio voice)
  supplies the owned Pipeline Demo's default; per-chunk casting still wins.
  Same-language borrowed inputs and caller configuration remain unchanged.
  Library configuration does not replace authored Demo geometry. CLI
  `--resolution` explicitly replaces it; omitting the option preserves it.

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

CLI defaults are Ollama and Kokoro, whereas the library translator default is
identity. Both real server/model and voice/runtime prerequisites must be
provisioned explicitly. See [localization guide](../../../docs/translation.md),
[CLI defaults](../../../docs/cli.md#localize) and [backends](../../../docs/backends.md).
