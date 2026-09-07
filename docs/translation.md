# Translation and localization

DemoCreate can produce videos with narration in one language and subtitles in another via the `democreate.translation` subsystem (added in v0.7.0).

## Quick start

```bash
# Translate an existing demo to Spanish audio + English subtitles
democreate localize demo.yaml --audio-lang es --subtitle-lang en

# Requires a running Ollama server (default: http://localhost:11434).
# The command exits with an actionable error when Ollama is unreachable —
# pass --translator identity to render without translation (no-op).
```

## How it works

The `translation` subsystem wraps the narration pipeline with a configurable translation step:

1. **Narration generation** — script is generated in the source language (default: English).
2. **Translation** — each narration chunk is passed through a
   `democreate.translation.Translator`. The CLI defaults to `--translator ollama`
   (a local model); `--translator identity` selects the deterministic no-op
   (`IdentityTranslator`), which is also the library-level default.
3. **TTS synthesis** — translated text is synthesized with the target-language TTS backend.
4. **Subtitle track** — the original-language narration is written as
   `.srt`/`.vtt` sidecar files next to the video (`--burn` burns them into the
   picture instead).

## Configuration

Localization is configured on the `democreate localize` command line (the demo
schema has no `translation:` block):

```bash
# --audio-lang    ISO 639-1 code for the spoken (TTS) track
# --subtitle-lang ISO 639-1 code for the subtitle track
# --model         ollama model tag used for translation
# --host          ollama host (default: http://localhost:11434)
democreate localize demo.yaml --audio-lang es --subtitle-lang en --model llama3
```

## Backend API

```python
from democreate.translation import IdentityTranslator, OllamaTranslator, Translator

# No-op (identity) — always available, the library-level default
t = IdentityTranslator()
assert t.translate("Hello", source="en", target="es") == "Hello"

# Ollama — requires a running server
t = OllamaTranslator(model="llama3", host="http://localhost:11434")
translated = t.translate("Hello, world.", source="en", target="es")
```

## Supported languages

Any language supported by the configured ollama model. The TTS backend must also support the target language; `kokoro-onnx` covers English, Spanish, French, German, Japanese, Korean, and Chinese out of the box.

## Testing

The translation subsystem has a no-dependency test suite in `tests/translation/`:

```bash
uv run pytest tests/translation/ -v
```

Tests use `IdentityTranslator` by default and do not require a running ollama server.
