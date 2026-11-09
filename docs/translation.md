# Localization: separate narration and subtitle languages

The library translates authored narration for audio and independently translates
the original text for subtitles. A TTS voice must support the **audio** language;
subtitle text support is not a promise of font coverage or translation quality.
The library default `IdentityTranslator` is a deterministic **no-op**, while the
CLI defaults to **Ollama** and **Kokoro**. Voice selection is blank by default:
configured/authored choices are retained, then Kokoro's language-specific fallback
applies (English: `af_heart`). Neither server nor voice models ship with core.

## Prepare the selected server and voice

Use the [backend prerequisites](backends.md): Kokoro needs compatible packages,
runtime and model/voices (the recorded voice environment used Python 3.14), and
MP4 needs ffmpeg/ffprobe. Ollama needs a running server and an acquired model
whose tag matches `--model`. Reachability does not prove usable model output.

With those prerequisites and an authored `demo.json`:

```bash
democreate localize demo.json --audio-lang en --subtitle-lang ru --model smollm2
```

The CLI rejects an unreachable default Ollama endpoint; it does not silently
pretend translation succeeded. `--translator identity` deliberately leaves words
unchanged even when target language labels differ.

## How the language tracks are constructed

1. Read the authored Demo; preserve scene IDs and virtual actions.
2. Translate narration from `--source-lang` into `--audio-lang`, then synthesize
   that text. Action trigger words also need review after translation.
3. Translate the original narration separately into `--subtitle-lang`; align
   cues to the resolved audio-language clip windows rather than re-estimating
   from subtitle length. These are clip windows, not acoustic onset annotations.
4. Write `<title-slug>-audio_<a>-subs_<s>.mp4` in `video/` and matching full-tag
   `.srt`/`.vtt` files in `captions/`. `--burn` additionally burns the selected
   subtitle track; it does not replace the sidecars. Burning needs libass.

Inspect translated content, cue timing and encoded output. Identity translation,
media-energy checks and heuristic word timing do not validate language quality
or semantic equivalence.

Explicit/configured voice defaults are applied to the pipeline's owned Demo;
per-chunk casting remains higher precedence and borrowed same-language inputs
are unchanged. A blank system voice can use the native default rather than an
unrelated Kokoro ID. CLI `--resolution` explicitly resizes the loaded Demo;
omission preserves authored geometry. Library config alone does not resize it.

## Select a language pair or batch

```bash
# A single English voice track with Russian subtitle text
democreate localize demo.json --audio-lang en --subtitle-lang ru --model smollm2

# The same English audio with two independently translated subtitle languages
democreate localize demo.json --pairs "en:ru,en:es" --model smollm2

# Explicit no-translation control, using a usable native voice
democreate localize demo.json --audio-lang en --subtitle-lang en \
  --translator identity --tts system --voice ""
```

A batch uses one configured voice; do not assume arbitrary audio-language pairs
work with it. Russian audio, for example, requires an installed suitable system
voice because Kokoro's language map does not include Russian. See the
[CLI option/default table](cli.md#localize) for source language, server host,
asset-root, theme, resolution and failure exit behavior.

## Library translator contract

```python
from democreate.translation import IdentityTranslator, OllamaTranslator

identity = IdentityTranslator()
assert identity.translate("Hello", source="en", target="es") == "Hello"

# Explicit server operation; requires the selected model to be provisioned.
translator = OllamaTranslator(model="smollm2", host="http://localhost:11434")
translated = translator.translate("Hello", source="en", target="es")
```

`translate_demo` returns translated content in a copy, or the untouched input for
same-language requests. `localized_captions` does not mutate either Demo and can
receive a distinct resolved `timing_demo`. `localize_render` and `localize_batch`
orchestrate media outputs. See the [source guide](../src/democreate/translation/README.md),
[API](api.md), and [testing policy](testing_philosophy.md). The `OllamaTranslator`
uses stdlib HTTP and can target a configured remote host; “local” describes the
default endpoint, not a network-isolation guarantee.
