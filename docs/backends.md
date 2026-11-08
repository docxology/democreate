# Backend readiness: implemented paths, prerequisites and unwired slots

Core Python **3.15** is pinned for development; package support starts at
**3.11.5**, with **Pillow ≥13**. Core packages are `pyyaml`, `typer`, `rich`,
`jinja2` and `pillow`. Fixed inputs/assets/config/runtime yield deterministic
silent WAVs, synthetic PNGs, captions, manifests and a timed HTML preview. That
preview does not play synthesized narration.

## Choose an implemented media path

| Capability | Implemented core or real path | Additional prerequisites |
|---|---|---|
| Core narration | `SilentTTSBackend`; `auto` and `silent` both select it | None; generated WAV duration is measured, but it has no spoken onsets |
| OS speech | `SystemTTSBackend` | Usable macOS `say` or Linux `espeak`/`espeak-ng`, plus ffmpeg or macOS afconvert for canonical WAV conversion |
| Local neural speech | `KokoroTTSBackend` | `tts` extra, compatible Python/ONNX runtime, local model and voices |
| Cloud speech | `ElevenLabsTTSBackend` | `elevenlabs` extra, `ELEVENLABS_API_KEY`, provider/network access |
| Word/action timing | `HeuristicTranscriber` | Known narration text; estimates character-weighted positions over measured WAV duration, not recognition |
| Screen pixels | `SyntheticRenderer` by default; `MssScreenCapture` for actual capture | `capture` extra and usable display/session for mss |
| Browser automation | `NullBrowserDriver` records synthetic calls; `PlaywrightBrowserDriver` drives a browser | `browser` extra and installed browser executable; explicitly select driver in library calls |
| Input hooks | Pure `EventLog`; real `record_session` / `replay_session` | `replay` extra, OS permissions/session; replay causes actual input effects |
| Python source analysis | stdlib `ast` walker, import graph, text/DOT output | No extra; does not execute the analyzed project |
| Frame animation | Pillow scheduled action replay, waveform, cursor and transitions | No animation extra; see [video](video.md) |
| MP4 encode/verify and audio filters | Direct native ffmpeg/ffprobe subprocesses | Both binaries on `PATH`; subtitle burn additionally needs subtitles/libass support |
| Research-paper ingestion | poppler `pdfinfo`, `pdftotext`, `pdftoppm` | Native poppler; no `pdf` pip extra and no core PDF fallback |
| Transcript PDF export | WeasyPrint | `docs` extra and its native dependencies; Markdown export is core |
| Translation | `IdentityTranslator` no-op; `OllamaTranslator` HTTP client | Explicitly running server and acquired model for Ollama; no translation pip extra |

These are separate capabilities, not automatic upgrades to every pipeline stage.
Ordinary `build`/`render` uses synthetic visuals; installing capture/browser
packages does not turn authored virtual actions into live recordings.

## Unwired slots and package-only extras

| Surface | Current boundary |
|---|---|
| `WhisperTranscriber` / `whisper` extra | Dependency guard, then `NotImplementedError`; no acoustic recognizer |
| `ChatterboxTTSBackend` | Unwired; **no published extra** enables its synthesis |
| `render_manim_scene` / `animation` extra | JSON scene specs are core; real Manim rendering remains unwired |
| `MoviePyCompositor` / `video` extra | Legacy compositor raises `NotImplementedError` even when MoviePy is installed; direct ffmpeg export is implemented separately |
| `codebase` extra | Installs tree-sitter packages; current source walker remains Python AST, not a wired multi-language analyzer |

Install only prerequisites for an implemented path. `.[all]` is an aggregate
package request, not a ready-to-render configuration or a guarantee that all
packages support core Python 3.15.

## Inspecting backend state

```bash
democreate backends
```

Native rows say `found`/`absent`; the system TTS probe tests a short synthesis and
transcode. Optional rows say `module installed`/`module absent`. Neither a module
nor an ffmpeg executable proves model availability, browser/display permissions,
codec/filter support or successful execution. Unwired rows stay unwired when
installed. Missing guards raise `BackendUnavailableError` with `.backend` and,
where a real extra exists, `.extra`; dependency-present unwired calls fail
explicitly rather than falling back to fabricated output.

## Neural voice (Kokoro) — explicit runtime and model provisioning

Kokoro is an implemented local ONNX synthesis path, not a placeholder. The
historical identified voice run used Python **3.14.10**; the locked ONNX
distribution has no CPython 3.15 wheel. Use a separately compatible environment
without changing the core pin. In that environment:

```bash
uv pip install -e ".[tts]"
democreate fetch-voice
democreate render demo.json --tts kokoro --voice af_heart
```

`fetch-voice` explicitly downloads roughly 340 MB. Models are resolved from
`KOKORO_MODEL_PATH` and `KOKORO_VOICES_PATH`, then `DEMOCREATE_KOKORO_DIR`
(default `~/.cache/democreate/kokoro`). Both model and voice files are required;
subsequent synthesis can run locally. Unknown per-chunk voice names fall back to
the configured valid voice. Voice naturalness/speed depends on the environment;
no comparative quality or timing result follows from adapter availability. See
[identified media](videos.md) for the historical run, not a proof of this tree.

## Optional LLM narration

`narration.llm` is a library-only, stdlib `urllib` OpenAI-compatible client.
CLI template narration does not invoke it. Configure `OPENAI_API_KEY` or
`DEMOCREATE_LLM_API_KEY`; `DEMOCREATE_LLM_BASE_URL` defaults to
`https://api.openai.com/v1`. Calling it can transmit source narration externally;
there is no local-only guarantee. Rewritten text can lose trigger words and must
be reviewed before replacing authored content. See the
[opt-in recipe](recipes.md#8-optional-llm-narration-env-gated-library-only).

## Related media controls

[Audio](audio.md) owns WAV assembly and filters; [video](video.md) owns scheduled
animation, static holds, captions and media checks; [configuration](config.md)
owns defaults and precedence; [provenance](provenance.md) owns unsigned metadata
semantics. [Troubleshooting](troubleshooting.md) covers missing prerequisites.
