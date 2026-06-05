"""Content-asserting verification for rendered video.

Existence is not content. An all-black clip, a 0.04-second single-frame stub, or
a video carrying a *silent* audio track all satisfy a naive "does ffprobe report a
1920x1080 video stream?" check. This module refuses that bar.

:func:`verify_video` asserts, against the real file:

* a video stream of the expected dimensions and at least the expected duration;
* a second, **audio** stream whose duration covers the video;
* that the audio is **not digital silence** (mean volume above a floor); and
* that at least one sampled frame is **not uniformly black** (pixel variance).

The JSON-parsing core (:func:`parse_ffprobe`) is pure and unit-tested with canned
``ffprobe`` output; the probes that shell out to ``ffprobe``/``ffmpeg`` are guarded
and excluded from coverage because they need the binaries.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .._logging import get_logger
from ..errors import BackendUnavailableError, RenderError

__all__ = ["VideoReport", "parse_ffprobe", "verify_video"]

logger = get_logger(__name__)

# A real voiceover track sits well above this; digital silence sits at -91 dB
# (16-bit floor) or ffmpeg's -inf sentinel.
SILENCE_FLOOR_DB = -60.0
# Below this Pillow variance an image is effectively a flat/black plate.
BLACK_VARIANCE_FLOOR = 5.0


@dataclass
class VideoReport:
    """The result of content-asserting verification of a video file.

    Attributes:
        path: The verified file.
        has_video: A video stream is present.
        width / height: Video dimensions in pixels.
        duration_s: Container/stream duration in seconds.
        has_audio: An audio stream is present.
        audio_duration_s: Audio stream duration in seconds.
        mean_volume_db: Measured mean audio volume (``None`` if not measured).
        is_silent: Audio is at or below the silence floor.
        frame_variance: Pixel variance of a sampled frame (``None`` if not measured).
        is_black: Sampled frame is effectively uniform/black.
        problems: Human-readable reasons the video fails its assertions.
    """

    path: Path
    has_video: bool = False
    width: int = 0
    height: int = 0
    duration_s: float = 0.0
    has_audio: bool = False
    audio_duration_s: float = 0.0
    mean_volume_db: float | None = None
    is_silent: bool = False
    frame_variance: float | None = None
    is_black: bool = False
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """``True`` iff the video passed every assertion."""
        return not self.problems

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "has_video": self.has_video,
            "width": self.width,
            "height": self.height,
            "duration_s": round(self.duration_s, 3),
            "has_audio": self.has_audio,
            "audio_duration_s": round(self.audio_duration_s, 3),
            "mean_volume_db": self.mean_volume_db,
            "is_silent": self.is_silent,
            "frame_variance": self.frame_variance,
            "is_black": self.is_black,
            "ok": self.ok,
            "problems": list(self.problems),
        }


def parse_ffprobe(
    probe: dict[str, Any],
    *,
    path: Path,
    expected_width: int | None = None,
    expected_height: int | None = None,
    min_duration_s: float = 1.0,
    min_audio_ratio: float = 0.9,
) -> VideoReport:
    """Build a :class:`VideoReport` from parsed ``ffprobe -of json`` output (pure).

    Checks stream presence, dimensions, and that audio duration covers at least
    ``min_audio_ratio`` of the video. Audio-silence and black-frame checks are
    layered on by :func:`verify_video` (they need extra probes).

    Args:
        probe: The decoded ``ffprobe`` JSON (``streams`` + ``format``).
        path: The file the probe describes (for the report).
        expected_width: Required video width, or ``None`` to skip.
        expected_height: Required video height, or ``None`` to skip.
        min_duration_s: Minimum acceptable video duration.
        min_audio_ratio: Audio duration must be ≥ this fraction of video duration.

    Returns:
        A :class:`VideoReport` with ``problems`` populated for any failed check.
    """
    report = VideoReport(path=path)
    streams = probe.get("streams", [])
    fmt = probe.get("format", {})

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    fmt_duration = _to_float(fmt.get("duration"))

    if video is None:
        report.problems.append("no video stream")
    else:
        report.has_video = True
        report.width = int(video.get("width", 0) or 0)
        report.height = int(video.get("height", 0) or 0)
        report.duration_s = _to_float(video.get("duration")) or fmt_duration
        if expected_width is not None and report.width != expected_width:
            report.problems.append(
                f"video width {report.width} != expected {expected_width}"
            )
        if expected_height is not None and report.height != expected_height:
            report.problems.append(
                f"video height {report.height} != expected {expected_height}"
            )
        if report.duration_s < min_duration_s:
            report.problems.append(
                f"video duration {report.duration_s:.2f}s < minimum {min_duration_s}s"
            )

    if audio is None:
        report.problems.append("no audio stream")
    else:
        report.has_audio = True
        report.audio_duration_s = _to_float(audio.get("duration")) or fmt_duration
        if report.duration_s > 0 and (
            report.audio_duration_s < report.duration_s * min_audio_ratio
        ):
            report.problems.append(
                f"audio duration {report.audio_duration_s:.2f}s covers < "
                f"{int(min_audio_ratio * 100)}% of video {report.duration_s:.2f}s"
            )

    return report


def _to_float(value: Any) -> float:
    """Best-effort float coercion; ``None``/garbage become ``0.0``."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def verify_video(
    path: Path,
    *,
    expected_width: int | None = None,
    expected_height: int | None = None,
    min_duration_s: float = 1.0,
    check_content: bool = True,
) -> VideoReport:  # pragma: no cover - requires ffprobe/ffmpeg binaries
    """Run full content-asserting verification on a real video file.

    Args:
        path: The ``.mp4`` (or other container) to verify.
        expected_width / expected_height: Required dimensions, or ``None``.
        min_duration_s: Minimum acceptable duration.
        check_content: Also assert the audio is not silent and a frame is not
            black (requires ffmpeg). When ``False``, only structural checks run.

    Returns:
        A :class:`VideoReport`. Inspect ``report.ok``.

    Raises:
        BackendUnavailableError: If ``ffprobe`` is not installed.
        RenderError: If probing fails.
    """
    if shutil.which("ffprobe") is None:
        raise BackendUnavailableError("ffprobe", extra="video")

    probe = _run_ffprobe(path)
    report = parse_ffprobe(
        probe,
        path=path,
        expected_width=expected_width,
        expected_height=expected_height,
        min_duration_s=min_duration_s,
    )

    if check_content and report.has_audio:
        report.mean_volume_db = _measure_mean_volume_db(path)
        if report.mean_volume_db is None:
            # Fail CLOSED: an un-measurable probe is not a pass. Otherwise a
            # genuinely silent video (or a tooling change) sails through as ok.
            report.problems.append(
                "could not measure audio volume (probe returned no reading)"
            )
        elif report.mean_volume_db <= SILENCE_FLOOR_DB:
            report.is_silent = True
            report.problems.append(
                f"audio is effectively silent (mean volume {report.mean_volume_db:.1f} dB)"
            )

    if check_content and report.has_video:
        report.frame_variance = _sample_frame_variance(path)
        if report.frame_variance is None:
            report.problems.append(
                "could not sample a video frame (probe returned no reading)"
            )
        elif report.frame_variance < BLACK_VARIANCE_FLOOR:
            report.is_black = True
            report.problems.append(
                f"sampled frame is effectively blank (variance {report.frame_variance:.2f})"
            )

    logger.info("verify %s → ok=%s problems=%s", path, report.ok, report.problems)
    return report


def _run_ffprobe(path: Path) -> dict[str, Any]:  # pragma: no cover - binary
    """Return decoded ``ffprobe`` JSON for ``path``."""
    import subprocess

    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-print_format", "json",
            "-show_format", "-show_streams", str(path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RenderError(f"ffprobe failed: {result.stderr.strip()}")
    return json.loads(result.stdout)


def _measure_mean_volume_db(path: Path) -> float | None:  # pragma: no cover - binary
    """Return the mean audio volume in dB via ffmpeg ``volumedetect``."""
    import re
    import subprocess

    result = subprocess.run(
        ["ffmpeg", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
    )
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", result.stderr)
    return float(match.group(1)) if match else None


def _sample_frame_variance(path: Path) -> float | None:  # pragma: no cover - binary
    """Extract one mid-stream frame and return its grayscale pixel variance."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        frame = Path(tmp) / "sample.png"
        result = subprocess.run(
            [
                "ffmpeg", "-y", "-ss", "0.5", "-i", str(path),
                "-frames:v", "1", str(frame),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not frame.exists():
            return None
        from PIL import Image, ImageStat

        img = Image.open(frame).convert("L")
        return ImageStat.Stat(img).var[0]
