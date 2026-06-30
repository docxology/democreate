# Translation and localization

DemoCreate can produce videos with narration in one language and subtitles in another via the `democreate.translation` subsystem (added in v0.7.0).

## Quick start

```bash
# Translate an existing demo to Spanish audio + English subtitles
democreate localize demo.yaml --audio-lang es --subtitle-lang en

# Requires a running Ollama server (default: http://localhost:11434)
# Falls back to no-op (identity) translation when Ollama is unavailable.
```

## How it works

The `translation` subsystem wraps the narration pipeline with a configurable translation step:

1. **Narration generation** — script is generated in the source language (default: English).
2. **Translation** — each narration chunk is passed through `democreate.translation.Translator`, which by default calls a local `ollama` model. When `ollama` is unreachable the `NoopTranslator` (identity) is used, so renders always succeed.
3. **TTS synthesis** — translated text is synthesized with the target-language TTS backend.
4. **Subtitle track** — the original-language narration is burned in as SRT subtitles via ffmpeg.

## Configuration

In a demo YAML:

```yaml
translation:
  audio_lang: es          # ISO 639-1 language code for TTS
  subtitle_lang: en       # ISO 639-1 language code for subtitle track
  model: llama3           # ollama model to use for translation
  ollama_url: http://localhost:11434
```

## Backend API

```python
from democreate.translation import Translator, NoopTranslator, OllamaTranslator

# No-op (identity) — always available
t = NoopTranslator()
assert t.translate("Hello", target_lang="es") == "Hello"

# Ollama — requires a running server
t = OllamaTranslator(model="llama3", base_url="http://localhost:11434")
translated = t.translate("Hello, world.", target_lang="es")
```

## Supported languages

Any language supported by the configured ollama model. The TTS backend must also support the target language; `kokoro-onnx` covers English, Spanish, French, German, Japanese, Korean, and Chinese out of the box.

## Testing

The translation subsystem has a no-dependency test suite in `tests/translation/`:

```bash
uv run pytest tests/translation/ -v
```

Tests use `NoopTranslator` by default and do not require a running ollama server.
