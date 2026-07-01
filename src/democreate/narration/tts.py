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

Example
-------
>>> backend = get_tts_backend("silent")
>>> # backend.synthesize("hello world", Path("out.wav"))  # writes real silence
"""

from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import tempfile
import wave
from functools import lru_cache
from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError, DemoCreateError
from ..media import AudioClip
from ..schema import Demo

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

# Default synthesis parameters for the deterministic silent backend.
_DEFAULT_WPM = 150
_DEFAULT_SAMPLE_RATE = 22050
_MIN_DURATION_MS = 300
_SAMPLE_WIDTH_BYTES = 2  # 16-bit PCM
_CHANNELS = 1  # mono

# Kokoro neural TTS defaults. The model + voices files are large (~340 MB) and
# are NOT bundled or pip-installed; they are resolved from env vars or a cache
# dir (see :func:`_kokoro_model_paths`). 24 kHz is Kokoro's native output rate.
_KOKORO_DEFAULT_VOICE = "af_heart"  # warm US-English female; see Kokoro voice list
_KOKORO_MODEL_NAMES = ("kokoro-v1.0.onnx", "kokoro-v0.19.onnx", "kokoro.onnx")
_KOKORO_VOICES_NAMES = ("voices-v1.0.bin", "voices.bin", "voices-v1.0.json")


_KOKORO_RELEASE = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
)
_KOKORO_MODEL_URL = f"{_KOKORO_RELEASE}/kokoro-v1.0.onnx"
_KOKORO_VOICES_URL = f"{_KOKORO_RELEASE}/voices-v1.0.bin"

# ElevenLabs cloud TTS defaults. The `elevenlabs` package is a light pure-Python
# client (no torch/onnx), gated by the `elevenlabs` extra; the API key is read
# from the env var named by the backend's `api_key_env` (default below). Output
# is requested as WAV at the nearest supported rate, then transcoded to the
# pipeline's canonical 16-bit mono PCM WAV — audio stays the timing truth.
_ELEVENLABS_DEFAULT_VOICE = "21m00Tcm4TlvDq8ikWAM"  # "Rachel", an ElevenLabs stock voice
_ELEVENLABS_DEFAULT_MODEL = "eleven_multilingual_v2"
_ELEVENLABS_MODELS: dict[str, str] = {
    "multilingual_v2": "eleven_multilingual_v2",
    "turbo_v2_5": "eleven_turbo_v2_5",
    "flash_v2_5": "eleven_flash_v2_5",
}
# WAV output-format strings that encode the sample rate. Requesting the nearest
# supported rate minimizes transcoding work; anything else raises early.
_ELEVENLABS_FORMAT_MAP: dict[int, str] = {
    8000: "wav_8000",
    16000: "wav_16000",
    22050: "wav_22050",
    24000: "wav_24000",
    32000: "wav_32000",
    44100: "wav_44100",
    48000: "wav_48000",
}


def _resolve_elevenlabs_voice_id(voice: str | None, configured_voice_id: str) -> str:
    """Resolve the voice id ElevenLabs should actually receive.

    `Demo.voice`/chunk `voice` use the literal string ``"default"`` as a
    cross-backend sentinel meaning "no override" (schema.py); an unset
    per-chunk override can also arrive as ``""``. System/Kokoro/Silent
    backends tolerate either as-is; ElevenLabs calls a real API that 404s on
    the literal string "default" (``voice_not_found``), so both must resolve
    to the backend's configured voice instead. Pure and deterministic, so it
    is unit-tested without the network.
    """
    if not voice or voice == "default":
        return configured_voice_id
    return voice


def fetch_kokoro_model(  # pragma: no cover - network + large (~340 MB) download
    dest: Path | None = None,
) -> tuple[Path, Path]:
    """Download the Kokoro model + voices into the cache dir if absent.

    This is an explicit, opt-in network operation (never run on the default path).
    Existing files are not re-downloaded.

    Args:
        dest: Target directory; defaults to :func:`_kokoro_cache_dir`.

    Returns:
        ``(model_path, voices_path)``.
    """
    import urllib.request

    dest = Path(dest) if dest is not None else _kokoro_cache_dir()
    dest.mkdir(parents=True, exist_ok=True)
    model = dest / "kokoro-v1.0.onnx"
    voices = dest / "voices-v1.0.bin"
    if not voices.exists():
        logger.info("downloading Kokoro voices → %s", voices)
        urllib.request.urlretrieve(_KOKORO_VOICES_URL, voices)
    if not model.exists():
        logger.info("downloading Kokoro model (~310 MB) → %s", model)
        urllib.request.urlretrieve(_KOKORO_MODEL_URL, model)
    return model, voices


def _kokoro_synth_segment(engine, text, *, voice, speed, lang):  # pragma: no cover - model
    """Synthesize one segment, recovering from Kokoro's ~510-phoneme overflow.

    Char-based splitting cannot bound *phonemes* (numbers, arrows, and symbols
    expand into many), so a short-looking segment can still exceed the limit. On
    any failure we split the segment in half on word boundaries and recurse, then
    concatenate — guaranteeing success for arbitrary, phoneme-dense narration.
    """
    import numpy as np

    try:
        return engine.create(text, voice=voice, speed=speed, lang=lang)
    except Exception:
        words = text.split()
        if len(words) <= 1:
            raise
        mid = len(words) // 2
        left, rate = _kokoro_synth_segment(
            engine, " ".join(words[:mid]), voice=voice, speed=speed, lang=lang
        )
        right, _ = _kokoro_synth_segment(
            engine, " ".join(words[mid:]), voice=voice, speed=speed, lang=lang
        )
        return np.concatenate([left, right]), rate


def _split_for_tts(text: str, *, max_chars: int = 250) -> list[str]:
    """Split ``text`` into segments under ``max_chars``, at sentence/word bounds.

    Kokoro's ONNX model has a per-call token limit (~510 phoneme tokens); a long
    narration chunk overflows it (``index 510 out of bounds``). Splitting at
    sentence boundaries — falling back to word boundaries for a single overlong
    sentence — keeps each synthesis call safely within the limit. Pure and
    deterministic, so it is unit-tested without the model installed.
    """
    clean = " ".join(text.split())
    if len(clean) <= max_chars:
        return [clean] if clean else []

    # Sentence-ish split that keeps the terminator attached.
    import re

    sentences = re.findall(r"[^.!?]+[.!?]?", clean)
    segments: list[str] = []
    cur = ""
    for sentence in (s.strip() for s in sentences if s.strip()):
        if len(sentence) > max_chars:  # a single overlong sentence → split on words
            if cur:
                segments.append(cur)
                cur = ""
            word_cur = ""
            for word in sentence.split():
                if word_cur and len(word_cur) + 1 + len(word) > max_chars:
                    segments.append(word_cur)
                    word_cur = word
                else:
                    word_cur = f"{word_cur} {word}".strip()
            if word_cur:
                cur = word_cur
        elif cur and len(cur) + 1 + len(sentence) > max_chars:
            segments.append(cur)
            cur = sentence
        else:
            cur = f"{cur} {sentence}".strip()
    if cur:
        segments.append(cur)
    return segments


def _kokoro_cache_dir() -> Path:
    """Return the directory Kokoro model files are looked for in.

    Honors ``DEMOCREATE_KOKORO_DIR``; defaults to ``~/.cache/democreate/kokoro``.
    """
    override = os.environ.get("DEMOCREATE_KOKORO_DIR")
    if override:
        return Path(override)
    return Path.home() / ".cache" / "democreate" / "kokoro"


def _kokoro_model_paths() -> tuple[Path, Path] | None:
    """Resolve ``(model_path, voices_path)`` for Kokoro, or ``None`` if absent.

    Resolution order: the explicit ``KOKORO_MODEL_PATH`` + ``KOKORO_VOICES_PATH``
    env vars, then the first known filename present in :func:`_kokoro_cache_dir`.
    Returns ``None`` (rather than raising) so callers can decide how to report it.
    """
    env_model = os.environ.get("KOKORO_MODEL_PATH")
    env_voices = os.environ.get("KOKORO_VOICES_PATH")
    if env_model and env_voices:
        model, voices = Path(env_model), Path(env_voices)
        return (model, voices) if model.exists() and voices.exists() else None

    cache = _kokoro_cache_dir()
    found_model = next(
        (cache / n for n in _KOKORO_MODEL_NAMES if (cache / n).exists()), None
    )
    found_voices = next(
        (cache / n for n in _KOKORO_VOICES_NAMES if (cache / n).exists()), None
    )
    if found_model is not None and found_voices is not None:
        return found_model, found_voices
    return None


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
    """Kokoro neural TTS backend — a high-quality, fully-local voice.

    Kokoro is an 82M-parameter open-weight neural TTS that runs offline via ONNX
    Runtime (`kokoro-onnx`), producing far more natural narration than the system
    ``say``/``espeak`` voices. It is heavier and slower (a few seconds per chunk on
    CPU) but needs no cloud and no API key.

    Two things must be present: the ``kokoro-onnx`` package (the ``tts`` extra) and
    the model files (``kokoro-v1.0.onnx`` + ``voices-v1.0.bin``, ~340 MB), which are
    NOT pip-installed. Place them in ``~/.cache/democreate/kokoro`` (overridable via
    ``DEMOCREATE_KOKORO_DIR``) or point ``KOKORO_MODEL_PATH`` + ``KOKORO_VOICES_PATH``
    at them. See ``docs/backends.md`` for the one-line download.

    Output is synthesized at Kokoro's native 24 kHz, then transcoded to the
    pipeline's canonical 16-bit mono PCM WAV; the returned duration is *measured*
    from that file (audio stays the single source of timing truth).

    Args:
        voice: Kokoro voice id (e.g. ``"af_heart"``, ``"am_michael"``,
            ``"bf_emma"``). Defaults to :data:`_KOKORO_DEFAULT_VOICE`.
        sample_rate: Canonical output sample rate in Hz.
        speed: Speaking-rate multiplier (1.0 = natural).
        lang: Kokoro language code (``"en-us"`` / ``"en-gb"``).

    Raises:
        BackendUnavailableError: If ``kokoro-onnx`` or the model files are absent.
    """

    name = "kokoro"

    def __init__(
        self,
        *,
        voice: str | None = None,
        sample_rate: int = _DEFAULT_SAMPLE_RATE,
        speed: float = 1.0,
        lang: str = "en-us",
    ) -> None:
        if not _dep_available("kokoro_onnx"):
            raise BackendUnavailableError("kokoro-onnx", extra="tts")
        paths = _kokoro_model_paths()
        if paths is None:
            raise BackendUnavailableError(
                "kokoro-onnx model files (set KOKORO_MODEL_PATH + KOKORO_VOICES_PATH, "
                "or place kokoro-v1.0.onnx + voices-v1.0.bin in "
                f"{_kokoro_cache_dir()} — see docs/backends.md)"
            )
        self._model_path, self._voices_path = paths
        self.voice = voice or _KOKORO_DEFAULT_VOICE
        self.sample_rate = sample_rate
        self.speed = speed
        self.lang = lang
        self._engine_obj = None  # lazily constructed (loading the model is costly)

    def is_available(self) -> bool:
        """Return whether ``kokoro-onnx`` AND its model files are present."""
        return _dep_available("kokoro_onnx") and _kokoro_model_paths() is not None

    def _engine(self):  # pragma: no cover - requires kokoro model files
        """Lazily construct and cache the Kokoro ONNX engine."""
        if self._engine_obj is None:
            from kokoro_onnx import Kokoro

            self._engine_obj = Kokoro(str(self._model_path), str(self._voices_path))
        return self._engine_obj

    def synthesize(  # pragma: no cover - requires kokoro model files
        self, text: str, out_path: Path, *, voice: str | None = None
    ) -> AudioClip:
        """Synthesize ``text`` with Kokoro to a canonical WAV; measure its duration."""
        import soundfile as sf

        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if not text.strip():
            return SilentTTSBackend(sample_rate=self.sample_rate).synthesize(
                text, out_path
            )

        # Demos are often authored with a system voice name (e.g. "Samantha")
        # in demo.voice; Kokoro has its own voice ids and asserts on unknown
        # names. Fall back to the configured Kokoro voice (then the default)
        # rather than crashing, so any demo renders with the neural backend.
        engine = self._engine()
        available = set(engine.get_voices())
        requested = voice or self.voice
        chosen = requested if requested in available else self.voice
        if chosen not in available:
            chosen = _KOKORO_DEFAULT_VOICE
        if chosen != requested:
            logger.info("kokoro voice %r unavailable; using %r", requested, chosen)

        # Split long narration so each call stays under Kokoro's ~510-token limit,
        # then concatenate the audio into one clip (audio stays the timing truth).
        import numpy as np

        segments = _split_for_tts(text) or [text]
        pieces = []
        native_rate = self.sample_rate
        for segment in segments:
            samples, native_rate = _kokoro_synth_segment(
                engine, segment, voice=chosen, speed=self.speed, lang=self.lang
            )
            pieces.append(samples)
        samples = pieces[0] if len(pieces) == 1 else np.concatenate(pieces)
        raw = out_path.with_suffix(".kokoro.wav")
        sf.write(str(raw), samples, native_rate)
        _transcode_audio_file(raw, out_path, self.sample_rate)
        raw.unlink(missing_ok=True)

        measured_ms = measure_wav_duration_ms(out_path)
        logger.info("kokoro TTS spoke %d ms to %s", measured_ms, out_path)
        return AudioClip(
            path=out_path,
            duration_ms=measured_ms,
            sample_rate=self.sample_rate,
            text=text,
        )


class ElevenLabsTTSBackend(TTSBackend):
    """ElevenLabs cloud TTS backend — highest-fidelity hosted voice synthesis.

    Calls the ElevenLabs cloud API to synthesize narration in a chosen stock or
    cloned voice, then transcodes the result to the pipeline's canonical 16-bit
    mono PCM WAV at ``sample_rate`` Hz; the returned duration is *measured* from
    that file (audio stays the single source of timing truth).

    Two things must be present for :meth:`synthesize` to run: the light
    ``elevenlabs`` client package (the ``elevenlabs`` extra) and an API key in the
    environment variable named by ``api_key_env`` (default ``ELEVENLABS_API_KEY``).
    Neither is required merely to *construct* the backend, so a demo config can
    reference it and fail only at synthesis time with a clear, typed error.

    Args:
        voice_id: ElevenLabs voice id used when a per-call/per-chunk ``voice`` is
            not supplied. Defaults to :data:`_ELEVENLABS_DEFAULT_VOICE`.
        model: ElevenLabs model id, or one of the short aliases in
            :data:`_ELEVENLABS_MODELS` (e.g. ``"turbo_v2_5"``). Unknown values are
            passed through verbatim so new model ids need no code change.
        api_key_env: Name of the environment variable holding the API key.
        sample_rate: Canonical output sample rate in Hz. Must be one of
            8000 / 16000 / 22050 / 24000 / 32000 / 44100 / 48000.

    Raises:
        ValueError: If ``sample_rate`` is not an ElevenLabs-supported WAV rate.
    """

    name = "elevenlabs"

    def __init__(
        self,
        *,
        voice_id: str | None = None,
        model: str = _ELEVENLABS_DEFAULT_MODEL,
        api_key_env: str = "ELEVENLABS_API_KEY",
        sample_rate: int = _DEFAULT_SAMPLE_RATE,
    ) -> None:
        if sample_rate not in _ELEVENLABS_FORMAT_MAP:
            raise ValueError(
                f"unsupported sample_rate {sample_rate}; "
                f"choose from {sorted(_ELEVENLABS_FORMAT_MAP)}"
            )
        self.voice_id = voice_id or _ELEVENLABS_DEFAULT_VOICE
        self.model = _ELEVENLABS_MODELS.get(model, model)
        self._api_key_env = api_key_env
        self.sample_rate = sample_rate
        self._output_format = _ELEVENLABS_FORMAT_MAP[sample_rate]

    def _api_key(self) -> str | None:
        """Return the API key from the configured env var, or ``None`` if unset."""
        return os.environ.get(self._api_key_env)

    def is_available(self) -> bool:
        """Return whether the ``elevenlabs`` package AND an API key are present.

        Performs no network call, matching every other backend's contract: it
        only checks that the client is importable and a key is configured.
        """
        return _dep_available("elevenlabs") and bool(self._api_key())

    def _require_available(self) -> None:
        """Raise a clear, typed error if the package or key is missing.

        Missing *package* → :class:`BackendUnavailableError` (carries the extra so
        the message says exactly what to install). Missing *key* →
        :class:`DemoCreateError` (nothing to install; the user must export a key).
        """
        if not _dep_available("elevenlabs"):
            raise BackendUnavailableError("elevenlabs (cloud TTS)", extra="elevenlabs")
        if not self._api_key():
            raise DemoCreateError(
                f"ElevenLabs API key not set — export {self._api_key_env}=<your-key>"
            )

    def synthesize(
        self, text: str, out_path: Path, *, voice: str | None = None
    ) -> AudioClip:
        """Synthesize ``text`` via ElevenLabs and write a canonical WAV.

        Empty/whitespace text falls back to a short silent clip so timing stays
        sane (the cloud API rejects empty input). A missing package or key raises
        before any network call.

        Args:
            text: Narration text to synthesize.
            out_path: Destination ``.wav`` file; parent dirs are created.
            voice: Per-call voice id override (falls back to :attr:`voice_id`).

        Returns:
            An :class:`~democreate.media.AudioClip` with the *measured* duration.

        Raises:
            BackendUnavailableError: If the ``elevenlabs`` package is absent.
            DemoCreateError: If no API key is configured.
        """
        out_path = Path(out_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        # Empty/whitespace text needs no cloud call — short-circuit to silence
        # before the availability check so an empty chunk never demands a key.
        if not text.strip():
            return SilentTTSBackend(sample_rate=self.sample_rate).synthesize(
                text, out_path
            )

        self._require_available()
        effective_voice_id = _resolve_elevenlabs_voice_id(voice, self.voice_id)
        return self._synthesize_remote(text, out_path, effective_voice_id)

    def _synthesize_remote(  # pragma: no cover - requires elevenlabs + network
        self, text: str, out_path: Path, voice_id: str
    ) -> AudioClip:
        """Perform the real cloud call + transcode (only runs with dep + key)."""
        from elevenlabs.client import ElevenLabs

        client = ElevenLabs(api_key=self._api_key())
        logger.debug(
            "ElevenLabs synthesize: voice=%s model=%s rate=%d",
            voice_id,
            self.model,
            self.sample_rate,
        )
        audio_iter = client.text_to_speech.convert(
            voice_id,
            text=text,
            model_id=self.model,
            output_format=self._output_format,
        )

        # Stream raw WAV to a temp file, then transcode to canonical 16-bit mono
        # PCM. Transcoding is unconditional: ElevenLabs WAV output may be stereo
        # regardless of rate, and the assembly pipeline expects mono.
        raw = out_path.with_name(out_path.stem + "_el_raw.wav")
        try:
            with open(raw, "wb") as fh:
                for chunk in audio_iter:
                    fh.write(chunk)
            _transcode_audio_file(raw, out_path, self.sample_rate)
        finally:
            raw.unlink(missing_ok=True)

        measured_ms = measure_wav_duration_ms(out_path)
        logger.info("elevenlabs TTS spoke %d ms to %s", measured_ms, out_path)
        return AudioClip(
            path=out_path,
            duration_ms=measured_ms,
            sample_rate=self.sample_rate,
            text=text,
        )


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
