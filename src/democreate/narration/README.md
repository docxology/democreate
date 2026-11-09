# `democreate.narration`: scripts, WAV synthesis and estimated word timing

Templates/project facts construct authored Demo content; implemented TTS paths
write silent or spoken WAV clips; synchronization measures clip windows and
estimates word/action positions from known text. It does **not** recognize spoken
onsets by default. Abstract TTS/transcriber/script interfaces have core defaults,
but optional dependency presence is not implementation/model readiness. See
[backend prerequisites](../../../docs/backends.md).

## Modules

| Module | Responsibility |
|--------|----------------|
| `script.py` | Build a `Demo` from context (templates, codebase summaries). |
| `project_summary.py` | Build a *describing* project-summary `Demo` from collected repo facts (used by `democreate.portfolio`). |
| `tts.py`    | Synthesize narration audio to real WAV files (silent default, wired Kokoro neural voice). |
| `sync.py`   | Measure clip durations, interpolate known words and timestamp actions. |
| `llm.py`    | Optional LLM-backed script generation (guarded; no network by default). |

## Pipeline

```
context ──script.generate──▶ Demo
Demo ──tts.synthesize_demo──▶ [AudioClip]   (writes <workspace>/audio/chunk_NNNN.wav,
                                              sets chunk.audio_path)
Demo + clips ──sync.sync_demo──▶ Demo        (sets chunk start/duration and
                                              action time/duration/origin)
Demo + clips ──sync.absolute_word_timestamps──▶ [WordTimestamp]  (for captions)
```

## Public API

### `tts.py`
- `TTSBackend` (ABC): `name`, `is_available()`, `synthesize(text, out_path, *, voice=None) -> AudioClip`.
- `SilentTTSBackend` — **default**. Writes valid 16-bit mono PCM silence via the
  stdlib `wave` module. Duration estimated from word count at a configurable
  `wpm` (default 150, floor 300 ms). `sample_rate` default 22050.
- `SystemTTSBackend` — real OS voice with **zero pip dependencies** (macOS `say`,
  Linux `espeak`/`espeak-ng`); transcodes to canonical PCM WAV via `ffmpeg`
  (else macOS `afconvert`) and measures duration from the file.
- `KokoroTTSBackend` — **wired** neural voice (open-weight Kokoro via
  `kokoro-onnx`, fully local). Needs the `tts` extra plus the model files
  (`democreate fetch-voice`); resolves them from `KOKORO_MODEL_PATH`/
  `KOKORO_VOICES_PATH` or `~/.cache/democreate/kokoro`, else raises
  `BackendUnavailableError`. An unknown voice name falls back to a valid one.
- `ElevenLabsTTSBackend` — cloud voice via the light `elevenlabs` client (the
  `elevenlabs` extra) and an `ELEVENLABS_API_KEY` API key; raises
  `BackendUnavailableError(..., extra="elevenlabs")` at synthesis time when
  either is missing.
- `ChatterboxTTSBackend` — unwired slot. No published extra installs its engine
  or enables synthesis; missing dependencies carry no misleading `tts` hint.
- `get_tts_backend(name="auto") -> TTSBackend` — `"auto"`/`"silent"` → silent;
  `"system"`, `"kokoro"`, `"elevenlabs"`, `"chatterbox"` select the
  corresponding backend.
- `synthesize_demo(demo, workspace, backend=None) -> list[AudioClip]` — voices
  every chunk in order, mutating `chunk.audio_path`.
  IDs are opaque labels, not filenames: audio files are numbered in chunk order.
  Existing symbolic-link audio outputs are refused rather than followed.
- `fetch_kokoro_model(dest=None) -> tuple[Path, Path]` — explicit one-time download
  of the Kokoro model + voices into the cache dir (powers `democreate fetch-voice`).

### `sync.py`
- `Transcriber` (ABC): `transcribe(audio_path, text=None) -> list[WordTimestamp]`.
- `HeuristicTranscriber` — **default**, stdlib-only. Reads the WAV's true
  duration and lays words across it proportional to character length. `text=None`
  → `[]`.
- `WhisperTranscriber` — unwired slot (`extra="whisper"`); installed dependency
  still raises `NotImplementedError`, not acoustic recognition.
- `get_transcriber(name="auto") -> Transcriber`.
- `sync_demo(demo, clips, transcriber=None, *, lead_ms=0, gap_ms=0) -> Demo` — measured chunk
  windows and fuzzy, case-insensitive trigger matching. Explicit untriggered
  authored times survive; derived `timestamp_source="sync"` times refresh on
  re-synthesis. WAIT advances the fallback cursor. Unset action duration is
  600 ms; captured discrete inputs explicitly use zero.
- `absolute_word_timestamps(demo, clips, transcriber=None, *, lead_ms=0, gap_ms=0) -> list[WordTimestamp]`
  — flat absolute-ms word stream for captioning.

### `script.py`
- `ScriptGenerator` (ABC): `generate(context) -> Demo`.
- `TemplateScriptGenerator` — **default**, deterministic. One scene per `step`
  in `{"title", "steps": [{"narration", "kind", "actions": [...]}]}`.
  Action mappings use `Action.from_dict`: `timestamp_ms`, `timestamp_source`,
  `duration_ms` (including zero), `trigger_word` and `params` retain their schema
  meanings. Untriggered authored times survive sync; derived `"sync"` times
  refresh against narration. Existing `Action` objects retain their identity.
- `generate_codebase_demo(summaries, *, title) -> Demo` — duck-typed over
  `.name/.path/.functions/.classes` (objects **or** dicts). Emits `OPEN_FILE` +
  `HIGHLIGHT_LINES` actions. Does **not** import the codebase subsystem.
- `LLMScriptGenerator` — guarded provider abstraction (unconfigured →
  `BackendUnavailableError("llm")`), no network.

### `project_summary.py`
- `ProjectFacts` — pure data carrier for one project's render-ready facts (name,
  tagline, README bullets, module/LOC/class/function counts, top packages, key
  modules, run command).
- `KeyModule` — a load-bearing module selected for a code scene (name, path, real
  docstring, real source excerpt, symbol count).
- `generate_project_summary_demo(facts, *, title=None, architecture_image=None, …)
  -> Demo` — **deterministic, no I/O.** Builds the fixed seven-beat "describing"
  demo (title · README bullets · architecture · stats · key-code-from-real-docstrings
  · run · outro). Identical facts → byte-identical demo.

## Optional extras

| Backend | Dependency | pyproject extra |
|---------|-----------|-----------------|
| `SystemTTSBackend` | OS speech engine (`say` / `espeak`) | — (zero pip) |
| `KokoroTTSBackend` | wired neural voice (kokoro-onnx) | `tts` + model files |
| `ElevenLabsTTSBackend` | `elevenlabs` client + API key | `elevenlabs` |
| `ChatterboxTTSBackend` | unwired `chatterbox` slot | none; not enabled by `tts` |
| `WhisperTranscriber` | `whisper` adapter slot | `whisper` |
| `LLMScriptGenerator` | provider SDK | — (no pip extra) |

## Determinism

The silent/template/heuristic paths have no RNG, network or sleeping. Their
duration model is reproducible for fixed input/config/runtime, not an accuracy
measurement. Optional cloud/LLM calls are explicit network paths. Pipeline owns
input cloning; direct `synthesize_demo`/`sync_demo` mutate the supplied Demo.
Consumers of Pipeline must use `result.demo` for resolved timing and assets.

## Tests

`tests/narration/` — `test_tts.py`, `test_tts_system.py`, `test_tts_kokoro.py`,
`test_tts_elevenlabs.py`, `test_sync.py`, `test_script.py`, `test_llm.py`,
`test_project_summary.py` — real WAV I/O on temp files, no mocks.
