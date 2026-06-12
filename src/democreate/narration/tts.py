"""Text-to-speech backends for DemoCreate narration.

Every TTS capability sits behind :class:`TTSBackend`, an abstract base class with
a pure-Python deterministic default — :class:`SilentTTSBackend` — that needs only
the standard library. It writes real, valid WAV files of digital silence whose
duration is estimated from the narration's word count. This keeps the whole
narration pipeline import-safe and fully testable with no heavy dependencies.

Neural engine slots (Kokoro, Chatterbox) are guarded: their constructors raise
:class:`~democreate.errors.BackendUnavailableError` when the optional dependency
is missing, and their synthesis bodies remain unavailable until the concrete
engine APIs are wired.

Example
-------
>>> backend = get_tts_backend("silent")
>>> # backend.synthesize("hello world", Path("out.wav"))  # writes real silence
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError
from ..media import AudioClip
from ..schema import Demo

__all__ = [
    "TTSBackend",
    "SilentTTSBackend",
    "SystemTTSBackend",
    "KokoroTTSBackend",
    "ChatterboxTTSBackend",
    "get_tts_backend",
    "synthesize_demo",
    "measure_wav_duration_ms",
]

logger = get_logger(__name__)

# Default synthesis parameters for the deterministic silent backend.
_DEFAULT_WPM = 150
_DEFAULT_SAMPLE_RATE = 22050
_MIN_DURATION_MS = 300
_SAMPLE_WIDTH_BYTES = 2  # 16-bit PCM
_CHANNELS = 1  # mono


def measure_wav_duration_ms(path: Path | str) -> int:
    """Return the true duration of a WAV file in milliseconds.

    Reads the file header with the stdlib :mod:`wave` module — no decoding of
    samples — so it is exact and cheap. This is the audio-as-ground-truth
    primitive: real synthesized speech has whatever duration it has, and the
    render timeline must be built from *this* number, never a word-count guess.

    Args:
        path: Path to a ``.wav`` file.

    Returns:
        Duration in milliseconds (rounded).

    Raises:
        DemoCreateError: If the file cannot be read as WAV.
    """
    from ..errors import DemoCreateError

    try:
        with wave.open(str(path), "rb") as wav:
            frames = wav.getnframes()
            rate = wav.getframerate()
        if rate <= 0:  # pragma: no cover - defensive
            raise DemoCreateError(f"WAV {path} has non-positive frame rate")
        return int(round(frames / rate * 1000))
    except wave.Error as exc:
        raise DemoCreateError(f"cannot read WAV duration from {path}: {exc}") from exc


def _dep_available(name: str) -> bool:
    """Return ``True`` if an importable module/package ``name`` is installed.

    Args:
        name: The top-level import name to probe (e.g. ``"kokoro"``).

    Returns:
        ``True`` if :func:`importlib.util.find_spec` locates the module.
    """
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):  # pragma: no cover - defensive
        return False


def _transcode_audio_file(src: Path, dst: Path, sample_rate: int) -> None:
    """Transcode ``src`` to canonical 16-bit mono PCM WAV at ``dst``."""
    if shutil.which("ffmpeg"):
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(src),
                "-ar", str(sample_rate), "-ac", "1",
                "-c:a", "pcm_s16le", str(dst),
            ],
            check=True,
            capture_output=True,
        )
    elif shutil.which("afconvert"):
        subprocess.run(
            [
                "afconvert", "-f", "WAVE", "-d", f"LEI16@{sample_rate}",
                "-c", "1", str(src), str(dst),
            ],
            check=True,
            capture_output=True,
        )
    else:
        raise BackendUnavailableError("ffmpeg/afconvert (audio transcode)", extra="video")


def _probe_system_tts(engine: str) -> bool:
    """Return whether ``engine`` can produce non-empty, transcodable speech."""
    if not (shutil.which("ffmpeg") or shutil.which("afconvert")):
        return False
    try:
        with tempfile.TemporaryDirectory(prefix="democreate-tts-") as tmp:
            root = Path(tmp)
            raw = root / ("probe.aiff" if engine == "say" else "probe.raw.wav")
            out = root / "probe.wav"
            if engine == "say":
                cmd = ["say", "-o", str(raw), "test"]
            else:
                cmd = [engine, "-w", str(raw), "test"]
            subprocess.run(cmd, check=True, capture_output=True, timeout=10)
            _transcode_audio_file(raw, out, _DEFAULT_SAMPLE_RATE)
            return (
                out.exists()
                and out.stat().st_size > 1000
                and measure_wav_duration_ms(out) >= 100
            )
    except Exception:  # pragma: no cover - host/system binary dependent
        return False


class TTSBackend:
    """Abstract base for a text-to-speech engine.

    Concrete backends turn narration text into a real audio file on disk and
    report its measured properties as an :class:`~democreate.media.AudioClip`.
    """

    name: str = "abstract"

    def is_available(self) -> bool:
        """Return whether this backend can actually synthesize on this machine.

        Returns:
            ``True`` if the backend's dependencies are present.
        """
        raise NotImplementedError

    def synthesize(
        self, text: str, out_path: Path, *, voice: str | None = None
    ) -> AudioClip:
        """Synthesize ``text`` to ``out_path`` and return the resulting clip.

        Args:
            text: Narration text to speak.
            out_path: Destination file path (a ``.wav`` for the default backend).
            voice: Optional voice identifier override.

        Returns:
            An :class:`~democreate.media.AudioClip` describing the written audio.
        """
        raise NotImplementedError


class SilentTTSBackend(TTSBackend):
    """Deterministic default backend that writes real WAV files of silence.

    The audio is valid 16-bit mono PCM at ``sample_rate`` Hz containing only
    zero samples. Its duration is estimated from the word count at ``wpm`` words
    per minute, floored at ``min_duration_ms``. Because it uses only the stdlib
    :mod:`wave` module, it is fully testable without any heavy dependency.

    Args:
        wpm: Words-per-minute pace used to estimate duration.
        sample_rate: Output sample rate in Hz.
        min_duration_ms: Minimum clip duration so empty text still reserves a beat.
    """

    name = "silent"

    def __init__(
        self,
        *,
        wpm: int = _DEFAULT_WPM,
        sample_rate: int = _DEFAULT_SAMPLE_RATE,
        min_duration_ms: int = _MIN_DURATION_MS,
    ) -> None:
        if wpm <= 0:
            raise ValueError(f"wpm must be positive, got {wpm}")
        if sample_rate <= 0:
            raise ValueError(f"sample_rate must be positive, got {sample_rate}")
        if min_duration_ms < 0:
            raise ValueError(
                f"min_duration_ms must be non-negative, got {min_duration_ms}"
            )
        self.wpm = wpm
        self.sample_rate = sample_rate
        self.min_duration_ms = min_duration_ms

    def is_available(self) -> bool:
        """Always ``True`` — the default backend uses only the standard library."""
        return True

    def estimate_duration_ms(self, text: str) -> int:
        """Estimate spoken duration of ``text`` in milliseconds.

        Args:
            text: Narration text.

        Returns:
            The estimated duration, never below ``min_duration_ms``.
        """
        words = len(text.split())
        if words == 0:
            return self.min_duration_ms
        estimated = int(round(words / self.wpm * 60_000))
        return max(estimated, self.min_duration_ms)

    def synthesize(
        self, text: str, out_path: Path, *, voice: str | None = None
    ) -> AudioClip:
        """Write a silent WAV of the estimated duration and return its clip.

        The returned ``duration_ms`` is computed from the frames actually written
        (so it is exact for the file on disk), and ``text`` is carried through.
        ``chunk_id`` is left ``None`` for the caller to set.

        Args:
            text: Narration text to "speak" (its length drives the duration).
            out_path: Destination ``.wav`` path; parent dirs are created.
            voice: Ignored by this backend (silence has no voice).

        Returns:
            An :class:`~democreate.media.AudioClip` for the written file.
        """
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        duration_ms = self.estimate_duration_ms(text)
        num_frames = max(1, int(round(self.sample_rate * duration_ms / 1000)))
        silence = b"\x00" * (num_frames * _SAMPLE_WIDTH_BYTES * _CHANNELS)

        with wave.open(str(out_path), "wb") as wav:
            wav.setnchannels(_CHANNELS)
            wav.setsampwidth(_SAMPLE_WIDTH_BYTES)
            wav.setframerate(self.sample_rate)
            wav.writeframes(silence)

        measured_ms = int(round(num_frames / self.sample_rate * 1000))
        logger.debug(
            "silent TTS wrote %d frames (%d ms) to %s",
            num_frames,
            measured_ms,
            out_path,
        )
        return AudioClip(
            path=out_path,
            duration_ms=measured_ms,
            sample_rate=self.sample_rate,
            text=text,
        )


@lru_cache(maxsize=1)
def _system_tts_command() -> str | None:
    """Return the first usable system TTS binary, or ``None``.

    Probes macOS ``say`` first, then Linux ``espeak-ng``/``espeak``. This is a
    *platform* backend, not a portable one — hence it is never the auto default.
    A binary only counts as usable after a short synthesis/transcode smoke test;
    some hosts expose ``say`` but produce an empty audio file.
    """
    for candidate in ("say", "espeak-ng", "espeak"):
        if shutil.which(candidate) and _probe_system_tts(candidate):
            return candidate
    return None


class SystemTTSBackend(TTSBackend):
    """Real-voice TTS using the operating system's built-in speech synthesizer.

    Uses macOS ``say`` or Linux ``espeak``/``espeak-ng`` — both ship with the OS,
    so this produces genuine spoken narration with **zero pip dependencies**. The
    raw output is transcoded (via ``ffmpeg`` when present, else macOS ``afconvert``)
    to canonical 16-bit mono PCM WAV at ``sample_rate`` Hz, and the returned
    duration is *measured from that file* — the audio is the ground truth for all
    downstream timing.

    Args:
        voice: System voice name (e.g. ``"Samantha"`` on macOS). ``None`` or an
            empty string uses the OS default voice.
        sample_rate: Canonical output sample rate in Hz.
        rate_wpm: Optional speaking rate (words per minute) passed to the engine.

    Raises:
        BackendUnavailableError: If no usable system TTS engine is found.
    """

    name = "system"

    def __init__(
        self,
        *,
        voice: str | None = None,
        sample_rate: int = _DEFAULT_SAMPLE_RATE,
        rate_wpm: int | None = None,
    ) -> None:
        engine = _system_tts_command()
        if engine is None:
            raise BackendUnavailableError("system-tts (say/espeak)", extra="tts")
        self._engine = engine
        self.voice = voice
        self.sample_rate = sample_rate
        self.rate_wpm = rate_wpm

    def is_available(self) -> bool:
        """Return whether a system TTS engine can synthesize usable audio."""
        return _system_tts_command() is not None

    def synthesize(  # pragma: no cover - requires system speech + transcoder binaries
        self, text: str, out_path: Path, *, voice: str | None = None
    ) -> AudioClip:
        """Speak ``text`` to a canonical WAV and return its *measured* clip.

        Empty/whitespace text falls back to a short silent clip so timing stays
        sane (the OS synthesizers reject empty input).
        """
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if not text.strip():
            return SilentTTSBackend(sample_rate=self.sample_rate).synthesize(
                text, out_path
            )

        chosen_voice = voice or self.voice
        if self._engine == "say":
            raw = out_path.with_suffix(".aiff")
            cmd = ["say"]
            if chosen_voice:
                cmd += ["-v", chosen_voice]
            if self.rate_wpm:
                cmd += ["-r", str(self.rate_wpm)]
            cmd += ["-o", str(raw), text]
            subprocess.run(cmd, check=True, capture_output=True)
            self._transcode(raw, out_path)
            raw.unlink(missing_ok=True)
        else:  # espeak / espeak-ng write WAV directly
            raw = out_path.with_suffix(".raw.wav")
            cmd = [self._engine, "-w", str(raw)]
            if chosen_voice:
                cmd += ["-v", chosen_voice]
            if self.rate_wpm:
                cmd += ["-s", str(self.rate_wpm)]
            cmd += [text]
            subprocess.run(cmd, check=True, capture_output=True)
            self._transcode(raw, out_path)
            raw.unlink(missing_ok=True)

        measured_ms = measure_wav_duration_ms(out_path)
        logger.info(
            "system TTS (%s) spoke %d ms to %s", self._engine, measured_ms, out_path
        )
        return AudioClip(
            path=out_path,
            duration_ms=measured_ms,
            sample_rate=self.sample_rate,
            text=text,
        )

    def _transcode(self, src: Path, dst: Path) -> None:  # pragma: no cover - binaries
        """Transcode ``src`` to canonical 16-bit mono PCM WAV at ``dst``."""
        _transcode_audio_file(src, dst, self.sample_rate)


class KokoroTTSBackend(TTSBackend):
    """Kokoro neural TTS backend (optional, requires the ``tts`` extra).

    Args:
        voice: Default Kokoro voice identifier.

    Raises:
        BackendUnavailableError: If the ``kokoro`` package is not installed.
    """

    name = "kokoro"

    def __init__(self, *, voice: str | None = None) -> None:
        if not _dep_available("kokoro"):
            raise BackendUnavailableError("kokoro", extra="tts")
        self.voice = voice  # pragma: no cover - requires kokoro

    def is_available(self) -> bool:
        """Return whether the ``kokoro`` package is installed."""
        return _dep_available("kokoro")

    def synthesize(  # pragma: no cover - requires kokoro
        self, text: str, out_path: Path, *, voice: str | None = None
    ) -> AudioClip:
        """Synthesize ``text`` with Kokoro (only runs when ``kokoro`` is present)."""
        if not _dep_available("kokoro"):
            raise BackendUnavailableError("kokoro", extra="tts")
        raise BackendUnavailableError("kokoro", extra="tts")


class ChatterboxTTSBackend(TTSBackend):
    """Chatterbox TTS backend (optional, requires the ``tts`` extra).

    Args:
        voice: Default Chatterbox voice identifier.

    Raises:
        BackendUnavailableError: If the ``chatterbox`` package is not installed.
    """

    name = "chatterbox"

    def __init__(self, *, voice: str | None = None) -> None:
        if not _dep_available("chatterbox"):
            raise BackendUnavailableError("chatterbox", extra="tts")
        self.voice = voice  # pragma: no cover - requires chatterbox

    def is_available(self) -> bool:
        """Return whether the ``chatterbox`` package is installed."""
        return _dep_available("chatterbox")

    def synthesize(  # pragma: no cover - requires chatterbox
        self, text: str, out_path: Path, *, voice: str | None = None
    ) -> AudioClip:
        """Synthesize ``text`` with Chatterbox (only runs when installed)."""
        if not _dep_available("chatterbox"):
            raise BackendUnavailableError("chatterbox", extra="tts")
        raise BackendUnavailableError("chatterbox", extra="tts")


def get_tts_backend(name: str = "auto", *, voice: str | None = None) -> TTSBackend:
    """Return a TTS backend by name.

    Args:
        name: One of ``"auto"``/``"silent"`` (the deterministic default),
            ``"system"`` (real OS voice via ``say``/``espeak``), ``"kokoro"``, or
            ``"chatterbox"``. ``"auto"`` selects the always-available silent
            backend so the pipeline never fails to run.
        voice: Optional voice id forwarded to voiced backends.

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
        return KokoroTTSBackend(voice=voice)
    if key == "chatterbox":
        return ChatterboxTTSBackend(voice=voice)
    raise ValueError(
        f"unknown TTS backend {name!r}; expected one of "
        "'auto', 'silent', 'system', 'kokoro', 'chatterbox'"
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
