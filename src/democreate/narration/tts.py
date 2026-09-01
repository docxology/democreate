"""Text-to-speech backends for DemoCreate narration.

Every TTS capability sits behind :class:`TTSBackend`, an abstract base class with
a pure-Python deterministic default — :class:`SilentTTSBackend` — that needs only
the standard library. It writes real, valid WAV files of digital silence whose
duration is estimated from the narration's word count. This keeps the whole
narration pipeline import-safe and fully testable with no heavy dependencies.

:class:`KokoroTTSBackend` is a **wired**, fully-local neural voice (the open-weight
Kokoro model via ``kokoro-onnx``); it raises
:class:`~democreate.errors.BackendUnavailableError` only when the ``tts`` extra or
the model files are absent (fetch them with ``democreate fetch-voice``).
:class:`ElevenLabsTTSBackend` is a **wired** cloud voice (the ``elevenlabs`` extra);
it needs the ``elevenlabs`` package and an ``ELEVENLABS_API_KEY`` and fails with a
clear, typed error when either is missing — never a silent empty WAV.
:class:`ChatterboxTTSBackend` remains a guarded adapter slot whose synthesis is not
yet wired.

This module is the stable import surface for the narration TTS subsystem; the
implementation lives in cohesive private siblings:

- :mod:`democreate.narration._tts_audio` — WAV measurement, transcoding, probes,
  and the dependency probe.
- :mod:`democreate.narration._tts_kokoro` — Kokoro model paths, downloads, and
  synthesis/segmentation helpers.
- :mod:`democreate.narration._tts_backends` — the concrete backend classes and
  the ElevenLabs defaults.

Example
-------
>>> backend = get_tts_backend("silent")
>>> # backend.synthesize("hello world", Path("out.wav"))  # writes real silence
"""

from __future__ import annotations

from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError  # noqa: F401 (re-export)
from ..media import AudioClip
from ..schema import Demo
from ._tts_audio import (  # noqa: F401 (re-exports)
    _DEFAULT_SAMPLE_RATE,
    _DEFAULT_WPM,
    _MIN_DURATION_MS,
    _dep_available,
    _probe_system_tts,
    _transcode_audio_file,
    measure_wav_duration_ms,
)
from ._tts_backends import (  # noqa: F401 (re-exports)
    _ELEVENLABS_DEFAULT_MODEL,
    _ELEVENLABS_DEFAULT_VOICE,
    _ELEVENLABS_FORMAT_MAP,
    _ELEVENLABS_MODELS,
    ChatterboxTTSBackend,
    ElevenLabsTTSBackend,
    KokoroTTSBackend,
    SilentTTSBackend,
    SystemTTSBackend,
    TTSBackend,
    _resolve_elevenlabs_voice_id,
    _system_tts_command,
)
from ._tts_kokoro import (  # noqa: F401 (re-exports)
    _KOKORO_DEFAULT_VOICE,
    _KOKORO_MODEL_NAMES,
    _KOKORO_VOICES_NAMES,
    _kokoro_cache_dir,
    _kokoro_model_paths,
    _kokoro_synth_segment,
    _split_for_tts,
    fetch_kokoro_model,
)

__all__ = [
    "TTSBackend",
    "SilentTTSBackend",
    "SystemTTSBackend",
    "KokoroTTSBackend",
    "ElevenLabsTTSBackend",
    "ChatterboxTTSBackend",
    "get_tts_backend",
    "synthesize_demo",
    "measure_wav_duration_ms",
    "fetch_kokoro_model",
]

logger = get_logger(__name__)


def get_tts_backend(
    name: str = "auto", *, voice: str | None = None, lang: str | None = None
) -> TTSBackend:
    """Return a TTS backend by name.

    Args:
        name: One of ``"auto"``/``"silent"`` (the deterministic default),
            ``"system"`` (real OS voice via ``say``/``espeak``), ``"kokoro"``
            (local neural), ``"elevenlabs"`` (cloud, needs a key), or
            ``"chatterbox"``. ``"auto"`` selects the always-available silent
            backend so the pipeline never fails to run.
        voice: Optional voice id forwarded to voiced backends.
        lang: Optional language code for Kokoro (e.g. ``"en-us"``, ``"es"``) so
            non-English audio is phonemized in the right language.

    Returns:
        A :class:`TTSBackend` instance.

    Raises:
        ValueError: If ``name`` is not a recognized backend.
        BackendUnavailableError: If a guarded backend's dependency is missing.
    """
    key = name.lower()
    if key in ("auto", "silent"):
        return SilentTTSBackend()
    if key == "system":
        return SystemTTSBackend(voice=voice)
    if key == "kokoro":
        return KokoroTTSBackend(voice=voice, lang=lang or "en-us")
    if key == "elevenlabs":
        return ElevenLabsTTSBackend(voice_id=voice or None)
    if key == "chatterbox":
        return ChatterboxTTSBackend(voice=voice)
    raise ValueError(
        f"unknown TTS backend {name!r}; expected one of "
        "'auto', 'silent', 'system', 'kokoro', 'elevenlabs', 'chatterbox'"
    )


def synthesize_demo(
    demo: Demo, workspace, backend: TTSBackend | None = None
) -> list[AudioClip]:
    """Synthesize audio for every chunk of ``demo`` into the workspace.

    Each chunk's narration is rendered to ``<workspace.audio>/<chunk.id>.wav``,
    the chunk's ``audio_path`` is set to that file's string path, and the
    returned clips carry their ``chunk_id``. Clips are returned in chunk order.

    Args:
        demo: The demo whose chunks to voice. Mutated in place (``audio_path``).
        workspace: A :class:`~democreate.project_paths.Workspace` providing the
            ``audio`` output directory.
        backend: TTS backend to use; defaults to :class:`SilentTTSBackend`.

    Returns:
        A list of :class:`~democreate.media.AudioClip`, one per chunk in order.
    """
    engine = backend or SilentTTSBackend()
    clips: list[AudioClip] = []
    audio_dir = Path(workspace.audio)
    for chunk in demo.iter_chunks():
        out_path = audio_dir / f"{chunk.id}.wav"
        clip = engine.synthesize(chunk.text, out_path, voice=chunk.voice or demo.voice)
        clip.chunk_id = chunk.id
        chunk.audio_path = str(out_path)
        clips.append(clip)
    logger.info("synthesized %d chunk(s) with %s backend", len(clips), engine.name)
    return clips
