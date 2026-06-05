"""Video and GIF export.

Two pure capabilities work with only the core dependencies:

* :func:`build_ffmpeg_command` constructs the ``ffmpeg`` argv list for an H.264
  MP4 encode from a numbered-frame glob plus optional audio. It executes nothing,
  so the exact command can be unit-tested and inspected.
* :func:`frames_to_gif` assembles an animated GIF from still frames using Pillow
  (imported as ``PIL``, a core dependency).

The actual MP4 encode in :func:`export_video` requires the ``ffmpeg`` binary on
``PATH`` (or the ``moviepy`` backend) and is therefore guarded: when neither is
present it raises :class:`~democreate.errors.BackendUnavailableError`.
"""

from __future__ import annotations

import importlib.util
import shutil
import wave
from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError, RenderError

__all__ = [
    "build_ffmpeg_command",
    "frames_to_gif",
    "export_video",
    "concat_wavs",
    "build_concat_demuxer_file",
    "assemble_video",
    "encode_frame_sequence",
    "ffmpeg_available",
]

logger = get_logger(__name__)


def build_ffmpeg_command(
    frames_glob: str,
    audio_path: str | None,
    out_path: Path,
    *,
    fps: int = 30,
) -> list[str]:
    """Construct the ``ffmpeg`` argv list for an H.264 MP4 encode.

    Builds (but never runs) the command that turns a sequence of numbered frames
    into a web-friendly ``libx264`` / ``yuv420p`` MP4, optionally muxing a single
    audio track. The frame input uses ffmpeg's ``image2`` glob pattern (e.g.
    ``frame_%05d.png``).

    Args:
        frames_glob: An ffmpeg ``image2`` input pattern, e.g. ``"frames/%05d.png"``.
        audio_path: Path to an audio file to mux in, or ``None`` for silent video.
        out_path: Destination path for the encoded video.
        fps: Output frame rate (also the input frame rate for the image sequence).

    Returns:
        The argv list, beginning with ``"ffmpeg"``, ready to hand to
        :func:`subprocess.run`.

    Raises:
        ValueError: If ``fps`` is not positive.
    """
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")

    cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
        "-i",
        frames_glob,
    ]
    if audio_path is not None:
        cmd += ["-i", str(audio_path)]
    cmd += [
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-r",
        str(fps),
    ]
    if audio_path is not None:
        # Encode audio and stop at the shortest stream so a slightly-longer audio
        # track does not leave a frozen tail frame.
        cmd += ["-c:a", "aac", "-ar", "48000", "-shortest"]
    cmd.append(str(out_path))
    return cmd


def frames_to_gif(frame_paths: list[Path], out_path: Path, *, fps: int = 10) -> Path:
    """Assemble an animated GIF from still frames using Pillow.

    Args:
        frame_paths: Ordered list of image files (PNG/JPEG/...) to use as frames.
        out_path: Destination ``.gif`` path. Parent directories are created.
        fps: Playback frame rate; the per-frame duration is ``1000 / fps`` ms.

    Returns:
        ``out_path``.

    Raises:
        ValueError: If ``frame_paths`` is empty or ``fps`` is not positive.
        RenderError: If a frame file cannot be opened as an image.
    """
    if not frame_paths:
        raise ValueError("frames_to_gif requires at least one frame")
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")

    from PIL import Image, UnidentifiedImageError  # core dep (pillow)

    images: list[Image.Image] = []
    for fp in frame_paths:
        try:
            img = Image.open(fp)
            images.append(img.convert("RGB"))
        except (FileNotFoundError, UnidentifiedImageError, OSError) as exc:
            raise RenderError(f"cannot open frame {fp!s}: {exc}") from exc

    out_path.parent.mkdir(parents=True, exist_ok=True)
    duration_ms = int(round(1000 / fps))
    first, rest = images[0], images[1:]
    first.save(
        out_path,
        format="GIF",
        save_all=True,
        append_images=rest,
        duration=duration_ms,
        loop=0,
        optimize=False,
    )
    logger.info("wrote GIF with %d frame(s) → %s", len(images), out_path)
    return out_path


def concat_wavs(wav_paths: list[Path], out_path: Path) -> Path:
    """Concatenate canonical WAV clips gap-free into one track (pure stdlib).

    This is the audio-as-ground-truth assembler: per-chunk narration clips are
    joined back-to-back in order using the stdlib :mod:`wave` module — no ffmpeg,
    no resampling. Every input must share the same channel count, sample width,
    and frame rate (the synthesis backends all emit canonical 16-bit mono PCM);
    a mismatch raises rather than silently producing skewed audio.

    Args:
        wav_paths: Ordered list of ``.wav`` files to join.
        out_path: Destination ``.wav`` path. Parent directories are created.

    Returns:
        ``out_path``.

    Raises:
        ValueError: If ``wav_paths`` is empty or the clips' formats disagree.
        RenderError: If a clip cannot be read.
    """
    if not wav_paths:
        raise ValueError("concat_wavs requires at least one clip")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    params = None
    frames: list[bytes] = []
    for wp in wav_paths:
        try:
            with wave.open(str(wp), "rb") as w:
                p = (w.getnchannels(), w.getsampwidth(), w.getframerate())
                if params is None:
                    params = p
                elif p != params:
                    raise ValueError(
                        f"WAV format mismatch: {wp} has {p}, expected {params}"
                    )
                frames.append(w.readframes(w.getnframes()))
        except wave.Error as exc:
            raise RenderError(f"cannot read WAV {wp}: {exc}") from exc

    nchannels, sampwidth, framerate = params  # type: ignore[misc]
    with wave.open(str(out_path), "wb") as out:
        out.setnchannels(nchannels)
        out.setsampwidth(sampwidth)
        out.setframerate(framerate)
        for chunk in frames:
            out.writeframes(chunk)
    logger.info("concatenated %d clip(s) → %s", len(wav_paths), out_path)
    return out_path


def build_concat_demuxer_file(
    frames_with_durations: list[tuple[Path, float]],
    *,
    repeat_last: bool = True,
) -> str:
    """Build an ffmpeg concat-demuxer script holding each frame for its duration.

    The concat demuxer (unlike the fixed-rate ``image2`` demuxer) lets each image
    declare its own on-screen ``duration`` in seconds — which is exactly how a
    timeline with unequal per-chunk durations becomes correctly-timed video. The
    demuxer ignores the final entry's duration unless the last file is listed
    twice, so ``repeat_last`` does that.

    Args:
        frames_with_durations: Ordered ``(frame_path, seconds)`` pairs.
        repeat_last: Repeat the final frame so its duration is honored.

    Returns:
        The concat-script text (use with ``ffmpeg -f concat -safe 0``).

    Raises:
        ValueError: If empty or any duration is non-positive.
    """
    if not frames_with_durations:
        raise ValueError("build_concat_demuxer_file requires at least one frame")
    lines = ["ffconcat version 1.0"]
    for path, seconds in frames_with_durations:
        if seconds <= 0:
            raise ValueError(f"frame duration must be positive, got {seconds}")
        # POSIX-quote the path for the demuxer (single quotes, escaped).
        safe = str(path).replace("'", r"'\''")
        lines.append(f"file '{safe}'")
        lines.append(f"duration {seconds:.3f}")
    if repeat_last:
        last = str(frames_with_durations[-1][0]).replace("'", r"'\''")
        lines.append(f"file '{last}'")
    return "\n".join(lines) + "\n"


def ffmpeg_available() -> bool:
    """Return ``True`` if the ``ffmpeg`` binary is on ``PATH``."""
    return shutil.which("ffmpeg") is not None


def assemble_video(
    frame_paths: list[Path],
    durations_ms: list[int],
    audio_path: Path | None,
    out_path: Path,
    *,
    fps: int = 30,
    size: tuple[int, int] | None = None,
    subtitles: Path | None = None,
    crf: int = 18,
    preset: str = "medium",
) -> Path:  # pragma: no cover - requires the ffmpeg binary
    """Encode an audio-synced MP4 holding each frame for its measured duration.

    This is the real HD assembler used by the ``render`` pipeline. Frame ``i`` is
    held on screen for ``durations_ms[i]`` (the *measured* narration length of the
    corresponding chunk), so video and the concatenated voiceover share one
    timebase by construction. The output is ``libx264``/``yuv420p`` with even
    dimensions (forced via ``scale``) and AAC audio.

    Args:
        frame_paths: Ordered frame images (one per chunk/timeline entry).
        durations_ms: Per-frame on-screen durations in ms (same length as frames).
        audio_path: Concatenated voiceover WAV to mux, or ``None`` for silent video.
        out_path: Destination ``.mp4``.
        fps: Output frame rate.
        size: Optional ``(w, h)`` to scale to; dimensions are forced even regardless.
        subtitles: Optional ``.srt`` to burn in (skipped if libass is unavailable).

    Returns:
        ``out_path``.

    Raises:
        BackendUnavailableError: If ffmpeg is not installed.
        ValueError: On empty/mismatched inputs.
        RenderError: If the encode exits non-zero.
    """
    import subprocess

    if not frame_paths:
        raise ValueError("assemble_video requires at least one frame")
    if len(frame_paths) != len(durations_ms):
        raise ValueError(
            f"frames ({len(frame_paths)}) and durations ({len(durations_ms)}) "
            "must be the same length"
        )
    if not ffmpeg_available():
        raise BackendUnavailableError("ffmpeg", extra="video")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    # The concat demuxer resolves `file` entries relative to the concat script's
    # own directory, so absolute frame paths are required for correctness
    # regardless of cwd or where the script is written.
    concat_text = build_concat_demuxer_file(
        [
            (p.resolve(), max(0.04, ms / 1000))
            for p, ms in zip(frame_paths, durations_ms, strict=True)
        ]
    )
    concat_file = out_path.parent / f"{out_path.stem}_frames.concat"
    concat_file.write_text(concat_text, encoding="utf-8")

    vf_parts = []
    if size is not None:
        vf_parts.append(f"scale={size[0]}:{size[1]}")
    vf_parts.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
    if subtitles is not None and _libass_available():
        esc = str(subtitles).replace("\\", "\\\\").replace(":", r"\:").replace("'", r"\'")
        vf_parts.append(f"subtitles='{esc}'")
    vf_parts.append("format=yuv420p")
    vf = ",".join(vf_parts)

    cmd: list[str] = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
    ]
    if audio_path is not None:
        cmd += ["-i", str(audio_path)]
    # Output constant-frame-rate H.264: the concat demuxer's per-image `duration`
    # directives set presentation time; `-r` resamples to a clean CFR stream
    # (broadly player-compatible). Avoid the deprecated `-vsync`, which conflicts
    # with `-r` on ffmpeg >= 7.
    cmd += ["-vf", vf, "-r", str(fps), "-c:v", "libx264",
            "-crf", str(crf), "-preset", preset]
    if audio_path is not None:
        cmd += ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest"]
    cmd.append(str(out_path))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(f"ffmpeg assemble failed: {result.stderr.strip()[-800:]}")
    logger.info("assembled video (%d frames) → %s", len(frame_paths), out_path)
    return out_path


def encode_frame_sequence(
    frame_paths: list[Path],
    audio_path: Path | None,
    out_path: Path,
    *,
    fps: int = 15,
    crf: int = 18,
    preset: str = "medium",
) -> Path:  # pragma: no cover - requires the ffmpeg binary
    """Encode uniformly-timed frames (+ audio) into an MP4 via the image2 demuxer.

    Used for animated renders where every frame is exactly ``1/fps`` long, so the
    fixed-rate ``image2`` input is correct (unlike the per-duration concat demuxer).
    Frames must share one directory and a zero-padded numeric suffix.

    Args:
        frame_paths: Ordered frame images in a single directory.
        audio_path: Audio track to mux, or ``None``.
        out_path: Destination ``.mp4``.
        fps: Frame rate of the sequence and the output.

    Returns:
        ``out_path``.

    Raises:
        BackendUnavailableError: If ffmpeg is absent.
        ValueError: If ``frame_paths`` is empty.
        RenderError: If the encode exits non-zero.
    """
    import subprocess

    if not frame_paths:
        raise ValueError("encode_frame_sequence requires at least one frame")
    if not ffmpeg_available():
        raise BackendUnavailableError("ffmpeg", extra="video")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    first = frame_paths[0].resolve()
    # derive the printf pattern from the first frame's digit-padded stem
    stem = first.stem
    digits = len(stem) - len(stem.rstrip("0123456789"))
    prefix = stem[: len(stem) - digits]
    pattern = str(first.parent / f"{prefix}%0{digits}d{first.suffix}")

    cmd = [
        "ffmpeg", "-y", "-framerate", str(fps), "-start_number",
        str(int(stem[len(prefix):])), "-i", pattern,
    ]
    if audio_path is not None:
        cmd += ["-i", str(audio_path)]
    cmd += [
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,format=yuv420p",
        "-c:v", "libx264", "-r", str(fps),
        "-crf", str(crf), "-preset", preset,
    ]
    if audio_path is not None:
        cmd += ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest"]
    cmd.append(str(out_path))

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(f"ffmpeg image2 encode failed: {result.stderr.strip()[-800:]}")
    logger.info("encoded %d frame(s) @ %dfps → %s", len(frame_paths), fps, out_path)
    return out_path


def _libass_available() -> bool:  # pragma: no cover - depends on ffmpeg build
    """Return ``True`` if ffmpeg exposes the ``subtitles`` (libass) filter."""
    import subprocess

    try:
        out = subprocess.run(
            ["ffmpeg", "-hide_banner", "-filters"],
            capture_output=True,
            text=True,
        )
        return " subtitles " in out.stdout
    except OSError:
        return False


def _has_ffmpeg() -> bool:
    """Return ``True`` if the ``ffmpeg`` binary is resolvable on ``PATH``."""
    return shutil.which("ffmpeg") is not None


def _has_moviepy() -> bool:
    """Return ``True`` if the ``moviepy`` backend is importable."""
    return importlib.util.find_spec("moviepy") is not None


def export_video(
    frame_paths: list[Path],
    audio_path: Path | None,
    out_path: Path,
    *,
    fps: int = 30,
) -> Path:  # pragma: no cover - requires the ffmpeg binary / moviepy
    """Encode frames (+ optional audio) into an MP4.

    Requires either the ``ffmpeg`` binary on ``PATH`` or the ``moviepy`` backend.
    The frames must share a zero-padded numeric naming scheme in a single
    directory so ffmpeg's ``image2`` demuxer can sequence them.

    Args:
        frame_paths: Ordered frame image paths (must live in one directory).
        audio_path: Optional audio track to mux in.
        out_path: Destination ``.mp4`` path.
        fps: Output frame rate.

    Returns:
        ``out_path``.

    Raises:
        BackendUnavailableError: If neither ffmpeg nor moviepy is available.
        ValueError: If ``frame_paths`` is empty.
        RenderError: If the encode subprocess exits non-zero.
    """
    if not frame_paths:
        raise ValueError("export_video requires at least one frame")
    if not (_has_ffmpeg() or _has_moviepy()):
        raise BackendUnavailableError("ffmpeg", extra="video")

    import subprocess

    out_path.parent.mkdir(parents=True, exist_ok=True)
    parent = frame_paths[0].parent
    suffix = frame_paths[0].suffix
    glob = str(parent / f"%05d{suffix}")
    cmd = build_ffmpeg_command(
        glob, str(audio_path) if audio_path else None, out_path, fps=fps
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(f"ffmpeg failed: {result.stderr.strip()}")
    return out_path
