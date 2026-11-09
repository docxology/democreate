# API reference

> **Generated** by `scripts/generate_api_docs.py` from the live `democreate` package (version `0.8.0`). Do not edit by hand — regenerate with `.venv/bin/python scripts/generate_api_docs.py`.

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
- [`democreate.evaluation`](#democreateevaluation)
- [`democreate.api_docs`](#democreateapi_docs)
- [`democreate.manuscript`](#democreatemanuscript)
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
- [`democreate.assembly.effects`](#democreateassemblyeffects)
- [`democreate.capture.screen`](#democreatecapturescreen)
- [`democreate.capture.browser`](#democreatecapturebrowser)
- [`democreate.capture.replay`](#democreatecapturereplay)
- [`democreate.capture.terminal`](#democreatecaptureterminal)
- [`democreate.animation.waveform`](#democreateanimationwaveform)
- [`democreate.animation.diagram`](#democreateanimationdiagram)
- [`democreate.animation.fonts`](#democreateanimationfonts)
- [`democreate.animation.highlights`](#democreateanimationhighlights)
- [`democreate.animation.zoom`](#democreateanimationzoom)
- [`democreate.animation.manim_scenes`](#democreateanimationmanim_scenes)
- [`democreate.codebase.walker`](#democreatecodebasewalker)
- [`democreate.codebase.dependency`](#democreatecodebasedependency)
- [`democreate.codebase.ast_viz`](#democreatecodebaseast_viz)
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
- [`democreate.export.metadata`](#democreateexportmetadata)
- [`democreate.export.overlay`](#democreateexportoverlay)
- [`democreate.export.stego`](#democreateexportstego)

## `democreate`

DemoCreate — declarative, deterministic audio-visual demo generation.

### Classes

- **`Action`** *(dataclass)* — One typed event mutating the virtual environment.
  - `from_dict(data: 'dict[str, Any]') -> 'Action'` — Inverse of :meth:`to_dict`.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain JSON-ready dict (omitting unset optional fields).
- **`ActionType`** — Every primitive change a demo can express against the virtual environment.
- **`BackendUnavailableError`** — A requested optional backend is not installed.
- **`CaptureError`** — A screen, browser, or terminal capture step failed.
- **`Chunk`** *(dataclass)* — A narration unit and the actions it triggers.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Estimate narration duration from word count at ``wpm`` words/minute.
  - `from_dict(data: 'dict[str, Any]') -> 'Chunk'` — _(no docstring)_
  - `playback_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Return measured narration duration, or its pre-synthesis estimate.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
  - `word_count(self) -> 'int'` — Number of whitespace-delimited words in the narration.
- **`Demo`** *(dataclass)* — The top-level declarative artifact for a complete walkthrough.
  - `chunk_by_id(self, chunk_id: 'str') -> 'Chunk | None'` — Return the first chunk with ``id == chunk_id`` across all scenes.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Total estimated runtime from narration word counts.
  - `filter_scenes(self, *, ids: 'list[str] | None' = None, kinds: 'list[SceneKind] | None' = None, slice_start: 'int | None' = None, slice_end: 'int | None' = None) -> 'Demo'` — Return a new :class:`Demo` containing only the matching scenes.
  - `from_dict(data: 'dict[str, Any]') -> 'Demo'` — Rebuild a :class:`Demo` from its :meth:`to_dict` mapping.
  - `from_file(path: 'str | Path') -> 'Demo'` — Load a :class:`Demo` from a ``.json`` or ``.yaml`` file.
  - `from_json(text: 'str') -> 'Demo'` — Parse a :class:`Demo` from a JSON string.
  - `from_yaml(text: 'str') -> 'Demo'` — Parse a :class:`Demo` from a YAML string.
  - `is_valid(self) -> 'bool'` — ``True`` iff :meth:`validate` returns no problems.
  - `iter_actions(self) -> 'list[Action]'` — Flat, ordered list of every action across all scenes/chunks.
  - `iter_chunks(self) -> 'list[Chunk]'` — Flat, ordered list of every chunk across all scenes.
  - `merge(self, other: 'Demo', *, offset: 'int' = 0) -> 'Demo'` — Append ``other``'s scenes onto this demo, returning a new :class:`Demo`.
  - `scene_by_id(self, scene_id: 'str') -> 'Scene | None'` — Return the first scene with ``id == scene_id``, or ``None``.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
  - `to_file(self, path: 'str | Path') -> 'Path'` — Write this demo to a ``.json`` or ``.yaml`` file and return its path.
  - `to_json(self, *, indent: 'int | None' = 2) -> 'str'` — Serialize to a JSON string.
  - `to_yaml(self) -> 'str'` — Serialize to a YAML string. Requires PyYAML (a core dependency).
  - `validate(self) -> 'list[str]'` — Return a list of human-readable structural problems (empty == valid).
- **`DemoCreateError`** — Base class for every error DemoCreate raises deliberately.
- **`Pipeline`** — Configurable orchestrator over the DemoCreate subsystems.
  - `dry_run(self, demo: 'Demo') -> 'list[str]'` — Validate ``demo`` without running TTS, sync, or rendering.
  - `run(self, demo: 'Demo', workspace: 'Workspace | None' = None) -> 'PipelineResult'` — Render ``demo`` end-to-end, returning a :class:`PipelineResult`.
- **`PipelineResult`** *(dataclass)* — Paths and artifacts produced by a pipeline run.
  - `summary(self) -> 'dict[str, object]'` — A compact JSON-able summary of what was produced.
- **`RenderError`** — A frame, video, or export render step failed.
- **`Scene`** *(dataclass)* — A logical chapter of the demo with a single capture strategy.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Sum of chunk duration estimates.
  - `from_dict(data: 'dict[str, Any]') -> 'Scene'` — _(no docstring)_
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
- **`SceneKind`** — The capture/render strategy a scene implies.
- **`SchemaValidationError`** — A :class:`~democreate.schema.Demo` failed structural validation.
- **`SyncError`** — Audio/action synchronization failed (e.g. transcription mismatch).
- **`WordTimestamp`** *(dataclass)* — A single word with millisecond start/end, produced by a transcriber.
  - `from_dict(data: 'dict[str, Any]') -> 'WordTimestamp'` — _(no docstring)_
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
- **`Workspace`** *(dataclass)* — Resolved output locations for one demo build.
  - `clean(self) -> 'None'` — Remove the entire workspace root if it exists (idempotent).
  - `ensure_safe(self) -> 'None'` — Refuse existing links in generated namespaces before local writes.

### Functions

- **`build_demo(demo: 'Demo', workspace: 'Workspace | None' = None, **kwargs: 'object') -> 'PipelineResult'`** — Convenience one-shot: construct a default :class:`Pipeline` and run it.
- **`default_output_root() -> 'Path'`** — Return the conventional output root (``./output`` under the cwd).
- **`get_logger(name: 'str') -> 'logging.Logger'`** — Return a logger namespaced under ``democreate``.
- **`log_stage(stage: 'str', logger: 'logging.Logger | None' = None) -> 'Iterator[None]'`** — Time a named stage, logging start, success, and elapsed milliseconds.

## `democreate.schema`

Declarative demo schema — the deterministic spine of DemoCreate.

### Classes

- **`Action`** *(dataclass)* — One typed event mutating the virtual environment.
  - `from_dict(data: 'dict[str, Any]') -> 'Action'` — Inverse of :meth:`to_dict`.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain JSON-ready dict (omitting unset optional fields).
- **`ActionType`** — Every primitive change a demo can express against the virtual environment.
- **`Chunk`** *(dataclass)* — A narration unit and the actions it triggers.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Estimate narration duration from word count at ``wpm`` words/minute.
  - `from_dict(data: 'dict[str, Any]') -> 'Chunk'` — _(no docstring)_
  - `playback_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Return measured narration duration, or its pre-synthesis estimate.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
  - `word_count(self) -> 'int'` — Number of whitespace-delimited words in the narration.
- **`Demo`** *(dataclass)* — The top-level declarative artifact for a complete walkthrough.
  - `chunk_by_id(self, chunk_id: 'str') -> 'Chunk | None'` — Return the first chunk with ``id == chunk_id`` across all scenes.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Total estimated runtime from narration word counts.
  - `filter_scenes(self, *, ids: 'list[str] | None' = None, kinds: 'list[SceneKind] | None' = None, slice_start: 'int | None' = None, slice_end: 'int | None' = None) -> 'Demo'` — Return a new :class:`Demo` containing only the matching scenes.
  - `from_dict(data: 'dict[str, Any]') -> 'Demo'` — Rebuild a :class:`Demo` from its :meth:`to_dict` mapping.
  - `from_file(path: 'str | Path') -> 'Demo'` — Load a :class:`Demo` from a ``.json`` or ``.yaml`` file.
  - `from_json(text: 'str') -> 'Demo'` — Parse a :class:`Demo` from a JSON string.
  - `from_yaml(text: 'str') -> 'Demo'` — Parse a :class:`Demo` from a YAML string.
  - `is_valid(self) -> 'bool'` — ``True`` iff :meth:`validate` returns no problems.
  - `iter_actions(self) -> 'list[Action]'` — Flat, ordered list of every action across all scenes/chunks.
  - `iter_chunks(self) -> 'list[Chunk]'` — Flat, ordered list of every chunk across all scenes.
  - `merge(self, other: 'Demo', *, offset: 'int' = 0) -> 'Demo'` — Append ``other``'s scenes onto this demo, returning a new :class:`Demo`.
  - `scene_by_id(self, scene_id: 'str') -> 'Scene | None'` — Return the first scene with ``id == scene_id``, or ``None``.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
  - `to_file(self, path: 'str | Path') -> 'Path'` — Write this demo to a ``.json`` or ``.yaml`` file and return its path.
  - `to_json(self, *, indent: 'int | None' = 2) -> 'str'` — Serialize to a JSON string.
  - `to_yaml(self) -> 'str'` — Serialize to a YAML string. Requires PyYAML (a core dependency).
  - `validate(self) -> 'list[str]'` — Return a list of human-readable structural problems (empty == valid).
- **`Scene`** *(dataclass)* — A logical chapter of the demo with a single capture strategy.
  - `estimated_duration_ms(self, wpm: 'int' = 150) -> 'int'` — Sum of chunk duration estimates.
  - `from_dict(data: 'dict[str, Any]') -> 'Scene'` — _(no docstring)_
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_
- **`SceneKind`** — The capture/render strategy a scene implies.
- **`WordTimestamp`** *(dataclass)* — A single word with millisecond start/end, produced by a transcriber.
  - `from_dict(data: 'dict[str, Any]') -> 'WordTimestamp'` — _(no docstring)_
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_

## `democreate.config`

Configuration and theming for DemoCreate renders.

### Classes

- **`AudioConfig`** *(dataclass)* — Voice and audio-assembly settings.
- **`MetadataConfig`** *(dataclass)* — Metadata labels and unsigned content association settings.
- **`RenderConfig`** *(dataclass)* — Top-level render configuration: theme + audio + video + metadata.
  - `commented_yaml(theme_name: 'str' = 'noir') -> 'str'` — Return a fully-commented default config YAML (for ``democreate config``).
  - `from_dict(data: 'dict[str, Any]') -> 'RenderConfig'` — Build a config from a (possibly partial) dict.
  - `from_file(path: 'Path | str') -> 'RenderConfig'` — Load a config from a YAML file.
  - `from_yaml(text: 'str') -> 'RenderConfig'` — Parse a config from YAML text.
  - `preset(theme_name: 'str' = 'noir') -> 'RenderConfig'` — Return a config using a named preset theme (default ``"noir"``).
  - `set_aspect(self, name: 'str') -> 'RenderConfig'` — Set ``video.width``/``video.height`` from a named aspect preset.
  - `set_resolution(self, name: 'str') -> 'RenderConfig'` — Set 16:9 ``video.width``/``video.height`` from a resolution tier.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain dict (colors stay as lists for YAML cleanliness).
  - `to_yaml(self) -> 'str'` — Serialize the config to YAML.
- **`Theme`** *(dataclass)* — Colors and font scale for rendered frames.
  - `from_dict(data: 'dict[str, Any]') -> 'Theme'` — Build a theme from a dict, coercing color lists to tuples.
- **`VideoConfig`** *(dataclass)* — Geometry and motion settings.

## `democreate.media`

Shared media value types used across capture, narration, and assembly.

### Classes

- **`AudioClip`** *(dataclass)* — A rendered narration audio file and its measured properties.
- **`FrameState`** *(dataclass)* — A renderable snapshot of the virtual environment at one instant.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_

## `democreate.pipeline`

End-to-end orchestration: a declarative :class:`Demo` becomes rendered output.

### Classes

- **`Pipeline`** — Configurable orchestrator over the DemoCreate subsystems.
  - `dry_run(self, demo: 'Demo') -> 'list[str]'` — Validate ``demo`` without running TTS, sync, or rendering.
  - `run(self, demo: 'Demo', workspace: 'Workspace | None' = None) -> 'PipelineResult'` — Render ``demo`` end-to-end, returning a :class:`PipelineResult`.
- **`PipelineResult`** *(dataclass)* — Paths and artifacts produced by a pipeline run.
  - `summary(self) -> 'dict[str, object]'` — A compact JSON-able summary of what was produced.

### Functions

- **`build_demo(demo: 'Demo', workspace: 'Workspace | None' = None, **kwargs: 'object') -> 'PipelineResult'`** — Convenience one-shot: construct a default :class:`Pipeline` and run it.
- **`render_video(result: 'PipelineResult', out_path: 'Path | None' = None, *, fps: 'int | None' = None, burn_captions: 'bool' = False, verify: 'bool' = True, animate: 'bool' = True, animation_fps: 'int | None' = None, config=None)`** — Assemble an audio-synced MP4 from a completed pipeline result.

## `democreate.portfolio`

Portfolio orchestration: a directory of repositories becomes a shelf of videos.

### Classes

- **`PortfolioReport`** *(dataclass)* — The result of a whole-directory portfolio run.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-ready dict.
- **`ProjectResult`** *(dataclass)* — Outcome of rendering one project.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-ready dict for the portfolio index.

### Functions

- **`build_project_demo(repo: 'Path', workspace, *, config=None, max_modules: 'int' = 6, title: 'str | None' = None)`** — Collect facts, render an architecture diagram, and build the summary demo.
- **`collect_project_facts(repo: 'Path', *, max_modules: 'int' = 6) -> 'ProjectFacts'`** — Walk ``repo`` and assemble its render-ready :class:`ProjectFacts`.
- **`collect_project_videos(output_root: 'Path', results: 'list[ProjectResult]') -> 'Path'`** — Copy every rendered project video into a flat ``project_videos/`` folder.
- **`discover_projects(projects_dir: 'Path', *, skip: 'tuple[str, ...]' = ()) -> 'list[Path]'`** — Return the sorted project directories under ``projects_dir``.
- **`render_portfolio(projects_dir: 'Path', output_root: 'Path', *, config=None, tts: 'str' = 'system', voice: 'str' = '', max_projects: 'int' = 0, max_modules: 'int' = 6, skip: 'tuple[str, ...]' = (), timestamp: 'str | None' = None, verify: 'bool' = True) -> 'PortfolioReport'`** — Render a summary video for every project under ``projects_dir``.
- **`render_project(repo: 'Path', output_root: 'Path', *, config=None, tts: 'str' = 'system', voice: 'str' = '', max_modules: 'int' = 6, timestamp: 'str | None' = None, verify: 'bool' = True) -> 'ProjectResult'`** — Render one repository to a timestamped, verified summary MP4.
- **`utc_stamp(now: 'datetime | None' = None) -> 'str'`** — Return a filesystem-safe UTC timestamp like ``20260625T164530Z``.

## `democreate.project_paths`

Path resolution for DemoCreate runs.

### Classes

- **`Workspace`** *(dataclass)* — Resolved output locations for one demo build.
  - `clean(self) -> 'None'` — Remove the entire workspace root if it exists (idempotent).
  - `ensure_safe(self) -> 'None'` — Refuse existing links in generated namespaces before local writes.

### Functions

- **`default_output_root() -> 'Path'`** — Return the conventional output root (``./output`` under the cwd).
- **`relativize_under_root(obj: 'Any', root: 'Path | str') -> 'Any'`** — Rewrite absolute-path strings under ``root`` to ``root``-relative POSIX form.
- **`stage_demo_assets(demo: 'Demo', workspace: 'Workspace', asset_root: 'Path') -> 'None'`** — Confine required backgrounds to an explicit root and stage portable copies.

## `democreate.errors`

Exception hierarchy for DemoCreate.

### Classes

- **`BackendUnavailableError`** — A requested optional backend is not installed.
- **`CaptureError`** — A screen, browser, or terminal capture step failed.
- **`DemoCreateError`** — Base class for every error DemoCreate raises deliberately.
- **`RenderError`** — A frame, video, or export render step failed.
- **`SchemaValidationError`** — A :class:`~democreate.schema.Demo` failed structural validation.
- **`SyncError`** — Audio/action synchronization failed (e.g. transcription mismatch).

## `democreate.evaluation`

Score supplied independent onset annotations without certifying an experiment.

### Classes

- **`SyncEvaluation`** *(dataclass)* — Diagnostic arithmetic and eligibility checks for one supplied cohort.
  - `to_dict(self) -> 'dict[str, Any]'` — Return the JSON-serializable report with its evidence limits attached.

### Functions

- **`load_sync_annotations(path: 'Path') -> 'SyncEvaluation'`** — Read strict JSON and score annotations without opening referenced media.
- **`score_sync_annotations(document: 'Mapping[str, Any]') -> 'SyncEvaluation'`** — Score one declared onset-annotation cohort under the existing H1 criteria.

## `democreate.api_docs`

Generate ``docs/api.md`` — a Markdown API reference for ``democreate``.

### Functions

- **`generate(out: 'Path') -> 'Path'`** — Write the API reference Markdown to ``out`` from the live package.
- **`is_public(name: 'str') -> 'bool'`** — Public names do not start with an underscore.
- **`members(module: 'object', kind: 'str') -> 'list[tuple[str, object]]'`** — Return sorted ``(name, obj)`` members of ``module`` that are defined in it.
- **`module_anchor(mod_name: 'str') -> 'str'`** — Return the stable Markdown anchor used for a documented module.
- **`render_module(mod_name: 'str') -> 'str'`** — Render the Markdown section for a single module.
- **`signature_of(obj: 'object') -> 'str'`** — Best-effort one-line signature; empty string if it cannot be introspected.
- **`summary(obj: 'object') -> 'str'`** — Return the first non-empty line of an object's docstring, or a placeholder.

## `democreate.manuscript`

Build the DemoCreate manuscript PDF from its declarative ``config.yaml``.

### Functions

- **`build_manuscript(config: 'Path', manuscript_dir: 'Path', output: 'Path', check: 'bool' = False) -> 'int'`** — Run the citation + figure gates and, unless ``check``, build the PDF.
- **`defined_bib_keys(bib: 'Path') -> 'set[str]'`** — Return the citation keys defined by a BibTeX ``references.bib``.
- **`extract_preamble(preamble_md: 'Path', out_tex: 'Path') -> 'Path'`** — Strip the ```latex fence from ``preamble.md`` into a raw ``.tex`` header.
- **`figure_insertions(chapters: 'list[Path]') -> 'list[str]'`** — The ``figures/x.png`` paths inserted as images across the chapters.
- **`load_config(path: 'Path') -> 'dict[str, Any]'`** — Load the manuscript ``config.yaml``.
- **`pick_engine() -> 'str'`** — Return the first available XeLaTeX-class PDF engine on ``PATH``.
- **`used_citation_keys(chapters: 'list[Path]') -> 'set[str]'`** — Citation keys actually used in prose (``[@key]`` / ``@key``), excluding

## `democreate.cli`

The ``democreate`` command-line interface.

### Functions

- **`backends() -> 'None'`** — List subsystem backends and whether their optional extras are installed.
- **`build(demo: 'Path', output: 'Path' = PosixPath('output'), tts: 'str' = 'auto', strict: 'bool' = True, asset_root: 'Path | None' = None) -> 'None'`** — Run the full pipeline: TTS, sync, frames, captions, and HTML player.
- **`captions(demo: 'Path', fmt: 'str' = 'srt') -> 'None'`** — Emit subtitles for a demo to stdout.
- **`config(out: 'Path' = PosixPath('democreate.yaml'), theme: 'str' = 'noir') -> 'None'`** — Write a fully-commented render-config YAML you can edit and pass to --config.
- **`fetch_voice() -> 'None'`** — Download the Kokoro neural-TTS model files (~340 MB) for `--tts kokoro`.
- **`init(path: 'Path' = PosixPath('demo.json'), fmt: 'str' = 'json') -> 'None'`** — Write a starter demo artifact you can edit and then ``build``.
- **`inspect(demo: 'Path', json_out: 'bool' = False) -> 'None'`** — Validate a demo and print a structural summary.
- **`localize(demo: 'Path', output: 'Path' = PosixPath('output'), audio_lang: 'str' = 'en', subtitle_lang: 'str' = 'ru', source_lang: 'str' = 'en', pairs: 'str' = '', translator: 'str' = 'ollama', model: 'str' = 'smollm2', host: 'str' = 'http://localhost:11434', tts: 'str' = 'kokoro', voice: 'str' = '', theme: 'str' = 'noir', resolution: 'str' = '', burn: 'bool' = False, asset_root: 'Path | None' = None) -> 'None'`** — Render localized videos — audio in one language, subtitles in another.
- **`main() -> 'None'`** — Entry point for the ``democreate`` console script.
- **`paper(pdf: 'Path', repo: 'Path' = None, figures: 'Path' = None, output: 'Path' = PosixPath('output'), pages: 'str' = '1', theme: 'str' = 'paper', voice: 'str' = '', tts: 'str' = 'system', aspect: 'str' = '', resolution: 'str' = '', author: 'str' = '', watermark: 'str' = '', max_figures: 'int' = 6, config: 'Path' = None, render_it: 'bool' = True) -> 'None'`** — Generate a narrated demo of a research paper (PDF + optional codebase).
- **`portfolio(projects_dir: 'Path', output: 'Path' = PosixPath('output'), tts: 'str' = 'system', voice: 'str' = '', theme: 'str' = 'noir', resolution: 'str' = '1080p', max_projects: 'int' = 0, max_modules: 'int' = 6, skip: 'str' = '') -> 'None'`** — Render a timestamped summary video for every project under a directory.
- **`score_sync(annotations: 'Path') -> 'None'`** — Score supplied onset annotations, not study independence or release readiness.
- **`tour(repo: 'Path', output: 'Path' = PosixPath('output'), title: 'str' = 'Codebase Tour', build_it: 'bool' = True, render_it: 'bool' = False, tts: 'str' = 'system', voice: 'str' = '', theme: 'str' = 'noir') -> 'None'`** — Generate a codebase tour demo from a repository (build and/or render it).
- **`version() -> 'None'`** — Print the installed DemoCreate version.

## `democreate.translation.translator`

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
- **`localized_captions(demo: 'Demo', translator: 'Translator', *, source: 'str', target: 'str', fmt: 'str' = 'srt', timing_demo: 'Demo | None' = None) -> 'str'`** — Emit subtitles in ``target`` from the **source** demo, with audio timing.
- **`translate_demo(demo: 'Demo', translator: 'Translator', *, source: 'str', target: 'str') -> 'Demo'`** — Translate chunk narration without modifying ``demo``.

## `democreate.translation.localize`

Render a demo with audio in one language and subtitles in another.

### Classes

- **`LocalizedResult`** *(dataclass)* — One localized render (one audio/subtitle language pair).
  - `to_dict(self) -> 'dict[str, object]'` — Serialize to a JSON-ready dict.

### Functions

- **`localize_batch(demo: 'Demo', workspace, *, pairs: 'list[tuple[str, str]]', source: 'str' = 'en', translator: 'Translator | None' = None, config=None, tts: 'str' = 'system', voice: 'str' = '', burn: 'bool' = False, verify: 'bool' = True, name: 'str | None' = None, asset_root: 'Path | None' = None) -> 'list[LocalizedResult]'`** — Render one localized video per ``(audio_lang, subtitle_lang)`` pair.
- **`localize_render(demo: 'Demo', workspace, *, languages: 'LanguageConfig', translator: 'Translator | None' = None, config=None, tts: 'str' = 'system', voice: 'str' = '', burn: 'bool' = False, verify: 'bool' = True, name: 'str | None' = None, asset_root: 'Path | None' = None) -> 'LocalizedResult'`** — Render one audio/subtitle language pair; return a :class:`LocalizedResult`.

## `democreate.narration.script`

Script generation: turning structured context into a declarative Demo.

### Classes

- **`LLMScriptGenerator`** — LLM-backed script generator (optional; never used in tests).
  - `generate(self, context: 'dict[str, Any]') -> 'Demo'` — Generate a demo via the configured LLM provider.
- **`ScriptGenerator`** — Abstract base for building a :class:`Demo` from input context.
  - `generate(self, context: 'dict[str, Any]') -> 'Demo'` — Build and return a :class:`Demo` from ``context``.
- **`TemplateScriptGenerator`** — Deterministic generator that maps a context dict to a :class:`Demo`.
  - `generate(self, context: 'dict[str, Any]') -> 'Demo'` — Build a :class:`Demo` from the template context dict.

### Functions

- **`generate_codebase_demo(summaries: 'list[Any]', *, title: 'str', max_scenes: 'int' = 0) -> 'Demo'`** — Build a codebase-tour :class:`Demo` from a list of module summaries.

## `democreate.narration.project_summary`

Project-summary script generation: a repo's facts become a narrated ``Demo``.

### Classes

- **`KeyModule`** *(dataclass)* — One load-bearing module selected for a code scene.
- **`ProjectFacts`** *(dataclass)* — The structured, render-ready facts about one software project.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a plain JSON-ready dict (for the portfolio index).

### Functions

- **`generate_project_summary_demo(facts: 'ProjectFacts', *, title: 'str | None' = None, architecture_image: 'str | None' = None, width: 'int' = 1920, height: 'int' = 1080, fps: 'int' = 30, voice: 'str' = 'default', max_modules: 'int' = 6, max_packages: 'int' = 6) -> 'Demo'`** — Build a narrated project-summary :class:`Demo` from collected facts.

## `democreate.narration.tts`

Text-to-speech backends for DemoCreate narration.

### Classes

- **`ChatterboxTTSBackend`** — Unwired Chatterbox slot; no published extra enables this adapter.
  - `is_available(self) -> 'bool'` — Return whether the ``chatterbox`` package is installed.
  - `synthesize(self, text: 'str', out_path: 'Path', *, voice: 'str | None' = None) -> 'AudioClip'` — Refuse unavailable or unwired Chatterbox synthesis explicitly.
- **`ElevenLabsTTSBackend`** — Hosted ElevenLabs speech synthesis with a configured API account.
  - `is_available(self) -> 'bool'` — Return whether the ``elevenlabs`` package AND an API key are present.
  - `synthesize(self, text: 'str', out_path: 'Path', *, voice: 'str | None' = None) -> 'AudioClip'` — Synthesize ``text`` via ElevenLabs and write a canonical WAV.
- **`KokoroTTSBackend`** — Local Kokoro neural TTS backed by an optional ONNX Runtime model.
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
- **`get_tts_backend(name: 'str' = 'auto', *, voice: 'str | None' = None, lang: 'str | None' = None, rate_wpm: 'int | None' = None) -> 'TTSBackend'`** — Return a TTS backend by name.
- **`measure_wav_duration_ms(path: 'Path | str') -> 'int'`** — Return the true duration of a WAV file in milliseconds.
- **`synthesize_demo(demo: 'Demo', workspace, backend: 'TTSBackend | None' = None) -> 'list[AudioClip]'`** — Synthesize audio for every chunk of ``demo`` into the workspace.

## `democreate.narration.sync`

Measure clip windows and estimate word/action times from supplied narration.

### Classes

- **`HeuristicTranscriber`** — Deterministic stdlib transcriber that distributes words over real audio.
  - `transcribe(self, audio_path: 'Path', text: 'str | None' = None) -> 'list[WordTimestamp]'` — Distribute the words of ``text`` across the audio's real duration.
- **`Transcriber`** — Abstract base for turning audio + known text into word timestamps.
  - `transcribe(self, audio_path: 'Path', text: 'str | None' = None) -> 'list[WordTimestamp]'` — Return per-word timestamps for ``audio_path``.
- **`WhisperTranscriber`** — Unwired Whisper adapter slot; installing its dependency is insufficient.
  - `transcribe(self, audio_path: 'Path', text: 'str | None' = None) -> 'list[WordTimestamp]'` — Refuse unavailable or unwired Whisper transcription explicitly.

### Functions

- **`absolute_word_timestamps(demo: 'Demo', clips: 'list[AudioClip]', transcriber: 'Transcriber | None' = None, *, lead_ms: 'int' = 0, gap_ms: 'int' = 0) -> 'list[WordTimestamp]'`** — Return every word of the demo timestamped on the absolute timeline.
- **`get_transcriber(name: 'str' = 'auto') -> 'Transcriber'`** — Return a transcriber by name.
- **`sync_demo(demo: 'Demo', clips: 'list[AudioClip]', transcriber: 'Transcriber | None' = None, *, lead_ms: 'int' = 0, gap_ms: 'int' = 0) -> 'Demo'`** — Assign absolute timestamps to every chunk and action from real audio.

## `democreate.narration.llm`

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

## `democreate.assembly.animator`

Timed-frame animation: turn one-frame-per-chunk into smooth, dynamic video.

### Classes

- **`AnimationConfig`** *(dataclass)* — Settings for timed-frame animation.
  - `from_video(video, theme=None, audio=None) -> 'AnimationConfig'` — Build animation settings from video (+ optional theme/audio) config.
  - `validate(self) -> 'None'` — Reject timing values that cannot match a fixed-cadence audio render.

### Functions

- **`active_index_at(windows: 'list[tuple[int, int]]', t_ms: 'int') -> 'int'`** — Return the index of the chunk active at ``t_ms`` (gap- and end-aware).
- **`chunk_timing(clips: 'list[AudioClip]', *, lead_ms: 'int' = 0, gap_ms: 'int' = 0, trail_ms: 'int' = 0) -> 'tuple[list[tuple[int, int]], int]'`** — Return per-chunk spoken ``(start_ms, end_ms)`` windows and the total duration.
- **`frame_hold_durations(clips: 'list[AudioClip]', *, lead_ms: 'int' = 0, gap_ms: 'int' = 0, trail_ms: 'int' = 0) -> 'list[int]'`** — Return static frame holds aligned to measured speech and padded audio.
- **`render_animation_frames(frame_paths: 'list[Path]', clips: 'list[AudioClip]', voiceover_wav: 'Path', out_dir: 'Path', *, size: 'tuple[int, int]', config: 'AnimationConfig | None' = None, scene_ids: 'list[str] | None' = None, kenburns_flags: 'list[bool] | None' = None, frame_states: 'list | None' = None, timeline_entries: 'list[TimelineEntry] | None' = None, typing_flags: 'list[bool] | None' = None, theme=None, overlay_meta=None, demo_title: 'str' = '', draw_captions: 'bool' = True, rerender_states: 'bool' = True) -> 'tuple[list[Path], int]'`** — Render uniform-cadence animated frames with motion: typing, cursor, waveform.

## `democreate.assembly.audio`

Voiceover post-processing for the assembly stage.

### Functions

- **`apply_fade(in_path: 'Path', out_path: 'Path', *, fade_ms: 'int' = 180) -> 'Path'`** — Apply a fade-in and fade-out to ``in_path`` with ffmpeg's ``afade``.
- **`concat_with_gaps(wav_paths: 'list[Path]', out_path: 'Path', *, gap_ms: 'int' = 0, lead_ms: 'int' = 0, trail_ms: 'int' = 0) -> 'Path'`** — Concatenate WAV clips in order, inserting silent gaps and lead/trail.
- **`ffmpeg_audio_available() -> 'bool'`** — Report whether the ``ffmpeg`` binary is on ``PATH``.
- **`measure_duration_ms(wav_path: 'Path') -> 'int'`** — Return the true duration of ``wav_path`` in milliseconds.
- **`normalize_audio(in_path: 'Path', out_path: 'Path', *, i: 'float' = -16.0, tp: 'float' = -1.5, lra: 'float' = 11.0) -> 'Path'`** — Loudness-normalize ``in_path`` with ffmpeg's ``loudnorm`` filter.
- **`write_silence(out_path: 'Path', ms: 'int', *, sample_rate: 'int' = 22050) -> 'Path'`** — Write a silent 16-bit mono PCM WAV of ``ms`` milliseconds.

## `democreate.assembly.captions`

Pure subtitle/caption formatting.

### Functions

- **`to_ass(demo: 'Demo', *, wpm: 'int' = 150) -> 'str'`** — Render the demo's narration as a minimal Advanced SubStation (``.ass``).
- **`to_srt(demo: 'Demo', *, wpm: 'int' = 150) -> 'str'`** — Render the demo's narration as a SubRip (``.srt``) document.
- **`to_vtt(demo: 'Demo', *, wpm: 'int' = 150) -> 'str'`** — Render the demo's narration as a WebVTT (``.vtt``) document.
- **`word_timestamps_to_srt(words: 'list[WordTimestamp]') -> 'str'`** — Render word-level timestamps as a karaoke-granularity SRT document.

## `democreate.assembly.compositor`

Timeline construction and compositor backends.

### Classes

- **`Compositor`** — Abstract base for everything that turns a :class:`Timeline` into output.
  - `compose(self, timeline: 'Timeline', workspace: 'Workspace') -> 'Path'` — Render ``timeline`` into ``workspace`` and return the primary artifact.
- **`ManifestCompositor`** — The deterministic default compositor (core deps only).
  - `compose(self, timeline: 'Timeline', workspace: 'Workspace') -> 'Path'` — Write the render manifest and per-entry frames.
- **`MoviePyCompositor`** — Guarded legacy MoviePy compositor slot (extra: ``video``).
  - `compose(self, timeline: 'Timeline', workspace: 'Workspace') -> 'Path'` — Detect the legacy MoviePy compositor dependency.
- **`Timeline`** *(dataclass)* — A fully-resolved, non-overlapping render timeline.
  - `entry_at_ms(self, t: 'int') -> 'TimelineEntry | None'` — Return the entry whose window contains ``t``.
  - `frame_count(self) -> 'int'` — Total number of frames at this timeline's fps.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize the whole timeline to a JSON-ready dict.
- **`TimelineEntry`** *(dataclass)* — One narration window, with a final still and scheduled scene playback.
  - `state_at_ms(self, t_ms: 'int', *, typing: 'bool' = True) -> 'FrameState'` — Return an independent scene snapshot at absolute ``t_ms``.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-ready dict.

### Functions

- **`build_timeline(demo: 'Demo', *, fps: 'int | None' = None, wpm: 'int' = 150, trail_ms: 'int' = 0) -> 'Timeline'`** — Build measured narration windows and an event-sourced scene timeline.

## `democreate.assembly.effects`

Pure Pillow image effects for the assembly stage.

### Functions

- **`crossfade(a: '_ImageModule.Image', b: '_ImageModule.Image', t: 'float') -> '_ImageModule.Image'`** — Blend from image ``a`` to image ``b``.
- **`fade(image: '_ImageModule.Image', alpha: 'float') -> '_ImageModule.Image'`** — Fade ``image`` toward black.
- **`highlight_box(image: '_ImageModule.Image', box: 'tuple[int, int, int, int]', *, color: 'tuple[int, int, int]' = (255, 214, 0), width: 'int' = 4) -> '_ImageModule.Image'`** — Draw a rectangular highlight outline on a copy of ``image``.
- **`lower_third(image: '_ImageModule.Image', text: 'str', *, height: 'int' = 120) -> '_ImageModule.Image'`** — Overlay a translucent caption band ("lower third") at the bottom.

## `democreate.capture.screen`

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

## `democreate.capture.browser`

Browser driving for WEBSITE scenes — deterministic by default.

### Classes

- **`BrowserDriver`** — Abstract browser automation surface.
  - `click(self, selector: 'str') -> 'None'` — Click the first element matching ``selector``.
  - `click_xy(self, x: 'int', y: 'int', *, button: 'str' = 'left') -> 'None'` — Click viewport coordinates using the requested mouse button.
  - `close(self) -> 'None'` — Release any browser resources.
  - `fill(self, selector: 'str', value: 'str') -> 'None'` — Fill the field matching ``selector`` with ``value``.
  - `navigate(self, url: 'str') -> 'None'` — Load ``url`` in the browser.
  - `screenshot(self, path: 'Path | str') -> 'Path'` — Capture the current page to ``path``.
  - `scroll(self, direction: 'str', amount: 'int') -> 'None'` — Scroll ``amount`` pixels up, down, left, or right.
- **`NullBrowserDriver`** — Deterministic, dependency-free browser driver.
  - `click(self, selector: 'str') -> 'None'` — Record a click on ``selector``.
  - `click_xy(self, x: 'int', y: 'int', *, button: 'str' = 'left') -> 'None'` — Record a coordinate click without inventing an element selector.
  - `close(self) -> 'None'` — Record that the driver was closed (idempotent).
  - `fill(self, selector: 'str', value: 'str') -> 'None'` — Record filling ``selector`` with the canonical ``value``.
  - `navigate(self, url: 'str') -> 'None'` — Record a navigation and update the tracked URL.
  - `screenshot(self, path: 'Path | str') -> 'Path'` — Render a synthetic browser frame to ``path``.
  - `scroll(self, direction: 'str', amount: 'int') -> 'None'` — Record a directional scroll after validating its pixel delta.
- **`PlaywrightBrowserDriver`** — Real browser automation via Playwright (extra: ``browser``).
  - `click(self, selector: 'str') -> 'None'` — Click the element matching ``selector``.
  - `click_xy(self, x: 'int', y: 'int', *, button: 'str' = 'left') -> 'None'` — Click actual viewport coordinates with the requested mouse button.
  - `close(self) -> 'None'` — Close the page, browser, and Playwright context.
  - `fill(self, selector: 'str', value: 'str') -> 'None'` — Fill the field matching ``selector`` with ``value``.
  - `navigate(self, url: 'str') -> 'None'` — Load ``url`` in the real page.
  - `screenshot(self, path: 'Path | str') -> 'Path'` — Capture the real page to ``path`` and return it.
  - `scroll(self, direction: 'str', amount: 'int') -> 'None'` — Apply directional pixel scrolling to the real page.

### Functions

- **`drive_website_scene(scene: 'Scene', driver: 'BrowserDriver | None' = None) -> 'list[dict[str, Any]]'`** — Translate a WEBSITE scene's actions into driver calls.

## `democreate.capture.replay`

Input record/replay — a pure event model with guarded real backends.

### Classes

- **`EventLog`** *(dataclass)* — An ordered log of input events.
  - `from_json(text: 'str') -> 'EventLog'` — Parse an :class:`EventLog` from a JSON string.
  - `to_actions(self) -> 'list[Action]'` — Map events onto schema actions for the render pipeline.
  - `to_json(self, *, indent: 'int | None' = 2) -> 'str'` — Serialize the log to a JSON string.
- **`InputEvent`** *(dataclass)* — A single recorded input event.
  - `from_dict(data: 'dict[str, Any]') -> 'InputEvent'` — Inverse of :meth:`to_dict`.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-ready dict.

### Functions

- **`record_session(duration_s: 'float' = 5.0, *, out_path: 'Path | str | None' = None) -> 'EventLog'`** — Record a live mouse/keyboard session (extra: ``replay``).
- **`replay_session(log: 'EventLog', *, speed: 'float' = 1.0) -> 'None'`** — Replay a recorded session onto the live desktop (extra: ``replay``).

## `democreate.capture.terminal`

Terminal recordings in asciinema asciicast v2 format (pure Python).

### Classes

- **`AsciicastEvent`** *(dataclass)* — One terminal event at a relative time.
  - `from_list(item: 'list') -> 'AsciicastEvent'` — Build an event from a ``[time, kind, data]`` triple.
  - `to_list(self) -> 'list'` — Return the ``[time, kind, data]`` triple used on disk.
- **`AsciicastRecording`** *(dataclass)* — An asciicast v2 recording: a header plus a stream of events.
  - `duration(self) -> 'float'` — Return the time of the last event (0.0 for an empty recording).
  - `from_json(text: 'str') -> 'AsciicastRecording'` — Parse a recording from asciicast v2 newline-delimited JSON.
  - `header(self) -> 'dict'` — Return the asciicast v2 header object.
  - `to_json(self) -> 'str'` — Serialize to asciicast v2 newline-delimited JSON.

### Functions

- **`record_commands(commands: 'list[tuple[str, str]]', *, prompt: 'str' = '$ ') -> 'AsciicastRecording'`** — Build a deterministic recording from ``(command, output)`` pairs.
- **`recording_to_frame_states(rec: 'AsciicastRecording') -> 'list[FrameState]'`** — Project a recording into terminal frame states for the renderer.

## `democreate.animation.waveform`

Speech-waveform visualization for demo frames.

### Functions

- **`compute_envelope(wav_path: 'Path', bars: 'int') -> 'list[float]'`** — Reduce a 16-bit PCM WAV file to ``bars`` normalized RMS amplitudes.
- **`draw_waveform(draw: 'ImageDraw.ImageDraw', box: 'tuple[int, int, int, int]', envelope: 'list[float]', *, progress: 'float' = 1.0, bar_color: 'tuple[int, int, int]' = (90, 110, 130), played_color: 'tuple[int, int, int]' = (80, 200, 255), playhead_color: 'tuple[int, int, int]' = (240, 245, 255), gap: 'int' = 2) -> 'None'`** — Draw a mirrored-bar waveform with a played/unplayed split and a playhead.
- **`render_waveform_strip(envelope: 'list[float]', size: 'tuple[int, int]', *, progress: 'float' = 1.0, bg: 'tuple[int, int, int]' = (15, 18, 26)) -> 'Image.Image'`** — Render a full-frame waveform strip image.

## `democreate.animation.diagram`

Architecture / overview diagram renderer for demo frames.

### Classes

- **`DiagramNode`** *(dataclass)* — A single labeled box inside an architecture column.

### Functions

- **`democreate_architecture_image(size: 'tuple[int, int]' = (1920, 1080), *, bg: 'tuple[int, int, int]' = (13, 17, 23), accent: 'tuple[int, int, int]' = (56, 139, 253), fg: 'tuple[int, int, int]' = (230, 237, 243)) -> 'Image.Image'`** — Render the canonical DemoCreate architecture as a diagram.
- **`render_architecture_diagram(size: 'tuple[int, int]', *, title: 'str', columns: 'list[tuple[str, list[DiagramNode]]]', bg: 'tuple[int, int, int]' = (13, 17, 23), accent: 'tuple[int, int, int]' = (56, 139, 253), fg: 'tuple[int, int, int]' = (230, 237, 243)) -> 'Image.Image'`** — Render a clean left-to-right architecture diagram.

## `democreate.animation.fonts`

Scalable, host-independent fonts from Pillow's bundled default face.

### Functions

- **`scaled_font(frame_height: 'int', ratio: 'float', *, mono: 'bool' = False) -> 'ImageFont.FreeTypeFont'`** — Load a font sized to a fraction of the frame height.

## `democreate.animation.highlights`

Syntax-highlighted code rendering for demo frames.

### Functions

- **`highlight_to_svg(code: 'str', *, language: 'str' = 'python', theme: 'str' = 'monokai', line_numbers: 'bool' = True) -> 'str'`** — Render ``code`` to a syntax-highlighted SVG string.
- **`highlight_to_text(code: 'str', *, language: 'str' = 'python') -> 'str'`** — Render ``code`` to plain text via ``rich`` (line numbers included).
- **`render_code_image(code: 'str', *, language: 'str' = 'python', size: 'tuple[int, int]' = (1280, 720), highlight_lines: 'tuple[int, ...]' = ())`** — Render ``code`` to a Pillow image on a fixed character grid.

## `democreate.animation.zoom`

Cursor-following zoom and pan math.

### Classes

- **`ZoomKeyframe`** *(dataclass)* — A virtual-camera state at one instant.

### Functions

- **`apply_zoom(image, kf: 'ZoomKeyframe')`** — Crop around the keyframe center and resize back to the original size.
- **`compute_zoom_path(cursor_points: 'list[tuple[int, int, int]]', frame_size: 'tuple[int, int]', *, zoom: 'float' = 1.6, hold_ms: 'int' = 400) -> 'list[ZoomKeyframe]'`** — Build a zoom keyframe track that follows the cursor.
- **`ease_in_out_cubic(t: 'float') -> 'float'`** — Cubic ease-in-out.
- **`ease_in_out_quad(t: 'float') -> 'float'`** — Quadratic ease-in-out.
- **`interpolate(keyframes: 'list[ZoomKeyframe]', t_ms: 'int', *, easing: 'Callable[[float], float]' = democreate.animation.zoom.ease_in_out_cubic) -> 'ZoomKeyframe'`** — Sample camera state at time ``t_ms`` by easing between bracketing keyframes.
- **`linear(t: 'float') -> 'float'`** — Identity easing.

## `democreate.animation.manim_scenes`

Manim code-walkthrough scene specs.

### Functions

- **`build_code_scene_spec(code: 'str', *, title: 'str' = '', language: 'str' = 'python') -> 'dict[str, Any]'`** — Build a JSON-serializable manim code-walkthrough scene description.
- **`render_manim_scene(spec: 'dict[str, Any]', out_path: 'Path') -> 'Path'`** — Render a scene spec to a video file using manim.

## `democreate.codebase.walker`

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

## `democreate.codebase.dependency`

Module dependency graphs built from import statements.

### Classes

- **`DependencyGraph`** *(dataclass)* — A directed dependency graph over module names.
  - `add_edge(self, source: 'str', target: 'str') -> 'None'` — Add a directed edge, creating endpoints as needed.
  - `add_node(self, node: 'str') -> 'None'` — Add a node if not already present.
  - `find_cycles(self) -> 'list[list[str]]'` — Find directed cycles via depth-first search.
  - `neighbors(self, node: 'str') -> 'list[str]'` — Return the direct successors of ``node`` (its dependencies).
  - `to_dot(self) -> 'str'` — Render the graph as a Graphviz DOT document.
  - `topological_order(self) -> 'list[str]'` — Return nodes in dependency order (dependencies before dependents).

### Functions

- **`build_import_graph(root: 'Path', *, package: 'str | None' = None) -> 'DependencyGraph'`** — Build an intra-package import dependency graph for a repository.

## `democreate.codebase.ast_viz`

Text and Graphviz visualization of module summaries.

### Functions

- **`module_to_tree(summary: 'ModuleSummary') -> 'str'`** — Render one module summary as an indented text tree.
- **`repository_to_dot(summaries: 'list[ModuleSummary]') -> 'str'`** — Render a repository's module summaries as a Graphviz DOT graph.

## `democreate.paper.extract`

Structured summarization of a research paper from its PDF + figures.

### Classes

- **`PaperSummary`** *(dataclass)* — A compact, render-ready summary of a research paper.
  - `to_dict(self) -> 'dict[str, Any]'` — Serialize to a JSON-friendly dict (figure paths as strings).

### Functions

- **`collect_figures(figures_dir: 'Path', *, limit: 'int | None' = None) -> 'list[Path]'`** — Collect sorted figure images from a directory (non-recursive).
- **`summarize_paper(pdf: 'Path', *, figures_dir: 'Path | None' = None, max_abstract_chars: 'int' = 900) -> 'PaperSummary'`** — Build a :class:`PaperSummary` from a PDF and optional figures directory.

## `democreate.paper.structure`

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

## `democreate.paper.script`

Build a narrated :class:`~democreate.schema.Demo` from a research paper.

### Functions

- **`build_paper_demo(summary: 'PaperSummary', *, code_summaries: 'list | None' = None, page_images: 'list[Path] | None' = None, architecture_image: 'Path | None' = None, figure_captions: 'list | None' = None, sections: 'list | None' = None, width: 'int' = 1920, height: 'int' = 1080, fps: 'int' = 30, voice: 'str' = '', max_figures: 'int' = 6) -> 'Demo'`** — Assemble a narrated demo from a paper summary and optional code/pages.
- **`chunk_sentences(text: 'str', *, max_words: 'int' = 26) -> 'list[str]'`** — Split prose into narration-sized chunks at sentence boundaries.

## `democreate.paper.pdf`

Poppler command-line wrapper for reading and rasterizing PDFs.

### Functions

- **`extract_text(pdf: 'Path', *, first: 'int | None' = None, last: 'int | None' = None) -> 'str'`** — Extract text from a (range of) PDF page(s) via ``pdftotext``.
- **`pdf_info(pdf: 'Path') -> 'dict[str, str]'`** — Return ``pdfinfo`` metadata as a dict of lowercased keys.
- **`pdf_page_count(pdf: 'Path') -> 'int'`** — Return the number of pages in ``pdf``.
- **`poppler_available() -> 'bool'`** — Report whether the required poppler binaries are installed.
- **`render_page(pdf: 'Path', page: 'int', out_path: 'Path', *, dpi: 'int' = 150) -> 'Path'`** — Rasterize a single PDF page to a PNG via ``pdftoppm``.
- **`render_pages(pdf: 'Path', out_dir: 'Path', *, pages: 'list[int] | None' = None, dpi: 'int' = 150, prefix: 'str' = 'page') -> 'list[Path]'`** — Rasterize several PDF pages to ``out_dir/<prefix>_<NNN>.png``.

## `democreate.export.video`

Video and GIF export.

### Functions

- **`assemble_video(frame_paths: 'list[Path]', durations_ms: 'list[int]', audio_path: 'Path | None', out_path: 'Path', *, fps: 'int' = 30, size: 'tuple[int, int] | None' = None, subtitles: 'Path | None' = None, crf: 'int' = 18, preset: 'str' = 'medium') -> 'Path'`** — Encode an audio-synced MP4 holding each frame for its measured duration.
- **`build_concat_demuxer_file(frames_with_durations: 'list[tuple[Path, float]]', *, repeat_last: 'bool' = True) -> 'str'`** — Build an ffmpeg concat-demuxer script holding each frame for its duration.
- **`build_ffmpeg_command(frames_glob: 'str', audio_path: 'str | None', out_path: 'Path', *, fps: 'int' = 30, start_number: 'int | None' = None, frame_count: 'int | None' = None) -> 'list[str]'`** — Construct the ``ffmpeg`` argv list for an H.264 MP4 encode.
- **`concat_wavs(wav_paths: 'list[Path]', out_path: 'Path') -> 'Path'`** — Concatenate canonical WAV clips gap-free into one track (pure stdlib).
- **`encode_frame_sequence(frame_paths: 'list[Path]', audio_path: 'Path | None', out_path: 'Path', *, fps: 'int' = 15, captions: 'Path | None' = None, crf: 'int' = 18, preset: 'str' = 'medium') -> 'Path'`** — Encode uniformly-timed frames (+ audio) into an MP4 via the image2 demuxer.
- **`export_video(frame_paths: 'list[Path]', audio_path: 'Path | None', out_path: 'Path', *, fps: 'int' = 30) -> 'Path'`** — Encode frames (+ optional audio) into an MP4.
- **`ffmpeg_available() -> 'bool'`** — Return ``True`` if the ``ffmpeg`` binary is on ``PATH``.
- **`frames_to_gif(frame_paths: 'list[Path]', out_path: 'Path', *, fps: 'int' = 10) -> 'Path'`** — Assemble an animated GIF from still frames using Pillow.

## `democreate.export.verify`

Content-asserting verification for rendered video.

### Classes

- **`VideoReport`** *(dataclass)* — The result of content-asserting verification of a video file.
  - `to_dict(self) -> 'dict[str, Any]'` — _(no docstring)_

### Functions

- **`parse_ffprobe(probe: 'dict[str, Any]', *, path: 'Path', expected_width: 'int | None' = None, expected_height: 'int | None' = None, min_duration_s: 'float' = 1.0, min_audio_ratio: 'float' = 0.9) -> 'VideoReport'`** — Build a :class:`VideoReport` from parsed ``ffprobe -of json`` output (pure).
- **`verify_video(path: 'Path', *, expected_width: 'int | None' = None, expected_height: 'int | None' = None, min_duration_s: 'float' = 1.0, check_content: 'bool' = True) -> 'VideoReport'`** — Run full content-asserting verification on a real video file.

## `democreate.export.chapters`

Chapter-marker export for narrated demos.

### Functions

- **`embed_chapters(mp4_in: 'Path', ffmetadata: 'Path', mp4_out: 'Path') -> 'Path'`** — Mux chapter metadata into an MP4 with ffmpeg.
- **`measured_chapters(demo: 'Demo', clips, *, lead_ms=0, gap_ms=0, trail_ms=0)`** — Return scene chapters aligned to the *measured* audio timeline.
- **`to_ffmetadata(demo: 'Demo', *, chapters=None, total_ms=None) -> 'str'`** — Build an ffmpeg ``FFMETADATA1`` document from a demo's scenes.
- **`to_youtube_chapters(demo: 'Demo', *, chapters=None) -> 'str'`** — Build a YouTube chapter list from a demo's scenes.
- **`write_chapters(demo: 'Demo', out_dir: 'Path', *, chapters=None, total_ms=None) -> 'dict[str, Path]'`** — Write both chapter formats to disk.

## `democreate.export.poster`

Poster/thumbnail frame and GIF preview export.

### Functions

- **`demo_to_gif(frame_paths: 'list[Path]', out_path: 'Path', *, fps: 'int' = 8, max_frames: 'int' = 48) -> 'Path'`** — Build an animated GIF preview by evenly sampling a frame sequence.
- **`render_poster(demo: 'Demo', out_path: 'Path', *, size: 'tuple[int, int]' = (1920, 1080), theme: 'Theme | None' = None, subtitle: 'str | None' = None) -> 'Path'`** — Render a designed poster/thumbnail PNG for a demo.

## `democreate.export.interactive`

Export a caption/chapter HTML preview with optional local frame images.

### Functions

- **`build_timeline(demo: 'Demo') -> 'dict'`** — Build a deterministic caption/chapter timeline from a demo.
- **`export_html_player(demo: 'Demo', timeline: 'dict | None', out_path: 'Path', *, frames_dir: 'str | None' = None) -> 'Path'`** — Render a caption/chapter preview referencing sibling frame assets.

## `democreate.export.formats`

Document-format exports for a :class:`~democreate.schema.Demo`.

### Functions

- **`export_pdf(demo: 'Demo', out_path: 'Path') -> 'Path'`** — Render the demo transcript to a styled PDF.
- **`to_chapters(demo: 'Demo') -> 'list[dict]'`** — Build a chapter list for players and YouTube descriptions.
- **`to_json(demo: 'Demo', *, indent: 'int' = 2, relative_to: 'Path | str | None' = None) -> 'str'`** — Serialize the demo to JSON.
- **`to_markdown(demo: 'Demo', *, format: 'str' = 'full') -> 'str'`** — Render the demo as a readable Markdown transcript.

## `democreate.export.metadata`

MP4 container metadata tags — provenance written into the video container.

### Functions

- **`build_tags(demo: 'Demo', meta: 'MetadataConfig | None' = None, *, version: 'str' = '') -> 'dict[str, str]'`** — Build a dict of ffmpeg container metadata tags from a demo (+ config).
- **`embed_tags(mp4_in: 'Path', mp4_out: 'Path', tags: 'dict[str, str]') -> 'Path'`** — Write container metadata into an MP4 by stream-copying through ffmpeg.
- **`ffmpeg_metadata_args(tags: 'dict[str, str]') -> 'list[str]'`** — Build a flat ``-metadata k=v`` argv fragment for direct ffmpeg use.
- **`to_ffmetadata(tags: 'dict[str, str]') -> 'str'`** — Render tags as an ffmpeg ``;FFMETADATA1`` global-metadata document.

## `democreate.export.overlay`

On-screen top/bottom metadata bars — a broadcast-style provenance overlay.

### Classes

- **`OverlayInfo`** *(dataclass)* — Resolved text for the on-screen metadata bars.

### Functions

- **`draw_footer(image: 'Image.Image', info: 'OverlayInfo', *, accent: 'RGB' = (56, 139, 253), fg: 'RGB' = (235, 238, 243), bg: 'RGB' = (0, 0, 0)) -> 'None'`** — Draw a slim translucent bottom bar of provenance, above the frame edge.
- **`draw_header(image: 'Image.Image', info: 'OverlayInfo', *, accent: 'RGB' = (56, 139, 253), fg: 'RGB' = (235, 238, 243), bg: 'RGB' = (0, 0, 0)) -> 'None'`** — Draw a slim translucent top bar: title (left) and section (right).
- **`format_clock(t_ms: 'int', total_ms: 'int') -> 'str'`** — Format a ``current / total`` time readout for the footer clock.
- **`from_metadata_config(meta: 'MetadataConfig', *, title: 'str' = '', section: 'str' = '', clock: 'str' = '') -> 'OverlayInfo'`** — Build an :class:`OverlayInfo` from a :class:`MetadataConfig`.

## `democreate.export.stego`

LSB steganography and unsigned content-association records for lossless frames.

### Functions

- **`build_provenance(demo: 'Demo', *, author: 'str' = '', version: 'str' = '', extra: 'dict[str, Any] | None' = None) -> 'dict[str, Any]'`** — Build a JSON-able provenance record for ``demo``.
- **`capacity_bytes(size: 'tuple[int, int]') -> 'int'`** — Return the maximum payload size, in bytes, for an image of ``size``.
- **`embed(image: 'Image.Image', payload: 'bytes') -> 'Image.Image'`** — Return a copy of ``image`` with ``payload`` hidden in its RGB LSBs.
- **`embed_provenance(image: 'Image.Image', demo: 'Demo', *, author: 'str' = '', version: 'str' = '', extra: 'dict[str, Any] | None' = None) -> 'tuple[Image.Image, dict[str, Any]]'`** — Build a provenance record and embed it into ``image``.
- **`extract(image: 'Image.Image') -> 'bytes'`** — Recover the payload hidden in ``image`` by :func:`embed`.
- **`extract_provenance(image: 'Image.Image') -> 'dict[str, Any]'`** — Extract and JSON-decode the provenance record from ``image``.
- **`verify_provenance(image: 'Image.Image', demo: 'Demo') -> 'bool'`** — Return whether the unsigned hidden content hash matches ``demo``.
