"""Voiceover post-processing for the assembly stage.

Improves narrated-audio quality by adding breathing room between synthesized
chunks, lead/trail silence, loudness normalization, and gentle fades. The
silence-generation and concatenation primitives are pure standard library (the
:mod:`wave` module), so they are import-safe, deterministic, and fully testable
without any external binary. Only :func:`normalize_audio` and :func:`apply_fade`
need ``ffmpeg``; they are guarded and raise :class:`BackendUnavailableError`
when it is absent.

Canonical audio is 16-bit mono PCM. The pure helpers generate silence at the
clips' own ``(channels, sampwidth, framerate)`` so concatenation never resamples.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError, RenderError

logger = get_logger(__name__)

__all__ = [
    "write_silence",
    "concat_with_gaps",
    "measure_duration_ms",
    "normalize_audio",
    "apply_fade",
    "ffmpeg_audio_available",
]

_DEFAULT_SAMPWIDTH = 2  # 16-bit PCM
_DEFAULT_CHANNELS = 1  # mono


def _frames_for_ms(ms: int, sample_rate: int) -> int:
    """Return the frame count for ``ms`` milliseconds at ``sample_rate``.

    Args:
        ms: Duration in milliseconds. Non-positive durations yield one frame so
            the resulting WAV is still a valid, readable file.
        sample_rate: Frames per second.

    Returns:
        The number of frames, always at least ``1``.
    """
    if ms <= 0:
        return 1
    return max(1, round(sample_rate * ms / 1000))


def write_silence(out_path: Path, ms: int, *, sample_rate: int = 22050) -> Path:
    """Write a silent 16-bit mono PCM WAV of ``ms`` milliseconds.

    Uses the standard library :mod:`wave` module only, so it is pure and
    deterministic. ``ms <= 0`` writes a roughly one-frame file so the output is
    always a valid WAV.

    Args:
        out_path: Destination ``.wav`` path (parent dirs are created).
        ms: Desired silence duration in milliseconds.
        sample_rate: Output frame rate in Hz.

    Returns:
        ``out_path``.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n_frames = _frames_for_ms(ms, sample_rate)
    silence = b"\x00" * (n_frames * _DEFAULT_SAMPWIDTH * _DEFAULT_CHANNELS)
    with wave.open(str(out_path), "wb") as wav:
        wav.setnchannels(_DEFAULT_CHANNELS)
        wav.setsampwidth(_DEFAULT_SAMPWIDTH)
        wav.setframerate(sample_rate)
        wav.writeframes(silence)
    return out_path


def _silence_frames(n_frames: int, sampwidth: int, channels: int) -> bytes:
    """Return silent PCM frames, using the unsigned midpoint for 8-bit samples.

    Args:
        n_frames: Number of audio frames.
        sampwidth: Bytes per sample.
        channels: Channel count.

    Returns:
        A bytes buffer of silent PCM samples in the given format.
    """
    sample = b"\x80" if sampwidth == 1 else b"\x00" * sampwidth
    return sample * (max(0, n_frames) * channels)


def concat_with_gaps(
    wav_paths: list[Path],
    out_path: Path,
    *,
    gap_ms: int = 0,
    lead_ms: int = 0,
    trail_ms: int = 0,
) -> Path:
    """Concatenate WAV clips in order, inserting silent gaps and lead/trail.

    Silence is generated at the clips' own ``(channels, sampwidth, framerate)``,
    so no resampling occurs. All clips must share that format. Pure and
    deterministic — uses only the standard library :mod:`wave` module.

    Args:
        wav_paths: Clips to concatenate, in playback order. Must be non-empty.
        out_path: Destination ``.wav`` path (parent dirs are created).
        gap_ms: Silence inserted between consecutive clips.
        lead_ms: Silence inserted before the first clip.
        trail_ms: Silence inserted after the last clip.

    Returns:
        ``out_path``.

    Raises:
        ValueError: If ``wav_paths`` is empty or the clips disagree on
            ``(channels, sampwidth, framerate)``.
    """
    if not wav_paths:
        raise ValueError("concat_with_gaps requires at least one clip")

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    params: tuple[int, int, int] | None = None
    clips: list[bytes] = []
    for raw_path in wav_paths:
        clip_path = Path(raw_path)
        with wave.open(str(clip_path), "rb") as wav:
            fmt = (wav.getnchannels(), wav.getsampwidth(), wav.getframerate())
            if params is None:
                params = fmt
            elif fmt != params:
                raise ValueError(
                    "WAV format mismatch: "
                    f"{clip_path} has {fmt}, expected {params} "
                    "(channels, sampwidth, framerate)"
                )
            clips.append(wav.readframes(wav.getnframes()))

    assert params is not None  # non-empty list guarantees this
    channels, sampwidth, framerate = params

    def _gap(ms: int) -> bytes:
        if ms <= 0:
            return b""
        n_frames = round(framerate * ms / 1000)
        return _silence_frames(n_frames, sampwidth, channels)

    pieces: list[bytes] = []
    lead = _gap(lead_ms)
    if lead:
        pieces.append(lead)
    gap = _gap(gap_ms)
    for index, clip in enumerate(clips):
        if index > 0 and gap:
            pieces.append(gap)
        pieces.append(clip)
    trail = _gap(trail_ms)
    if trail:
        pieces.append(trail)

    with wave.open(str(out_path), "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(sampwidth)
        out.setframerate(framerate)
        out.writeframes(b"".join(pieces))
    return out_path


def measure_duration_ms(wav_path: Path) -> int:
    """Return the true duration of ``wav_path`` in milliseconds.

    Reads the frame count and frame rate from the WAV header via the standard
    library :mod:`wave` module.

    Args:
        wav_path: Path to a readable ``.wav`` file.

    Returns:
        Duration in whole milliseconds (rounded).
    """
    with wave.open(str(Path(wav_path)), "rb") as wav:
        n_frames = wav.getnframes()
        framerate = wav.getframerate()
    if framerate <= 0:
        return 0
    return round(n_frames * 1000 / framerate)


def ffmpeg_audio_available() -> bool:
    """Report whether the ``ffmpeg`` binary is on ``PATH``.

    Returns:
        ``True`` if :func:`shutil.which` finds ``ffmpeg``, else ``False``.
    """
    return shutil.which("ffmpeg") is not None


def _filter_wav(
    in_path: Path, out_path: Path, audio_filter: str, operation: str
) -> Path:  # pragma: no cover - requires the ffmpeg binary
    """Filter PCM WAV audio without FFmpeg's version-dependent WAV headers."""
    try:
        with wave.open(str(in_path), "rb") as source:
            params = source.getparams()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=out_path.parent) as directory:
            raw_path = Path(directory) / "audio.pcm"
            wav_path = Path(directory) / "audio.wav"
            command = [
                "ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(in_path),
                "-af", audio_filter, "-ar", str(params.framerate),
                "-ac", str(params.nchannels), "-c:a", "pcm_s16le",
                "-f", "s16le", str(raw_path),
            ]
            subprocess.run(
                command, check=True, stdin=subprocess.DEVNULL, capture_output=True
            )
            with raw_path.open("rb") as raw, wave.open(str(wav_path), "wb") as output:
                output.setnchannels(params.nchannels)
                output.setsampwidth(2)
                output.setframerate(params.framerate)
                while data := raw.read(65536 * params.nchannels):
                    output.writeframesraw(data)
            wav_path.replace(out_path)
    except (OSError, EOFError, wave.Error, subprocess.CalledProcessError) as exc:
        raise RenderError(f"ffmpeg audio {operation} failed") from exc
    return out_path


def normalize_audio(
    in_path: Path,
    out_path: Path,
    *,
    i: float = -16.0,
    tp: float = -1.5,
    lra: float = 11.0,
) -> Path:  # pragma: no cover - requires the ffmpeg binary
    """Loudness-normalize ``in_path`` with ffmpeg's ``loudnorm`` filter.

    Preserves the input PCM WAV's sample rate and channel count; writes a
    standard 16-bit PCM WAV readable on Python 3.11 as well as newer runtimes.
    FFmpeg's automatic loudnorm output otherwise uses 192 kHz and may emit a
    WAVE_FORMAT_EXTENSIBLE header unsupported by Python 3.11's ``wave`` reader.

    Args:
        in_path: Source PCM WAV path.
        out_path: Destination ``.wav`` path (parent dirs are created).
        i: Integrated loudness target in LUFS.
        tp: True-peak ceiling in dBTP.
        lra: Loudness range target in LU.

    Returns:
        ``out_path``.

    Raises:
        BackendUnavailableError: If the ``ffmpeg`` binary is not installed.
        RenderError: If processing or output fails; the source WAV is unchanged.
    """
    if not ffmpeg_audio_available():
        raise BackendUnavailableError("ffmpeg", extra="video")

    in_path = Path(in_path)
    out_path = Path(out_path)
    logger.info("normalizing audio: %s -> %s", in_path, out_path)
    return _filter_wav(
        in_path, out_path, f"loudnorm=I={i}:TP={tp}:LRA={lra}", "normalization"
    )


def apply_fade(
    in_path: Path,
    out_path: Path,
    *,
    fade_ms: int = 180,
) -> Path:  # pragma: no cover - requires the ffmpeg binary
    """Apply a fade-in and fade-out to ``in_path`` with ffmpeg's ``afade``.

    The fade-out start is computed from the true clip duration via
    :func:`measure_duration_ms`.
    Sample rate and channel count are preserved in a standard 16-bit PCM WAV.

    Args:
        in_path: Source PCM WAV path.
        out_path: Destination ``.wav`` path (parent dirs are created).
        fade_ms: Duration of each fade (in and out) in milliseconds.

    Returns:
        ``out_path``.

    Raises:
        BackendUnavailableError: If the ``ffmpeg`` binary is not installed.
        RenderError: If processing or output fails; the source WAV is unchanged.
    """
    if not ffmpeg_audio_available():
        raise BackendUnavailableError("ffmpeg", extra="video")

    in_path = Path(in_path)
    out_path = Path(out_path)

    try:
        total_ms = measure_duration_ms(in_path)
    except (OSError, EOFError, wave.Error) as exc:
        raise RenderError("cannot read WAV for audio fade") from exc
    fade_s = max(fade_ms, 0) / 1000.0
    out_start_s = max(total_ms - max(fade_ms, 0), 0) / 1000.0
    afade = f"afade=t=in:st=0:d={fade_s},afade=t=out:st={out_start_s}:d={fade_s}"
    logger.info("applying fade (%d ms) to %s -> %s", fade_ms, in_path, out_path)
    return _filter_wav(in_path, out_path, afade, "fade")
