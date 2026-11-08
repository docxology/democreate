# Documentation: choose a workflow, reference or evidence record

DemoCreate's core builds silent WAVs, synthetic frames, captions, transcripts and
a timed HTML image preview. The HTML is **not a synthesized-audio player**.
Voiced MP4, real capture and PDF ingestion have separate prerequisites; not every
subsystem has an abstract backend or a core replacement for external tools.

## Start with the job you want to do

| Purpose | Authoritative guide |
|---|---|
| Install, author a starter and build an offline preview | [Quickstart](quickstart.md) |
| Copy a bounded workflow: tour, paper, vertical cut, GIF, chapters | [Recipes](recipes.md) |
| Understand authored input, staged assets and scheduled output | [Architecture and determinism boundaries](architecture.md) |
| Prepare paper text, figures and a codebase | [Paper workflow](paper.md) |
| Translate narration/subtitles with an explicit local server | [Localization](translation.md) |
| Resolve missing tools, models or malformed inputs | [Troubleshooting](troubleshooting.md) |

## Consult one reference per contract

| Contract | Reference |
|---|---|
| Commands, flags, defaults, image authority and resolved bundles | [CLI](cli.md) |
| Demo → Scene → Chunk → Action, measured versus authored timing | [Schema 1.1](schema.md) |
| Theme, AudioConfig, VideoConfig, MetadataConfig and CLI precedence | [Configuration](config.md) |
| Implemented backends versus unwired slots; extras and runtime prerequisites | [Backends](backends.md) |
| Scheduled animation, static holds, captions, quantization and encode limits | [Video](video.md) |
| WAV assembly, pauses, normalization and fades | [Audio](audio.md) |
| Visible/container metadata and unsigned poster digest limitations | [Provenance](provenance.md) |
| Public library signatures generated from source | [API reference](api.md) — generated, not hand-edited |

Procedural guides link to these references rather than redefining their option
and default tables. Source and native CLI help remain the behavioral authority.
The package floor is **Python 3.11.5 / Pillow 13**, the core pin **Python 3.15**;
Kokoro is implemented but needs a compatible voice environment (recorded as
Python 3.14), packages and models. Whisper/Chatterbox/Manim and the legacy MoviePy
compositor are unwired. Dependency presence does not certify readiness.

## Separate illustrations, identified observations and release gates

- [Synthetic gallery](gallery.md): authored renderer/diagram examples, **not**
  decoded-media or empirical paper evidence; [generator assets](_gallery/README.md).
- [Video recipes and identities](videos.md): the refreshed current-source Kokoro
  render, identified earlier observations and optional external paper inputs.
  An ignored output path alone does not identify a video.
- [Immutable 0.8.0 engineering receipt](release-0.8.0.md), backed by
  [structured source-bound evidence](../data/release-0.8.0.json): observed history,
  not proof of the subsequently edited tree.
- [Visual/documentation refresh receipt](visual-refresh.md), backed by
  [fresh native engineering evidence](../data/visual-refresh-2026-11-08.json):
  package-byte binding, regression proof and the canonical reproduction.
- [Manuscript](manuscript/README.md): scientific framing, figures and evaluation
  limits. Measured clip windows are not acoustic word onsets.
- [Testing policy](testing_philosophy.md): no mocked core computation, lazy heavy
  imports and the unchanged **≥90% core coverage gate**, not a current result.

Publication still requires ≥30 independently annotated voiced demos (≥10 per
mode), with both pooled absolute-event-error median and median of demo-level
absolute-error medians ≤120 ms. The candidate remains unpublished. Operator-
controlled write-class enablement and exact reviewed-plan confirmation are
separate requirements; neither waives the study. Unsigned content hashes do not
authenticate authors, images or video.

## Navigate source and contributor guidance

The [source map](../src/democreate/README.md) links each subsystem's local
README/AGENTS pair. [Scripts](../scripts/README.md) cover standalone front doors,
API generation, benchmarking and manuscript tooling. [Root AGENTS](../AGENTS.md)
and [documentation guidance](AGENTS.md) define contribution invariants;
[CHANGELOG](../CHANGELOG.md), [TODO](../TODO.md) and [tasks](../tasks.yaml) track
changes and work, not substitute media evidence.
