# `democreate.narration`

The narration subsystem owns the audio half of a demo build: turning structured
input into a declarative `Demo`, voicing each chunk to real audio, and anchoring
every action to the spoken word that triggers it.

Every heavy capability sits behind an abstract base class with a **pure-Python
deterministic default** that needs only the core dependencies. The whole
subsystem is import-safe and fully testable with no heavy backends installed.

## Modules

| Module | Responsibility |
|--------|----------------|
| `script.py` | Build a `Demo` from context (templates, codebase summaries). |
| `project_summary.py` | Build a *describing* project-summary `Demo` from collected repo facts (used by `democreate.portfolio`). |
| `tts.py`    | Synthesize narration audio to real WAV files (silent default, wired Kokoro neural voice). |
| `sync.py`   | Derive word timestamps from real audio and timestamp every action. |
| `llm.py`    | Optional LLM-backed script generation (guarded; no network by default). |

## Pipeline

```
context ──script.generate──▶ Demo
Demo ──tts.synthesize_demo──▶ [AudioClip]   (writes <workspace>/audio/<chunk>.wav,
                                              sets chunk.audio_path)
Demo + clips ──sync.sync_demo──▶ Demo        (sets chunk.start_ms and
                                              action.timestamp_ms / duration_ms)
Demo + clips ──sync.absolute_word_timestamps──▶ [WordTimestamp]  (for captions)
```

## Public API

### `tts.py`
- `TTSBackend` (ABC): `name`, `is_available()`, `synthesize(text, out_path, *, voice=None) -> AudioClip`.
- `SilentTTSBackend` — **default**. Writes valid 16-bit mono PCM silence via the
  stdlib `wave` module. Duration estimated from word count at a configurable
  `wpm` (default 150, floor 300 ms). `sample_rate` default 22050.
- `KokoroTTSBackend` — **wired** neural voice (open-weight Kokoro via
  `kokoro-onnx`, fully local). Needs the `tts` extra plus the model files
  (`democreate fetch-voice`); resolves them from `KOKORO_MODEL_PATH`/
  `KOKORO_VOICES_PATH` or `~/.cache/democreate/kokoro`, else raises
  `BackendUnavailableError`. An unknown voice name falls back to a valid one.
- `ChatterboxTTSBackend` — guarded adapter slot; constructor raises
  `BackendUnavailableError(..., extra="tts")` until its engine API is wired.
- `get_tts_backend(name="auto") -> TTSBackend` — `"auto"`/`"silent"` → silent.
- `synthesize_demo(demo, workspace, backend=None) -> list[AudioClip]` — voices
  every chunk in order, mutating `chunk.audio_path`.
- `fetch_kokoro_model(dest=None) -> tuple[Path, Path]` — explicit one-time download
  of the Kokoro model + voices into the cache dir (powers `democreate fetch-voice`).

### `sync.py`
- `Transcriber` (ABC): `transcribe(audio_path, text=None) -> list[WordTimestamp]`.
- `HeuristicTranscriber` — **default**, stdlib-only. Reads the WAV's true
  duration and lays words across it proportional to character length. `text=None`
  → `[]`.
- `WhisperTranscriber` — guarded adapter slot (`extra="whisper"`).
- `get_transcriber(name="auto") -> Transcriber`.
- `sync_demo(demo, clips, transcriber=None) -> Demo` — cumulative `chunk.start_ms`,
  fuzzy `trigger_word` matching (`difflib`, case-insensitive), default action
  duration 600 ms.
- `absolute_word_timestamps(demo, clips, transcriber=None) -> list[WordTimestamp]`
  — flat absolute-ms word stream for captioning.

### `script.py`
- `ScriptGenerator` (ABC): `generate(context) -> Demo`.
- `TemplateScriptGenerator` — **default**, deterministic. One scene per `step`
  in `{"title", "steps": [{"narration", "kind", "actions": [...]}]}`.
- `generate_codebase_demo(summaries, *, title) -> Demo` — duck-typed over
  `.name/.path/.functions/.classes` (objects **or** dicts). Emits `OPEN_FILE` +
  `HIGHLIGHT_LINES` actions. Does **not** import the codebase subsystem.
- `LLMScriptGenerator` — guarded provider abstraction (`extra="llm"`), no network.

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
| `KokoroTTSBackend` | wired neural voice (kokoro-onnx) | `tts` + model files |
| `ChatterboxTTSBackend` | `chatterbox` adapter slot | `tts` |
| `WhisperTranscriber` | `whisper` adapter slot | `whisper` |
| `LLMScriptGenerator` | provider SDK | `llm` |

## Determinism

No RNG, no network, no sleeping. The silent backend's audio duration encodes the
estimated narration length, so the heuristic transcriber produces stable, sensible
timings end to end — the same input always yields the same `Demo`.

## Tests

`tests/narration/test_tts.py`, `tests/narration/test_sync.py`,
`tests/narration/test_script.py` — real WAV I/O on temp files, no mocks.
