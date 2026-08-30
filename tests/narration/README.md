# tests/narration/

Tests for the narration subsystem: TTS backends (system say/espeak default, Kokoro, ElevenLabs adapter), narration script generation, audio-anchored sync, LLM-assisted script helpers, and project summaries.

Mirrors `src/democreate/narration/` — run scoped:
`.venv/bin/python -m pytest -q tests/narration/`.
