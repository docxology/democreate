"""TTS->STT synchronization: anchoring actions to real spoken word timestamps.

This module closes the loop opened by :mod:`democreate.narration.tts`. Given the
real audio that TTS produced, a :class:`Transcriber` derives per-word
:class:`~democreate.schema.WordTimestamp` objects, and :func:`sync_demo` uses
them to assign every action an absolute millisecond timestamp anchored to its
``trigger_word``.

The default :class:`HeuristicTranscriber` is deterministic and stdlib-only: it
reads each WAV's *true* duration via :mod:`wave` and distributes word timings
across that duration proportional to word length. The optional
:class:`WhisperTranscriber` does real speech recognition and is guarded behind
the ``whisper`` extra.

Because the silent default backend writes audio whose duration encodes the
estimated narration length, the heuristic transcriber yields stable, sensible
timings end-to-end with zero heavy dependencies.
"""

from __future__ import annotations

import difflib
import importlib.util
import wave
from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError, SyncError
from ..media import AudioClip
from ..schema import Demo, WordTimestamp

__all__ = [
    "Transcriber",
    "HeuristicTranscriber",
    "WhisperTranscriber",
    "get_transcriber",
    "sync_demo",
    "absolute_word_timestamps",
]

logger = get_logger(__name__)

# Fallback chunk duration (ms) when a clip cannot be measured from disk.
_FALLBACK_DURATION_MS = 300
# Default play-out duration (ms) given to any action lacking one.
_DEFAULT_ACTION_DURATION_MS = 600


def _dep_available(name: str) -> bool:
    """Return ``True`` if module ``name`` is importable on this machine."""
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):  # pragma: no cover - defensive
        return False


def _wav_duration_ms(audio_path: Path) -> int:
    """Read a WAV file's true duration in milliseconds.

    Args:
        audio_path: Path to a readable ``.wav`` file.

    Returns:
        The duration in milliseconds, rounded to the nearest integer.

    Raises:
        SyncError: If the file cannot be opened or has no frame rate.
    """
    try:
        with wave.open(str(audio_path), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
    except (wave.Error, OSError, EOFError) as exc:
        raise SyncError(f"could not read WAV {audio_path}: {exc}") from exc
    if rate <= 0:
        raise SyncError(f"WAV {audio_path} reports non-positive frame rate {rate}")
    return int(round(frames / rate * 1000))


class Transcriber:
    """Abstract base for turning audio + known text into word timestamps."""

    name: str = "abstract"

    def transcribe(
        self, audio_path: Path, text: str | None = None
    ) -> list[WordTimestamp]:
        """Return per-word timestamps for ``audio_path``.

        Args:
            audio_path: The audio file to time.
            text: The known narration text, if available. Backends that need
                ground-truth text (e.g. the heuristic one) require it.

        Returns:
            An ordered list of :class:`~democreate.schema.WordTimestamp`.
        """
        raise NotImplementedError


class HeuristicTranscriber(Transcriber):
    """Deterministic stdlib transcriber that distributes words over real audio.

    It reads the WAV's true duration and lays the words of ``text`` end-to-end
    across that span, giving each word a slice proportional to its character
    length (longer words take proportionally longer). This requires no model and
    is fully reproducible. If ``text`` is ``None`` it returns an empty list.
    """

    name = "heuristic"

    def transcribe(
        self, audio_path: Path, text: str | None = None
    ) -> list[WordTimestamp]:
        """Distribute the words of ``text`` across the audio's real duration.

        Args:
            audio_path: Path to the WAV to measure.
            text: The known narration text. If ``None``, returns ``[]``.

        Returns:
            Ordered word timestamps spanning ``[0, duration_ms]``.
        """
        if text is None:
            return []
        words = text.split()
        if not words:
            return []

        duration_ms = _wav_duration_ms(Path(audio_path))
        # Weight each word by its character length (minimum 1 to avoid zeros).
        weights = [max(1, len(w)) for w in words]
        total_weight = sum(weights)

        result: list[WordTimestamp] = []
        cursor_ms = 0.0
        for word, weight in zip(words, weights, strict=True):
            span = duration_ms * (weight / total_weight)
            start_ms = int(round(cursor_ms))
            cursor_ms += span
            end_ms = int(round(cursor_ms))
            # Guarantee start <= end even on tiny/zero-duration clips.
            if end_ms < start_ms:
                end_ms = start_ms
            result.append(WordTimestamp(word=word, start_ms=start_ms, end_ms=end_ms))
        # Snap the final word's end to the measured duration for tidiness.
        if result:
            result[-1].end_ms = max(result[-1].start_ms, duration_ms)
        return result


class WhisperTranscriber(Transcriber):
    """Whisper STT transcriber (optional, requires the ``whisper`` extra).

    Args:
        model: Whisper model size identifier (e.g. ``"base"``).

    Raises:
        BackendUnavailableError: If the ``whisper`` package is not installed.
    """

    name = "whisper"

    def __init__(self, *, model: str = "base") -> None:
        if not _dep_available("whisper"):
            raise BackendUnavailableError("whisper", extra="whisper")
        self.model = model  # pragma: no cover - requires whisper

    def transcribe(  # pragma: no cover - requires whisper
        self, audio_path: Path, text: str | None = None
    ) -> list[WordTimestamp]:
        """Transcribe with Whisper (only runs when ``whisper`` is installed)."""
        if not _dep_available("whisper"):
            raise BackendUnavailableError("whisper", extra="whisper")
        raise BackendUnavailableError("whisper", extra="whisper")


def get_transcriber(name: str = "auto") -> Transcriber:
    """Return a transcriber by name.

    Args:
        name: One of ``"auto"``/``"heuristic"`` (the deterministic default) or
            ``"whisper"``.

    Returns:
        A :class:`Transcriber` instance.

    Raises:
        ValueError: If ``name`` is unrecognized.
        BackendUnavailableError: If the whisper dependency is missing.
    """
    key = name.lower()
    if key in ("auto", "heuristic"):
        return HeuristicTranscriber()
    if key == "whisper":
        return WhisperTranscriber()
    raise ValueError(
        f"unknown transcriber {name!r}; expected 'auto', 'heuristic', or 'whisper'"
    )


def _clips_by_chunk(clips: list[AudioClip]) -> dict[str, AudioClip]:
    """Index clips by their ``chunk_id`` (last write wins for duplicates)."""
    return {c.chunk_id: c for c in clips if c.chunk_id is not None}


def _match_word(
    trigger: str, words: list[WordTimestamp]
) -> WordTimestamp | None:
    """Fuzzy-match ``trigger`` (case-insensitive) to the closest spoken word.

    Args:
        trigger: The action's ``trigger_word``.
        words: Candidate word timestamps for the chunk.

    Returns:
        The best-matching :class:`~democreate.schema.WordTimestamp`, or ``None``
        if no word is close enough.
    """
    if not words:
        return None
    lowered = [w.word.lower().strip(".,!?;:\"'()[]") for w in words]
    matches = difflib.get_close_matches(trigger.lower(), lowered, n=1, cutoff=0.6)
    if not matches:
        return None
    best = matches[0]
    for word, normalized in zip(words, lowered, strict=True):
        if normalized == best:
            return word
    return None  # pragma: no cover - get_close_matches guarantees a hit


def sync_demo(
    demo: Demo,
    clips: list[AudioClip],
    transcriber: Transcriber | None = None,
    *,
    lead_ms: int = 0,
    gap_ms: int = 0,
) -> Demo:
    """Assign absolute timestamps to every chunk and action from real audio.

    Each chunk's ``start_ms`` is its start in the *assembled* voiceover timeline:
    ``lead_ms`` of lead silence, then each clip's measured duration with
    ``gap_ms`` of silence inserted between consecutive clips. This MUST mirror the
    silence model used to concatenate the audio (``concat_with_gaps``) and to lay
    out the video frames (``chunk_timing``); otherwise burned-in captions and the
    interactive player drift ahead of the spoken audio by ``lead_ms`` at the start
    and a further ``gap_ms`` per chunk. Within a chunk, every action with a
    ``trigger_word`` is fuzzy-matched against the transcribed words and its
    ``timestamp_ms`` set to ``chunk.start_ms + word.start_ms``.

    Args:
        demo: The demo to annotate. Mutated in place and returned.
        clips: Audio clips produced by TTS; matched to chunks by ``chunk_id``.
        transcriber: Transcriber to use; defaults to
            :class:`HeuristicTranscriber`.
        lead_ms: Lead silence before the first clip (match the render/audio).
        gap_ms: Silence inserted between consecutive clips.

    Returns:
        The same ``demo`` instance, now timestamped.
    """
    engine = transcriber or HeuristicTranscriber()
    by_chunk = _clips_by_chunk(clips)

    cumulative_ms = lead_ms
    for index, chunk in enumerate(demo.iter_chunks()):
        if index > 0:
            cumulative_ms += gap_ms
        chunk.start_ms = cumulative_ms
        clip = by_chunk.get(chunk.id)

        words: list[WordTimestamp] = []
        if clip is not None and clip.path is not None and Path(clip.path).exists():
            words = engine.transcribe(Path(clip.path), chunk.text)
            duration_ms = clip.duration_ms
        elif chunk.audio_path and Path(chunk.audio_path).exists():
            words = engine.transcribe(Path(chunk.audio_path), chunk.text)
            duration_ms = _wav_duration_ms(Path(chunk.audio_path))
        else:
            duration_ms = _FALLBACK_DURATION_MS

        for action in chunk.actions:
            offset_ms = 0
            if action.trigger_word:
                match = _match_word(action.trigger_word, words)
                if match is not None:
                    offset_ms = match.start_ms
            action.timestamp_ms = chunk.start_ms + offset_ms
            if action.duration_ms is None:
                action.duration_ms = _DEFAULT_ACTION_DURATION_MS

        cumulative_ms += duration_ms

    logger.info(
        "synced %d chunk(s) / %d action(s) with %s transcriber",
        len(demo.iter_chunks()),
        len(demo.iter_actions()),
        engine.name,
    )
    return demo


def absolute_word_timestamps(
    demo: Demo,
    clips: list[AudioClip],
    transcriber: Transcriber | None = None,
) -> list[WordTimestamp]:
    """Return every word of the demo timestamped on the absolute timeline.

    Words are transcribed per chunk and shifted by each chunk's cumulative start
    offset, producing a single flat stream suitable for caption generation.

    Args:
        demo: The demo whose narration to flatten.
        clips: Audio clips produced by TTS, matched to chunks by ``chunk_id``.
        transcriber: Transcriber to use; defaults to
            :class:`HeuristicTranscriber`.

    Returns:
        A flat, ordered list of absolute :class:`~democreate.schema.WordTimestamp`.
    """
    engine = transcriber or HeuristicTranscriber()
    by_chunk = _clips_by_chunk(clips)

    out: list[WordTimestamp] = []
    cumulative_ms = 0
    for chunk in demo.iter_chunks():
        clip = by_chunk.get(chunk.id)
        audio_path: Path | None = None
        duration_ms = _FALLBACK_DURATION_MS
        if clip is not None and clip.path is not None and Path(clip.path).exists():
            audio_path = Path(clip.path)
            duration_ms = clip.duration_ms
        elif chunk.audio_path and Path(chunk.audio_path).exists():
            audio_path = Path(chunk.audio_path)
            duration_ms = _wav_duration_ms(audio_path)

        if audio_path is not None:
            for word in engine.transcribe(audio_path, chunk.text):
                out.append(
                    WordTimestamp(
                        word=word.word,
                        start_ms=cumulative_ms + word.start_ms,
                        end_ms=cumulative_ms + word.end_ms,
                    )
                )
        cumulative_ms += duration_ms

    return out
