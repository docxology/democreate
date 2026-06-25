"""Narration subsystem: script generation, TTS, and TTS->STT sync.

This package owns the audio-narration half of a demo build:

* :mod:`~democreate.narration.script` — build a declarative
  :class:`~democreate.schema.Demo` from structured context (template default,
  codebase helper, optional LLM backend).
* :mod:`~democreate.narration.project_summary` — build a narrated
  project-summary :class:`~democreate.schema.Demo` from collected repository
  facts (deterministic, used by :mod:`democreate.portfolio`).
* :mod:`~democreate.narration.tts` — synthesize narration audio (deterministic
  silent default; a wired local **Kokoro** neural voice; a guarded Chatterbox slot).
* :mod:`~democreate.narration.sync` — derive word timestamps from real audio and
  anchor every action to its ``trigger_word`` (deterministic heuristic default;
  optional Whisper backend).

Every heavy capability has a pure-Python deterministic default so the entire
subsystem is import-safe and testable with only the core dependencies.
"""

from __future__ import annotations

from .project_summary import (
    KeyModule,
    ProjectFacts,
    generate_project_summary_demo,
)
from .script import (
    LLMScriptGenerator,
    ScriptGenerator,
    TemplateScriptGenerator,
    generate_codebase_demo,
)
from .sync import (
    HeuristicTranscriber,
    Transcriber,
    WhisperTranscriber,
    absolute_word_timestamps,
    get_transcriber,
    sync_demo,
)
from .tts import (
    ChatterboxTTSBackend,
    KokoroTTSBackend,
    SilentTTSBackend,
    SystemTTSBackend,
    TTSBackend,
    get_tts_backend,
    measure_wav_duration_ms,
    synthesize_demo,
)

__all__ = [
    # tts
    "TTSBackend",
    "SilentTTSBackend",
    "SystemTTSBackend",
    "KokoroTTSBackend",
    "ChatterboxTTSBackend",
    "get_tts_backend",
    "synthesize_demo",
    "measure_wav_duration_ms",
    # sync
    "Transcriber",
    "HeuristicTranscriber",
    "WhisperTranscriber",
    "get_transcriber",
    "sync_demo",
    "absolute_word_timestamps",
    # script
    "ScriptGenerator",
    "TemplateScriptGenerator",
    "LLMScriptGenerator",
    "generate_codebase_demo",
    # project_summary
    "generate_project_summary_demo",
    "ProjectFacts",
    "KeyModule",
]
