# AGENTS — `democreate.narration`

Guidance for agents editing this subsystem. Read alongside `README.md`.

## What this subsystem is

The narration half of the build: `script`/`project_summary` → `Demo`, `tts` →
audio, `sync` → timestamps. `project_summary.py` builds the *describing*
project-summary demo consumed by `democreate.portfolio`; `tts.py` carries the
wired local Kokoro neural voice and the wired ElevenLabs cloud voice. It consumes the schema spine
(`Demo/Scene/Chunk/Action/WordTimestamp`) and the shared `AudioClip`; it never
redefines those types.

## Hard rules

1. **Deterministic default, always.** Each abstract base (`TTSBackend`,
   `Transcriber`, `ScriptGenerator`) has a pure-stdlib default
   (`SilentTTSBackend`, `HeuristicTranscriber`, `TemplateScriptGenerator`) that
   works with only core deps. Keep them import-safe and fully tested.
2. **No top-level heavy imports.** Detect optional deps with
   `importlib.util.find_spec(...)`. If a real backend method runs without its dep,
   raise `BackendUnavailableError("<dep>", extra="<extra>")`. Mark unrunnable
   bodies `# pragma: no cover`.
3. **Do not import the codebase subsystem.** `generate_codebase_demo` duck-types
   summaries via `getattr`/dict lookup (`.name/.path/.functions/.classes`) to avoid
   build-order coupling. Do not add a real import of `democreate.codebase`.
4. **Scope.** Only edit files under `src/democreate/narration/` and the
   `tests/narration/test_*.py` files (tts, sync, script, llm, project_summary).
   Never touch `schema.py`, `media.py`,
   `errors.py`, `_logging.py`, `project_paths.py`, `__init__.py` (package root),
   `pyproject.toml`, or `conftest.py`.

## Real WAV contract

`SilentTTSBackend` writes 16-bit mono PCM via the stdlib `wave` module. The
returned `AudioClip.duration_ms` is computed from frames actually written, so it
matches the file on disk exactly. `HeuristicTranscriber` and the sync functions
read the *true* duration back via `wave`, never the estimate — this keeps audio
and timeline consistent even if a clip is regenerated.

## Sync semantics (do not change without updating tests)

- `chunk.start_ms` = cumulative sum of preceding clip durations (chunk order).
- Action with a matching `trigger_word` → `chunk.start_ms + word.start_ms`.
- No trigger / no fuzzy match (`difflib`, cutoff 0.6, case-insensitive) →
  `chunk.start_ms`.
- Action `duration_ms` defaults to 600 ms only when unset (existing values kept).
- Clips matched to chunks by `chunk_id`; falls back to `chunk.audio_path`, then a
  300 ms per-chunk fallback when no audio exists.

## Verify before returning

```
cd <repo> && .venv/bin/python -m pytest \
  tests/narration/test_tts.py tests/narration/test_sync.py \
  tests/narration/test_script.py -p no:cacheprovider -q
```

Also keep ruff clean (`select = E,F,I,UP,B,W`, line-length 88, E501 ignored):
use `zip(..., strict=...)`, sorted imports, no useless expressions.
No mocks, no RNG, no network, no sleeping.
