"""Audio primitives for narration backends: WAV measurement, transcode, probes.

Split out of :mod:`democreate.narration.tts` (agent refactoring lane); the
public surface remains importable from :mod:`democreate.narration.tts`.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path

from ..errors import BackendUnavailableError, DemoCreateError

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
