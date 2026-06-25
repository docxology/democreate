# API reference

> **Generated** by `scripts/generate_api_docs.py` from the live `democreate` package (version `0.7.0`). Do not edit by hand — regenerate with `.venv/bin/python scripts/generate_api_docs.py`.

This reference lists the public classes and functions of each documented module with the one-line summary of their docstring. For prose and examples, see the topic docs linked from [README.md](README.md); for the full contracts, read the source and its tests.

## Modules

- [`democreate`](#democreate)
- [`democreate.schema`](#democreateschema)
- [`democreate.config`](#democreateconfig)
- [`democreate.media`](#democreatemedia)
- [`democreate.pipeline`](#democreatepipeline)
- [`democreate.portfolio`](#democreateportfolio)
- [`democreate.project_paths`](#democreateproject_paths)
- [`democreate.errors`](#democreateerrors)
- [`democreate.cli`](#democreatecli)
- [`democreate.translation.translator`](#democreatetranslationtranslator)
- [`democreate.translation.localize`](#democreatetranslationlocalize)
- [`democreate.narration.script`](#democreatenarrationscript)
- [`democreate.narration.project_summary`](#democreatenarrationproject_summary)
- [`democreate.narration.tts`](#democreatenarrationtts)
- [`democreate.narration.sync`](#democreatenarrationsync)
- [`democreate.narration.llm`](#democreatenarrationllm)
- [`democreate.assembly.animator`](#democreateassemblyanimator)
- [`democreate.assembly.audio`](#democreateassemblyaudio)
- [`democreate.assembly.captions`](#democreateassemblycaptions)
- [`democreate.assembly.compositor`](#democreateassemblycompositor)
- [`democreate.capture.screen`](#democreatecapturescreen)
- [`democreate.animation.waveform`](#democreateanimationwaveform)
- [`democreate.animation.diagram`](#democreateanimationdiagram)
- [`democreate.animation.fonts`](#democreateanimationfonts)
- [`democreate.codebase.walker`](#democreatecodebasewalker)
- [`democreate.paper.extract`](#democreatepaperextract)
- [`democreate.paper.structure`](#democreatepaperstructure)
- [`democreate.paper.script`](#democreatepaperscript)
- [`democreate.paper.pdf`](#democreatepaperpdf)
- [`democreate.export.video`](#democreateexportvideo)
- [`democreate.export.verify`](#democreateexportverify)
- [`democreate.export.chapters`](#democreateexportchapters)
- [`democreate.export.poster`](#democreateexportposter)
- [`democreate.export.interactive`](#democreateexportinteractive)
- [`democreate.export.formats`](#democreateexportformats)

## `democreate` {#democreate}

DemoCreate — declarative, deterministic audio-visual demo generation.

### Classes

- **`Action`** *(dataclass)* — One typed event mutating the virtual environment.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain JSON-ready dict (omitting unset optional fields).
- **`ActionType`** — Every primitive change a demo can express against the virtual environment.
- **`BackendUnavailableError`** — A requested optional backend is not installed.
- **`CaptureError`** — A screen, browser, or terminal capture step failed.
- **`Chunk`** *(dataclass)* — A narration unit and the actions it triggers (VSpeak model).
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Estimate narration duration from word count at ``wpm`` words/minute.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
  - `word_count(self) -> 'int'` — Number of whitespace-delimited words in the narration.
- **`Demo`** *(dataclass)* — The top-level declarative artifact for a complete walkthrough.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Total estimated runtime from narration word counts.
  - `is_valid(self) -> 'bool'` — ``True`` iff :meth:`validate` returns no problems.
  - `iter_actions(self) -> 'list[Action]'` — Flat, ordered list of every action across all scenes/chunks.
  - `iter_chunks(self) -> 'list[Chunk]'` — Flat, ordered list of every chunk across all scenes.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
  - `to_json(self, *, indent: 'int | None' = 2) -> 'str'` — Serialize to a JSON string.
  - `to_yaml(self) -> 'str'` — Serialize to a YAML string. Requires PyYAML (a core dependency).
  - `validate(self) -> 'list[str]'` — Return a list of human-readable structural problems (empty == valid).
- **`DemoCreateError`** — Base class for every error DemoCreate raises deliberately.
- **`Pipeline`** — Configurable orchestrator over the DemoCreate subsystems.
  - `run(self, demo: 'Demo', workspace: 'Workspace | None' = None) -> 'PipelineResult'` — Render ``demo`` end-to-end, returning a :class:`PipelineResult`.
- **`PipelineResult`** *(dataclass)* — Paths and artifacts produced by a pipeline run.
  - `summary(self) -> 'dict[str, object]'` — A compact JSON-able summary of what was produced.
- **`RenderError`** — A frame, video, or export render step failed.
- **`Scene`** *(dataclass)* — A logical chapter of the demo with a single capture strategy.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Sum of chunk duration estimates.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
- **`SceneKind`** — The capture/render strategy a scene implies.
- **`SchemaValidationError`** — A :class:`~democreate.schema.Demo` failed structural validation.
- **`SyncError`** — Audio/action synchronization failed (e.g. transcription mismatch).
- **`WordTimestamp`** *(dataclass)* — A single word with millisecond start/end, produced by a transcriber.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
- **`Workspace`** *(dataclass)* — Resolved output locations for one demo build.
  - `clean(self) -> 'None'` — Remove the entire workspace root if it exists (idempotent).

### Functions

- **`build_demo(demo: 'Demo', workspace: 'Workspace | None' = None, **kwargs: 'object') -> 'PipelineResult'`** — Convenience one-shot: construct a default :class:`Pipeline` and run it.
- **`default_output_root() -> 'Path'`** — Return the conventional output root (``./output`` under the cwd).
- **`get_logger(name: 'str') -> 'logging.Logger'`** — Return a logger namespaced under ``democreate``.
- **`log_stage(stage: 'str', logger: 'logging.Logger | None' = None) -> 'Iterator[None]'`** — Time a named stage, logging start, success, and elapsed milliseconds.

## `democreate.schema` {#democreateschema}

Declarative demo schema — the deterministic spine of DemoCreate.

### Classes

- **`Action`** *(dataclass)* — One typed event mutating the virtual environment.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain JSON-ready dict (omitting unset optional fields).
- **`ActionType`** — Every primitive change a demo can express against the virtual environment.
- **`Chunk`** *(dataclass)* — A narration unit and the actions it triggers (VSpeak model).
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Estimate narration duration from word count at ``wpm`` words/minute.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
  - `word_count(self) -> 'int'` — Number of whitespace-delimited words in the narration.
- **`Demo`** *(dataclass)* — The top-level declarative artifact for a complete walkthrough.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Total estimated runtime from narration word counts.
  - `is_valid(self) -> 'bool'` — ``True`` iff :meth:`validate` returns no problems.
  - `iter_actions(self) -> 'list[Action]'` — Flat, ordered list of every action across all scenes/chunks.
  - `iter_chunks(self) -> 'list[Chunk]'` — Flat, ordered list of every chunk across all scenes.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
  - `to_json(self, *, indent: 'int | None' = 2) -> 'str'` — Serialize to a JSON string.
  - `to_yaml(self) -> 'str'` — Serialize to a YAML string. Requires PyYAML (a core dependency).
  - `validate(self) -> 'list[str]'` — Return a list of human-readable structural problems (empty == valid).
- **`Scene`** *(dataclass)* — A logical chapter of the demo with a single capture strategy.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Sum of chunk duration estimates.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
- **`SceneKind`** — The capture/render strategy a scene implies.
- **`WordTimestamp`** *(dataclass)* — A single word with millisecond start/end, produced by a transcriber.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_

## `democreate.config` {#democreateconfig}

Configuration and theming for DemoCreate renders.

### Classes

- **`AudioConfig`** *(dataclass)* — Voice and audio-assembly settings.
- **`MetadataConfig`** *(dataclass)* — Provenance/metadata shown on screen, written to the container, and hidden.
- **`RenderConfig`** *(dataclass)* — Top-level render configuration: theme + audio + video + metadata.
  - `set_aspect(self, name: 'str') -> 'RenderConfig'` — Set ``video.width``/``video.height`` from a named aspect preset.
  - `set_resolution(self, name: 'str') -> 'RenderConfig'` — Set 16:9 ``video.width``/``video.height`` from a resolution tier.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain dict (colors stay as lists for YAML cleanliness).
  - `to_yaml(self) -> 'str'` — Serialize the config to YAML.
- **`Theme`** *(dataclass)* — Colors and font scale for rendered frames.
- **`VideoConfig`** *(dataclass)* — Geometry and motion settings.

## `democreate.media` {#democreatemedia}

Shared media value types used across capture, narration, and assembly.

### Classes

- **`AudioClip`** *(dataclass)* — A rendered narration audio file and its measured properties.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
- **`FrameState`** *(dataclass)* — A renderable snapshot of the virtual environment at one instant.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_

## `democreate.pipeline` {#democreatepipeline}

End-to-end orchestration: a declarative :class:`Demo` becomes rendered output.

### Classes

- **`Pipeline`** — Configurable orchestrator over the DemoCreate subsystems.
  - `run(self, demo: 'Demo', workspace: 'Workspace | None' = None) -> 'PipelineResult'` — Render ``demo`` end-to-end, returning a :class:`PipelineResult`.
- **`PipelineResult`** *(dataclass)* — Paths and artifacts produced by a pipeline run.
  - `summary(self) -> 'dict[str, object]'` — A compact JSON-able summary of what was produced.

### Functions

- **`build_demo(demo: 'Demo', workspace: 'Workspace | None' = None, **kwargs: 'object') -> 'PipelineResult'`** — Convenience one-shot: construct a default :class:`Pipeline` and run it.
- **`render_video(result: 'PipelineResult', out_path: 'Path | None' = None, *, fps: 'int | None' = None, burn_captions: 'bool' = False, verify: 'bool' = True, animate: 'bool' = True, animation_fps: 'int | None' = None, config=None)`** — Assemble an audio-synced MP4 from a completed pipeline result.

## `democreate.portfolio` {#democreateportfolio}

Portfolio orchestration: a directory of repositories becomes a shelf of videos.

### Classes

- **`PortfolioReport`** *(dataclass)* — The result of a whole-directory portfolio run.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-ready dict.
- **`ProjectResult`** *(dataclass)* — Outcome of rendering one project.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-ready dict for the portfolio index.

### Functions

- **`build_project_demo(repo: 'Path', workspace, *, config=None, max_modules: 'int' = 6, title: 'str | None' = None)`** — Collect facts, render an architecture diagram, and build the summary demo.
- **`collect_project_facts(repo: 'Path', *, max_modules: 'int' = 6) -> 'ProjectFacts'`** — Walk ``repo`` and assemble its render-ready :class:`ProjectFacts`.
- **`discover_projects(projects_dir: 'Path', *, skip: 'tuple[str, ...]' = ()) -> 'list[Path]'`** — Return the sorted project directories under ``projects_dir``.
- **`render_portfolio(projects_dir: 'Path', output_root: 'Path', *, config=None, tts: 'str' = 'system', voice: 'str' = '', max_projects: 'int' = 0, max_modules: 'int' = 6, skip: 'tuple[str, ...]' = (), timestamp: 'str | None' = None, verify: 'bool' = True) -> 'PortfolioReport'`** — Render a summary video for every project under ``projects_dir``.
- **`render_project(repo: 'Path', output_root: 'Path', *, config=None, tts: 'str' = 'system', voice: 'str' = '', max_modules: 'int' = 6, timestamp: 'str | None' = None, verify: 'bool' = True) -> 'ProjectResult'`** — Render one repository to a timestamped, verified summary MP4.
- **`utc_stamp(now: 'datetime | None' = None) -> 'str'`** — Return a filesystem-safe UTC timestamp like ``20260625T164530Z``.

## `democreate.project_paths` {#democreateproject_paths}

Path resolution for DemoCreate runs.

### Classes

- **`Workspace`** *(dataclass)* — Resolved output locations for one demo build.
  - `clean(self) -> 'None'` — Remove the entire workspace root if it exists (idempotent).

### Functions

- **`default_output_root() -> 'Path'`** — Return the conventional output root (``./output`` under the cwd).
- **`relativize_under_root(obj: 'Any', root: 'Path | str') -> 'Any'`** — Rewrite absolute-path strings under ``root`` to ``root``-relative POSIX form.

## `democreate.errors` {#democreateerrors}

Exception hierarchy for DemoCreate.

### Classes

- **`BackendUnavailableError`** — A requested optional backend is not installed.
- **`CaptureError`** — A screen, browser, or terminal capture step failed.
- **`DemoCreateError`** — Base class for every error DemoCreate raises deliberately.
- **`RenderError`** — A frame, video, or export render step failed.
- **`SchemaValidationError`** — A :class:`~democreate.schema.Demo` failed structural validation.
- **`SyncError`** — Audio/action synchronization failed (e.g. transcription mismatch).

## `democreate.cli` {#democreatecli}

The ``democreate`` command-line interface.

### Functions

- **`backends() -> 'None'`** — List subsystem backends and whether their optional extras are installed.
- **`build(demo: 'Path', output: 'Path' = PosixPath('output'), tts: 'str' = 'auto', strict: 'bool' = True) -> 'None'`** — Run the full pipeline: TTS, sync, frames, captions, and HTML player.
- **`captions(demo: 'Path', fmt: 'str' = 'srt') -> 'None'`** — Emit subtitles for a demo to stdout.
- **`config(out: 'Path' = PosixPath('democreate.yaml'), theme: 'str' = 'dark') -> 'None'`** — Write a fully-commented render-config YAML you can edit and pass to --config.
- **`fetch_voice() -> 'None'`** — Download the Kokoro neural-TTS model files (~340 MB) for `--tts kokoro`.
- **`gif(demo: 'Path', output: 'Path' = PosixPath('output'), out: 'Path' = PosixPath('demo.gif'), fps: 'int' = 8, theme: 'str' = 'dark') -> 'None'`** — Build a demo and export an animated GIF preview of its frames.
- **`init(path: 'Path' = PosixPath('demo.json'), fmt: 'str' = 'json') -> 'None'`** — Write a starter demo artifact you can edit and then ``build``.
- **`inspect(demo: 'Path') -> 'None'`** — Validate a demo and print a structural summary.
- **`localize(demo: 'Path', output: 'Path' = PosixPath('output'), audio_lang: 'str' = 'en', subtitle_lang: 'str' = 'ru', source_lang: 'str' = 'en', pairs: 'str' = '', translator: 'str' = 'ollama', model: 'str' = 'smollm2', host: 'str' = 'http://localhost:11434', tts: 'str' = 'kokoro', voice: 'str' = 'af_heart', theme: 'str' = 'noir', resolution: 'str' = '1080p', burn: 'bool' = False) -> 'None'`** — Render localized videos — audio in one language, subtitles in another.
- **`main() -> 'None'`** — Entry point for the ``democreate`` console script.
- **`paper(pdf: 'Path', repo: 'Path' = None, figures: 'Path' = None, output: 'Path' = PosixPath('output'), pages: 'str' = '1', theme: 'str' = 'paper', voice: 'str' = '', tts: 'str' = 'system', aspect: 'str' = '', resolution: 'str' = '', author: 'str' = '', watermark: 'str' = '', max_figures: 'int' = 6, config: 'Path' = None, render_it: 'bool' = True) -> 'None'`** — Generate a narrated demo of a research paper (PDF + optional codebase).
- **`portfolio(projects_dir: 'Path', output: 'Path' = PosixPath('output'), tts: 'str' = 'system', voice: 'str' = '', theme: 'str' = 'noir', resolution: 'str' = '1080p', max_projects: 'int' = 0, max_modules: 'int' = 6, skip: 'str' = '') -> 'None'`** — Render a timestamped summary video for every project under a directory.
- **`render(demo: 'Path', output: 'Path' = PosixPath('output'), tts: 'str' = 'system', voice: 'str' = '', fps: 'int' = 0, captions: 'bool' = False, animate: 'bool' = True, animation_fps: 'int' = 15, theme: 'str' = 'noir', aspect: 'str' = '', resolution: 'str' = '', author: 'str' = '', watermark: 'str' = '', header: 'bool' = False, config: 'Path' = None) -> 'None'`** — Render a demo to an HD MP4 with real voiceover, then verify its content.
- **`stego(image: 'Path', demo: 'Path' = None) -> 'None'`** — Extract (and optionally verify) the steganographic provenance in a PNG.
- **`thumbnail(demo: 'Path', out: 'Path' = PosixPath('poster.png'), theme: 'str' = 'dark', subtitle: 'str' = '') -> 'None'`** — Render a poster / thumbnail frame for a demo.
- **`tour(repo: 'Path', output: 'Path' = PosixPath('output'), title: 'str' = 'Codebase Tour', build_it: 'bool' = True, render_it: 'bool' = False, tts: 'str' = 'system', voice: 'str' = '', theme: 'str' = 'noir') -> 'None'`** — Generate a codebase tour demo from a repository (build and/or render it).
- **`verify(video: 'Path', width: 'int' = 0, height: 'int' = 0, min_duration: 'float' = 1.0) -> 'None'`** — Content-assert a video: real streams, expected size, non-silent, non-black.
- **`version() -> 'None'`** — Print the installed DemoCreate version.

## `democreate.translation.translator` {#democreatetranslationtranslator}

Translators and language helpers for localized demos.

### Classes

- **`IdentityTranslator`** — Deterministic default: returns text unchanged (a no-op translation).
  - `translate(self, text: 'str', *, source: 'str', target: 'str') -> 'str'` — Return ``text`` unchanged.
- **`LanguageConfig`** *(dataclass)* — Which language the audio is spoken in and which the subtitles are written in.
  - `tag(self) -> 'str'` — A filename tag making the audio/subtitle languages explicit.
- **`OllamaTranslator`** — Translate via a local `ollama` server (guarded; needs a running server).
  - `is_available(self) -> 'bool'` — Whether the ollama server answers its tags endpoint.
  - `translate(self, text: 'str', *, source: 'str', target: 'str') -> 'str'` — Translate ``text`` via ollama; passthrough on empty or same-language.
- **`Translator`** — Abstract translator: source-language text → target-language text.
  - `is_available(self) -> 'bool'` — Whether this translator can run.
  - `translate(self, text: 'str', *, source: 'str', target: 'str') -> 'str'` — Translate ``text`` from ``source`` to ``target``.

### Functions

- **`get_translator(name: 'str' = 'auto', **kwargs: 'object') -> 'Translator'`** — Return a translator by name.
- **`language_name(code: 'str') -> 'str'`** — Return a human language name for a code (falls back to the code itself).
- **`localized_captions(timed_demo: 'Demo', translator: 'Translator', *, source: 'str', target: 'str', fmt: 'str' = 'srt') -> 'str'`** — Emit subtitles in ``target`` against a *timed* demo's existing timing.
- **`translate_demo(demo: 'Demo', translator: 'Translator', *, source: 'str', target: 'str') -> 'Demo'`** — Return a copy of ``demo`` with every chunk's narration translated.

## `democreate.translation.localize` {#democreatetranslationlocalize}

Render a demo with audio in one language and subtitles in another.

### Classes

- **`LocalizedResult`** *(dataclass)* — One localized render (one audio/subtitle language pair).
  - `to_dict(self) -> 'dict[str, object]'` — Serialize to a JSON-ready dict.

### Functions

- **`localize_batch(demo: 'Demo', workspace, *, pairs: 'list[tuple[str, str]]', source: 'str' = 'en', translator: 'Translator | None' = None, config=None, tts: 'str' = 'system', voice: 'str' = '', burn: 'bool' = False, verify: 'bool' = True, name: 'str | None' = None) -> 'list[LocalizedResult]'`** — Render one localized video per ``(audio_lang, subtitle_lang)`` pair.
- **`localize_render(demo: 'Demo', workspace, *, languages: 'LanguageConfig', translator: 'Translator | None' = None, config=None, tts: 'str' = 'system', voice: 'str' = '', burn: 'bool' = False, verify: 'bool' = True, name: 'str | None' = None) -> 'LocalizedResult'`** — Render one audio/subtitle language pair; return a :class:`LocalizedResult`.

## `democreate.narration.script` {#democreatenarrationscript}

Script generation: turning structured context into a declarative Demo.

### Classes

- **`LLMScriptGenerator`** — LLM-backed script generator (optional; never used in tests).
  - `generate(self, context: 'dict[str, Any]') -> 'Demo'` — Generate a demo via the configured LLM provider.
- **`ScriptGenerator`** — Abstract base for building a :class:`Demo` from input context.
  - `generate(self, context: 'dict[str, Any]') -> 'Demo'` — Build and return a :class:`Demo` from ``context``.
- **`TemplateScriptGenerator`** — Deterministic generator that maps a context dict to a :class:`Demo`.
  - `generate(self, context: 'dict[str, Any]') -> 'Demo'` — Build a :class:`Demo` from the template context dict.

### Functions

- **`generate_codebase_demo(summaries: 'list[Any]', *, title: 'str') -> 'Demo'`** — Build a codebase-tour :class:`Demo` from a list of module summaries.

## `democreate.narration.project_summary` {#democreatenarrationproject_summary}

Project-summary script generation: a repo's facts become a narrated ``Demo``.

### Classes

- **`KeyModule`** *(dataclass)* — One load-bearing module selected for a code scene.
- **`ProjectFacts`** *(dataclass)* — The structured, render-ready facts about one software project.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain JSON-ready dict (for the portfolio index).

### Functions

- **`generate_project_summary_demo(facts: 'ProjectFacts', *, title: 'str | None' = None, architecture_image: 'str | None' = None, width: 'int' = 1920, height: 'int' = 1080, fps: 'int' = 30, voice: 'str' = 'default', max_modules: 'int' = 6, max_packages: 'int' = 6) -> 'Demo'`** — Build a narrated project-summary :class:`Demo` from collected facts.

## `democreate.narration.tts` {#democreatenarrationtts}

Text-to-speech backends for DemoCreate narration.

### Classes

- **`ChatterboxTTSBackend`** — Chatterbox TTS backend (optional, requires the ``tts`` extra).
  - `is_available(self) -> 'bool'` — Return whether the ``chatterbox`` package is installed.
  - `synthesize(self, text: 'str', out_path: 'Path', *, voice: 'str | None' = None) -> 'AudioClip'` — Synthesize ``text`` with Chatterbox (only runs when installed).
- **`KokoroTTSBackend`** — Kokoro neural TTS backend — a high-quality, fully-local voice.
  - `is_available(self) -> 'bool'` — Return whether ``kokoro-onnx`` AND its model files are present.
  - `synthesize(self, text: 'str', out_path: 'Path', *, voice: 'str | None' = None) -> 'AudioClip'` — Synthesize ``text`` with Kokoro to a canonical WAV; measure its duration.
- **`SilentTTSBackend`** — Deterministic default backend that writes real WAV files of silence.
  - `estimate_duration_ms(self, text: 'str') -> 'int'` — Estimate spoken duration of ``text`` in milliseconds.
  - `is_available(self) -> 'bool'` — Always ``True`` — the default backend uses only the standard library.
  - `synthesize(self, text: 'str', out_path: 'Path', *, voice: 'str | None' = None) -> 'AudioClip'` — Write a silent WAV of the estimated duration and return its clip.
- **`SystemTTSBackend`** — Real-voice TTS using the operating system's built-in speech synthesizer.
  - `is_available(self) -> 'bool'` — Return whether a system TTS engine can synthesize usable audio.
  - `synthesize(self, text: 'str', out_path: 'Path', *, voice: 'str | None' = None) -> 'AudioClip'` — Speak ``text`` to a canonical WAV and return its *measured* clip.
- **`TTSBackend`** — Abstract base for a text-to-speech engine.
  - `is_available(self) -> 'bool'` — Return whether this backend can actually synthesize on this machine.
  - `synthesize(self, text: 'str', out_path: 'Path', *, voice: 'str | None' = None) -> 'AudioClip'` — Synthesize ``text`` to ``out_path`` and return the resulting clip.

### Functions

- **`fetch_kokoro_model(dest: 'Path | None' = None) -> 'tuple[Path, Path]'`** — Download the Kokoro model + voices into the cache dir if absent.
- **`get_tts_backend(name: 'str' = 'auto', *, voice: 'str | None' = None) -> 'TTSBackend'`** — Return a TTS backend by name.
- **`measure_wav_duration_ms(path: 'Path | str') -> 'int'`** — Return the true duration of a WAV file in milliseconds.
- **`synthesize_demo(demo: 'Demo', workspace, backend: 'TTSBackend | None' = None) -> 'list[AudioClip]'`** — Synthesize audio for every chunk of ``demo`` into the workspace.

## `democreate.narration.sync` {#democreatenarrationsync}

TTS->STT synchronization: anchoring actions to real spoken word timestamps.

### Classes

- **`HeuristicTranscriber`** — Deterministic stdlib transcriber that distributes words over real audio.
  - `transcribe(self, audio_path: 'Path', text: 'str | None' = None) -> 'list[WordTimestamp]'` — Distribute the words of ``text`` across the audio's real duration.
- **`Transcriber`** — Abstract base for turning audio + known text into word timestamps.
  - `transcribe(self, audio_path: 'Path', text: 'str | None' = None) -> 'list[WordTimestamp]'` — Return per-word timestamps for ``audio_path``.
- **`WhisperTranscriber`** — Whisper STT transcriber (optional, requires the ``whisper`` extra).
  - `transcribe(self, audio_path: 'Path', text: 'str | None' = None) -> 'list[WordTimestamp]'` — Transcribe with Whisper (only runs when ``whisper`` is installed).

### Functions

- **`absolute_word_timestamps(demo: 'Demo', clips: 'list[AudioClip]', transcriber: 'Transcriber | None' = None) -> 'list[WordTimestamp]'`** — Return every word of the demo timestamped on the absolute timeline.
- **`get_transcriber(name: 'str' = 'auto') -> 'Transcriber'`** — Return a transcriber by name.
- **`sync_demo(demo: 'Demo', clips: 'list[AudioClip]', transcriber: 'Transcriber | None' = None, *, lead_ms: 'int' = 0, gap_ms: 'int' = 0) -> 'Demo'`** — Assign absolute timestamps to every chunk and action from real audio.

## `democreate.narration.llm` {#democreatenarrationllm}

Optional LLM narration backend for DemoCreate.

### Classes

- **`LLMNarrator`** — OpenAI-compatible chat client for generating or polishing narration.
  - `is_available(self) -> 'bool'` — Return whether this narrator has an API key to authenticate with.
  - `narrate(self, prompt: 'str', *, system: 'str | None' = None, max_tokens: 'int' = 400) -> 'str'` — Generate narration text for ``prompt`` via the chat endpoint.
  - `rewrite_chunks(self, texts: 'list[str]', *, context: 'str' = '') -> 'list[str]'` — Polish a list of narration chunks, preserving length and order.

### Functions

- **`build_chat_payload(messages: 'list[dict]', *, model: 'str', temperature: 'float' = 0.7) -> 'dict'`** — Build the JSON body for an OpenAI-compatible ``/chat/completions`` request.
- **`get_narrator(**kwargs) -> 'LLMNarrator'`** — Construct an :class:`LLMNarrator`, resolving config from the environment.
- **`llm_available() -> 'bool'`** — Return whether an LLM API key is configured in the environment.

## `democreate.assembly.animator` {#democreateassemblyanimator}

Timed-frame animation: turn one-frame-per-chunk into smooth, dynamic video.

### Classes

- **`AnimationConfig`** *(dataclass)* — Settings for timed-frame animation.

### Functions

- **`active_index_at(windows: 'list[tuple[int, int]]', t_ms: 'int') -> 'int'`** — Return the index of the chunk active at ``t_ms`` (gap- and end-aware).
- **`chunk_timing(clips: 'list[AudioClip]', *, lead_ms: 'int' = 0, gap_ms: 'int' = 0, trail_ms: 'int' = 0) -> 'tuple[list[tuple[int, int]], int]'`** — Return per-chunk spoken ``(start_ms, end_ms)`` windows and the total duration.
- **`render_animation_frames(frame_paths: 'list[Path]', clips: 'list[AudioClip]', voiceover_wav: 'Path', out_dir: 'Path', *, size: 'tuple[int, int]', config: 'AnimationConfig | None' = None, scene_ids: 'list[str] | None' = None, kenburns_flags: 'list[bool] | None' = None, frame_states: 'list | None' = None, typing_flags: 'list[bool] | None' = None, theme=None, overlay_meta=None, demo_title: 'str' = '') -> 'tuple[list[Path], int]'`** — Render uniform-cadence animated frames with motion: typing, cursor, waveform.

## `democreate.assembly.audio` {#democreateassemblyaudio}

Voiceover post-processing for the assembly stage.

### Functions

- **`apply_fade(in_path: 'Path', out_path: 'Path', *, fade_ms: 'int' = 180) -> 'Path'`** — Apply a fade-in and fade-out to ``in_path`` with ffmpeg's ``afade``.
- **`concat_with_gaps(wav_paths: 'list[Path]', out_path: 'Path', *, gap_ms: 'int' = 0, lead_ms: 'int' = 0, trail_ms: 'int' = 0) -> 'Path'`** — Concatenate WAV clips in order, inserting silent gaps and lead/trail.
- **`ffmpeg_audio_available() -> 'bool'`** — Report whether the ``ffmpeg`` binary is on ``PATH``.
- **`measure_duration_ms(wav_path: 'Path') -> 'int'`** — Return the true duration of ``wav_path`` in milliseconds.
- **`normalize_audio(in_path: 'Path', out_path: 'Path', *, i: 'float' = -16.0, tp: 'float' = -1.5, lra: 'float' = 11.0) -> 'Path'`** — Loudness-normalize ``in_path`` with ffmpeg's ``loudnorm`` filter.
- **`write_silence(out_path: 'Path', ms: 'int', *, sample_rate: 'int' = 22050) -> 'Path'`** — Write a silent 16-bit mono PCM WAV of ``ms`` milliseconds.

## `democreate.assembly.captions` {#democreateassemblycaptions}

Pure subtitle/caption formatting.

### Functions

- **`to_ass(demo: 'Demo', *, wpm: 'int' = 150) -> 'str'`** — Render the demo's narration as a minimal Advanced SubStation (``.ass``).
- **`to_srt(demo: 'Demo', *, wpm: 'int' = 150) -> 'str'`** — Render the demo's narration as a SubRip (``.srt``) document.
- **`to_vtt(demo: 'Demo', *, wpm: 'int' = 150) -> 'str'`** — Render the demo's narration as a WebVTT (``.vtt``) document.
- **`word_timestamps_to_srt(words: 'list[WordTimestamp]') -> 'str'`** — Render word-level timestamps as a karaoke-granularity SRT document.

## `democreate.assembly.compositor` {#democreateassemblycompositor}

Timeline construction and compositor backends.

### Classes

- **`Compositor`** — Abstract base for everything that turns a :class:`Timeline` into output.
  - `compose(self, timeline: 'Timeline', workspace: 'Workspace') -> 'Path'` — Render ``timeline`` into ``workspace`` and return the primary artifact.
- **`ManifestCompositor`** — The deterministic default compositor (core deps only).
  - `compose(self, timeline: 'Timeline', workspace: 'Workspace') -> 'Path'` — Write the render manifest and per-entry frames.
- **`MoviePyCompositor`** — Guarded legacy MoviePy compositor slot (extra: ``video``).
  - `compose(self, timeline: 'Timeline', workspace: 'Workspace') -> 'Path'` — Detect the legacy MoviePy compositor dependency.
- **`Timeline`** *(dataclass)* — A fully-resolved, gap-free render timeline.
  - `entry_at_ms(self, t: 'int') -> 'TimelineEntry | None'` — Return the entry whose window contains ``t``.
  - `frame_count(self) -> 'int'` — Total number of frames at this timeline's fps.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize the whole timeline to a JSON-ready dict.
- **`TimelineEntry`** *(dataclass)* — One contiguous slice of the timeline.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-ready dict.

### Functions

- **`build_timeline(demo: 'Demo', *, fps: 'int | None' = None, wpm: 'int' = 150) -> 'Timeline'`** — Build a gap-free render timeline from a demo (pure, deterministic).

## `democreate.capture.screen` {#democreatecapturescreen}

Frame rendering — the synthetic virtual renderer at the heart of capture.

### Classes

- **`FrameSource`** — Abstract source of rendered frames.
  - `render(self, state: 'FrameState', size: 'tuple[int, int]') -> '_ImageModule.Image'` — Render ``state`` to an image of ``size`` ``(width, height)``.
- **`MssScreenCapture`** — Real screen-pixel capture via the ``mss`` library (extra: ``capture``).
  - `render(self, state: 'FrameState', size: 'tuple[int, int]') -> '_ImageModule.Image'` — Capture the current screen and resize it to ``size``.
- **`SyntheticRenderer`** — Deterministic, themeable, resolution-aware pure-Pillow renderer.
  - `render(self, state: 'FrameState', size: 'tuple[int, int]') -> '_ImageModule.Image'` — Draw ``state`` onto a fresh image of ``size``.

### Functions

- **`render_demo_thumbnail(demo: 'Demo', size: 'tuple[int, int]' = (1280, 720), *, theme: 'Theme | None' = None) -> '_ImageModule.Image'`** — Render a thumbnail from the opening frame of a demo's first scene.
- **`render_frame(state: 'FrameState', size: 'tuple[int, int]' = (1920, 1080), *, theme: 'Theme | None' = None) -> '_ImageModule.Image'`** — Render a single frame with the default synthetic renderer.
- **`waveform_band_box(width: 'int', height: 'int') -> 'tuple[int, int, int, int]'`** — Return the ``(x0, y0, x1, y1)`` band reserved for the waveform overlay.

## `democreate.animation.waveform` {#democreateanimationwaveform}

Speech-waveform visualization for demo frames.

### Functions

- **`compute_envelope(wav_path: 'Path', bars: 'int') -> 'list[float]'`** — Reduce a 16-bit PCM WAV file to ``bars`` normalized RMS amplitudes.
- **`draw_waveform(draw: 'ImageDraw.ImageDraw', box: 'tuple[int, int, int, int]', envelope: 'list[float]', *, progress: 'float' = 1.0, bar_color: 'tuple[int, int, int]' = (90, 110, 130), played_color: 'tuple[int, int, int]' = (80, 200, 255), playhead_color: 'tuple[int, int, int]' = (240, 245, 255), gap: 'int' = 2) -> 'None'`** — Draw a mirrored-bar waveform with a played/unplayed split and a playhead.
- **`render_waveform_strip(envelope: 'list[float]', size: 'tuple[int, int]', *, progress: 'float' = 1.0, bg: 'tuple[int, int, int]' = (15, 18, 26)) -> 'Image.Image'`** — Render a full-frame waveform strip image.

## `democreate.animation.diagram` {#democreateanimationdiagram}

Architecture / overview diagram renderer for demo frames.

### Classes

- **`DiagramNode`** *(dataclass)* — A single labeled box inside an architecture column.

### Functions

- **`democreate_architecture_image(size: 'tuple[int, int]' = (1920, 1080), *, bg: 'tuple[int, int, int]' = (13, 17, 23), accent: 'tuple[int, int, int]' = (56, 139, 253), fg: 'tuple[int, int, int]' = (230, 237, 243)) -> 'Image.Image'`** — Render the canonical DemoCreate architecture as a diagram.
- **`render_architecture_diagram(size: 'tuple[int, int]', *, title: 'str', columns: 'list[tuple[str, list[DiagramNode]]]', bg: 'tuple[int, int, int]' = (13, 17, 23), accent: 'tuple[int, int, int]' = (56, 139, 253), fg: 'tuple[int, int, int]' = (230, 237, 243)) -> 'Image.Image'`** — Render a clean left-to-right architecture diagram.

## `democreate.animation.fonts` {#democreateanimationfonts}

Scalable font resolution for crisp, large frame text.

### Functions

- **`scaled_font(frame_height: 'int', ratio: 'float', *, mono: 'bool' = False) -> 'ImageFont.FreeTypeFont'`** — Load a font sized to a fraction of the frame height.

## `democreate.codebase.walker` {#democreatecodebasewalker}

AST-based source walking for the codebase subsystem.

### Classes

- **`ClassInfo`** *(dataclass)* — A summarized class and its methods.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain JSON-ready dict.
- **`FunctionInfo`** *(dataclass)* — A summarized function or method.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain JSON-ready dict.
- **`ModuleSummary`** *(dataclass)* — A structural summary of one Python module.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain JSON-ready dict.

### Functions

- **`summarize_module(path: 'Path') -> 'ModuleSummary'`** — Read a Python file and summarize it.
- **`summarize_source(source: 'str', *, path: 'str' = '<string>', name: 'str | None' = None) -> 'ModuleSummary'`** — Summarize Python source text into a :class:`ModuleSummary`.
- **`walk_repository(root: 'Path', *, pattern: 'str' = '**/*.py', exclude: 'tuple[str, ...]' = ('__pycache__', '.venv', 'build', 'dist')) -> 'list[ModuleSummary]'`** — Summarize every matching Python file under ``root``.

## `democreate.paper.extract` {#democreatepaperextract}

Structured summarization of a research paper from its PDF + figures.

### Classes

- **`PaperSummary`** *(dataclass)* — A compact, render-ready summary of a research paper.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-friendly dict (figure paths as strings).

### Functions

- **`collect_figures(figures_dir: 'Path', *, limit: 'int | None' = None) -> 'list[Path]'`** — Collect sorted figure images from a directory (non-recursive).
- **`summarize_paper(pdf: 'Path', *, figures_dir: 'Path | None' = None, max_abstract_chars: 'int' = 900) -> 'PaperSummary'`** — Build a :class:`PaperSummary` from a PDF and optional figures directory.

## `democreate.paper.structure` {#democreatepaperstructure}

Pure-text extraction of a paper's abstract, figure captions, and sections.

### Classes

- **`FigureCaption`** *(dataclass)* — A figure number paired with its caption sentence.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-friendly dict.
- **`PaperSection`** *(dataclass)* — A section heading: its number (possibly empty) and title.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-friendly dict.

### Functions

- **`extract_abstract(text: 'str', *, max_chars: 'int' = 1200) -> 'str'`** — Extract the real abstract from paper text, rejecting the TOC.
- **`extract_figure_captions(text: 'str', *, max_caption_chars: 'int' = 320) -> 'list[FigureCaption]'`** — Extract figure captions from paper text.
- **`extract_sections(text: 'str') -> 'list[PaperSection]'`** — Extract section headings from paper text.
- **`summarize_structure(pdf: 'Path', *, max_text_pages: 'int' = 14) -> 'dict[str, Any]'`** — Extract abstract, figure captions, and sections from a PDF.

## `democreate.paper.script` {#democreatepaperscript}

Build a narrated :class:`~democreate.schema.Demo` from a research paper.

### Functions

- **`build_paper_demo(summary: 'PaperSummary', *, code_summaries: 'list | None' = None, page_images: 'list[Path] | None' = None, architecture_image: 'Path | None' = None, figure_captions: 'list | None' = None, sections: 'list | None' = None, width: 'int' = 1920, height: 'int' = 1080, fps: 'int' = 30, voice: 'str' = '', max_figures: 'int' = 6) -> 'Demo'`** — Assemble a narrated demo from a paper summary and optional code/pages.
- **`chunk_sentences(text: 'str', *, max_words: 'int' = 26) -> 'list[str]'`** — Split prose into narration-sized chunks at sentence boundaries.

## `democreate.paper.pdf` {#democreatepaperpdf}

Poppler command-line wrapper for reading and rasterizing PDFs.

### Functions

- **`extract_text(pdf: 'Path', *, first: 'int | None' = None, last: 'int | None' = None) -> 'str'`** — Extract text from a (range of) PDF page(s) via ``pdftotext``.
- **`pdf_info(pdf: 'Path') -> 'dict[str, str]'`** — Return ``pdfinfo`` metadata as a dict of lowercased keys.
- **`pdf_page_count(pdf: 'Path') -> 'int'`** — Return the number of pages in ``pdf``.
- **`poppler_available() -> 'bool'`** — Report whether the required poppler binaries are installed.
- **`render_page(pdf: 'Path', page: 'int', out_path: 'Path', *, dpi: 'int' = 150) -> 'Path'`** — Rasterize a single PDF page to a PNG via ``pdftoppm``.
- **`render_pages(pdf: 'Path', out_dir: 'Path', *, pages: 'list[int] | None' = None, dpi: 'int' = 150, prefix: 'str' = 'page') -> 'list[Path]'`** — Rasterize several PDF pages to ``out_dir/<prefix>_<NNN>.png``.

## `democreate.export.video` {#democreateexportvideo}

Video and GIF export.

### Functions

- **`assemble_video(frame_paths: 'list[Path]', durations_ms: 'list[int]', audio_path: 'Path | None', out_path: 'Path', *, fps: 'int' = 30, size: 'tuple[int, int] | None' = None, subtitles: 'Path | None' = None, crf: 'int' = 18, preset: 'str' = 'medium') -> 'Path'`** — Encode an audio-synced MP4 holding each frame for its measured duration.
- **`build_concat_demuxer_file(frames_with_durations: 'list[tuple[Path, float]]', *, repeat_last: 'bool' = True) -> 'str'`** — Build an ffmpeg concat-demuxer script holding each frame for its duration.
- **`build_ffmpeg_command(frames_glob: 'str', audio_path: 'str | None', out_path: 'Path', *, fps: 'int' = 30) -> 'list[str]'`** — Construct the ``ffmpeg`` argv list for an H.264 MP4 encode.
- **`concat_wavs(wav_paths: 'list[Path]', out_path: 'Path') -> 'Path'`** — Concatenate canonical WAV clips gap-free into one track (pure stdlib).
- **`encode_frame_sequence(frame_paths: 'list[Path]', audio_path: 'Path | None', out_path: 'Path', *, fps: 'int' = 15, crf: 'int' = 18, preset: 'str' = 'medium') -> 'Path'`** — Encode uniformly-timed frames (+ audio) into an MP4 via the image2 demuxer.
- **`export_video(frame_paths: 'list[Path]', audio_path: 'Path | None', out_path: 'Path', *, fps: 'int' = 30) -> 'Path'`** — Encode frames (+ optional audio) into an MP4.
- **`ffmpeg_available() -> 'bool'`** — Return ``True`` if the ``ffmpeg`` binary is on ``PATH``.
- **`frames_to_gif(frame_paths: 'list[Path]', out_path: 'Path', *, fps: 'int' = 10) -> 'Path'`** — Assemble an animated GIF from still frames using Pillow.

## `democreate.export.verify` {#democreateexportverify}

Content-asserting verification for rendered video.

### Classes

- **`VideoReport`** *(dataclass)* — The result of content-asserting verification of a video file.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_

### Functions

- **`parse_ffprobe(probe: 'dict[str, Any]', *, path: 'Path', expected_width: 'int | None' = None, expected_height: 'int | None' = None, min_duration_s: 'float' = 1.0, min_audio_ratio: 'float' = 0.9) -> 'VideoReport'`** — Build a :class:`VideoReport` from parsed ``ffprobe -of json`` output (pure).
- **`verify_video(path: 'Path', *, expected_width: 'int | None' = None, expected_height: 'int | None' = None, min_duration_s: 'float' = 1.0, check_content: 'bool' = True) -> 'VideoReport'`** — Run full content-asserting verification on a real video file.

## `democreate.export.chapters` {#democreateexportchapters}

Chapter-marker export for narrated demos.

### Functions

- **`embed_chapters(mp4_in: 'Path', ffmetadata: 'Path', mp4_out: 'Path') -> 'Path'`** — Mux chapter metadata into an MP4 with ffmpeg.
- **`measured_chapters(demo: 'Demo', clips, *, lead_ms=0, gap_ms=0, trail_ms=0)`** — Return scene chapters aligned to the *measured* audio timeline.
- **`to_ffmetadata(demo: 'Demo', *, chapters=None, total_ms=None) -> 'str'`** — Build an ffmpeg ``FFMETADATA1`` document from a demo's scenes.
- **`to_youtube_chapters(demo: 'Demo', *, chapters=None) -> 'str'`** — Build a YouTube chapter list from a demo's scenes.
- **`write_chapters(demo: 'Demo', out_dir: 'Path', *, chapters=None, total_ms=None) -> 'dict[str, Path]'`** — Write both chapter formats to disk.

## `democreate.export.poster` {#democreateexportposter}

Poster/thumbnail frame and GIF preview export.

### Functions

- **`demo_to_gif(frame_paths: 'list[Path]', out_path: 'Path', *, fps: 'int' = 8, max_frames: 'int' = 48) -> 'Path'`** — Build an animated GIF preview by evenly sampling a frame sequence.
- **`render_poster(demo: 'Demo', out_path: 'Path', *, size: 'tuple[int, int]' = (1920, 1080), theme: 'Theme | None' = None, subtitle: 'str | None' = None) -> 'Path'`** — Render a designed poster/thumbnail PNG for a demo.

## `democreate.export.interactive` {#democreateexportinteractive}

Interactive, self-contained HTML player export.

### Functions

- **`build_timeline(demo: 'Demo') -> 'dict'`** — Build a deterministic caption/chapter timeline from a demo.
- **`export_html_player(demo: 'Demo', timeline: 'dict | None', out_path: 'Path', *, frames_dir: 'str | None' = None) -> 'Path'`** — Render a self-contained HTML player for ``demo``.

## `democreate.export.formats` {#democreateexportformats}

Document-format exports for a :class:`~democreate.schema.Demo`.

### Functions

- **`export_pdf(demo: 'Demo', out_path: 'Path') -> 'Path'`** — Render the demo transcript to a PDF.
- **`to_chapters(demo: 'Demo') -> 'list[dict]'`** — Build a chapter list for players and YouTube descriptions.
- **`to_json(demo: 'Demo', *, indent: 'int' = 2, relative_to: 'Path | str | None' = None) -> 'str'`** — Serialize the demo to JSON.
- **`to_markdown(demo: 'Demo') -> 'str'`** — Render the demo as a readable Markdown transcript.
