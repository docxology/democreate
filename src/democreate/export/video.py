"""Video and GIF export.

Two pure capabilities work with only the core dependencies:

* :func:`build_ffmpeg_command` constructs the ``ffmpeg`` argv list for an H.264
  MP4 encode from a numbered-frame glob plus optional audio. It executes nothing,
  so the exact command can be unit-tested and inspected.
* :func:`frames_to_gif` assembles an animated GIF from still frames using Pillow
  (imported as ``PIL``, a core dependency).

The actual MP4 encode in :func:`export_video` requires the ``ffmpeg`` binary on
``PATH`` and is therefore guarded: when it is absent,
:class:`~democreate.errors.BackendUnavailableError` is raised.
"""

from __future__ import annotations

import shutil
import wave
from pathlib import Path

from .._logging import get_logger
from ..errors import BackendUnavailableError, RenderError
from ._atomic import _atomic_output

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
    start_number: int | None = None,
    frame_count: int | None = None,
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
        start_number: Value for ffmpeg's image2 ``-start_number`` input option
            (the number the first frame's pattern index maps to); ``None``
            omits the option and lets ffmpeg default it.
        frame_count: Exact maximum number of output frames, or ``None`` to
            consume the entire input pattern.

    Returns:
        The argv list, beginning with ``"ffmpeg"``, ready to hand to
        :func:`subprocess.run`.

    Raises:
        ValueError: If ``fps`` is not positive.
    """
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    if frame_count is not None and frame_count <= 0:
        raise ValueError(f"frame_count must be positive, got {frame_count}")

    cmd: list[str] = [
        "ffmpeg",
        "-y",
        "-framerate",
        str(fps),
    ]
    if start_number is not None:
        cmd += ["-start_number_range", "1", "-start_number", str(start_number)]
    cmd += [
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
    if frame_count is not None:
        cmd += ["-frames:v", str(frame_count)]
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
        subtitles: Optional ``.srt`` to burn in; requires the subtitles filter.

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
        raise BackendUnavailableError("ffmpeg")

    # The concat demuxer resolves `file` entries relative to the concat script's
    # own directory, so absolute frame paths are required for correctness
    # regardless of cwd or where the script is written.
    concat_text = build_concat_demuxer_file(
        [
            (p.resolve(), max(0.04, ms / 1000))
            for p, ms in zip(frame_paths, durations_ms, strict=True)
        ]
    )

    vf_parts = []
    if size is not None:
        vf_parts.append(f"scale={size[0]}:{size[1]}")
    vf_parts.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")
    if subtitles is not None:
        # Concat stills are sparse: duplicate them before evaluating cue windows,
        # not only at the encoder's output-rate conversion.
        vf_parts.append(f"fps={fps}")
        vf_parts.append(_subtitle_filter(subtitles))
    vf_parts.append("format=yuv420p")
    vf = ",".join(vf_parts)

    with _atomic_output(out_path) as staged:
        concat_file = staged.parent / "frames.concat"
        concat_file.write_text(concat_text, encoding="utf-8")
        cmd: list[str] = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
        ]
        if audio_path is not None:
            cmd += ["-i", str(audio_path)]
        # The concat durations set presentation times; -r produces CFR output.
        cmd += ["-vf", vf, "-r", str(fps), "-c:v", "libx264",
                "-crf", str(crf), "-preset", preset]
        if audio_path is not None:
            cmd += ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest"]
        cmd.append(str(staged))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RenderError(
                f"ffmpeg assemble failed: {result.stderr.strip()[-800:]}"
            )
    logger.info("assembled video (%d frames) → %s", len(frame_paths), out_path)
    return out_path


def _frame_sequence_pattern(frame_paths: list[Path]) -> tuple[str, int]:
    """Validate an exact contiguous, ascending image2 sequence."""
    if not frame_paths:
        raise ValueError("a frame sequence requires at least one frame")
    first = frame_paths[0].resolve()
    stem = first.stem
    digits = len(stem) - len(stem.rstrip("0123456789"))
    if not digits or "%" in str(first):
        raise ValueError(
            "frame paths need a numeric stem suffix and cannot contain '%'"
        )
    prefix = stem[:-digits]
    start_number = int(stem[-digits:])
    for index, path in enumerate(frame_paths):
        expected = first.parent / (
            f"{prefix}{start_number + index:0{digits}d}{first.suffix}"
        )
        if path.resolve() != expected:
            raise ValueError(
                "frame paths must be contiguous, ascending, and share one "
                f"directory and naming pattern; expected {expected}, got {path}"
            )
        if not path.is_file():
            raise RenderError(f"cannot open frame {path}: file does not exist")
    return str(first.parent / f"{prefix}%0{digits}d{first.suffix}"), start_number


def encode_frame_sequence(
    frame_paths: list[Path],
    audio_path: Path | None,
    out_path: Path,
    *,
    fps: int = 15,
    captions: Path | None = None,
    crf: int = 18,
    preset: str = "medium",
) -> Path:  # pragma: no cover - requires the ffmpeg binary
    """Encode uniformly-timed frames (+ audio) into an MP4 via the image2 demuxer.

    Used for animated renders where every frame is exactly ``1/fps`` long, so the
    fixed-rate ``image2`` input is correct (unlike the per-duration concat demuxer).
    Frames must be contiguous and ascending in one directory with a common
    numeric suffix naming scheme. Only the supplied frame count is encoded.

    Args:
        frame_paths: Contiguous, ascending numbered images in a single directory.
        audio_path: Audio track to mux, or ``None``.
        out_path: Destination ``.mp4``.
        fps: Frame rate of the sequence and the output.
        captions: Optional subtitle file (such as SRT) to burn into every frame
            at its encoded presentation time; ``None`` disables subtitle burn.

    Returns:
        ``out_path``.

    Raises:
        BackendUnavailableError: If ffmpeg is absent.
        ValueError: If frames are empty, sparse, reordered, or inconsistently named,
            or ``fps`` is not positive.
        RenderError: If a frame is missing, the subtitles filter is unavailable
            for a caption request, or the encode exits non-zero.
    """
    import subprocess

    if not frame_paths:
        raise ValueError("encode_frame_sequence requires at least one frame")
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    pattern, start_number = _frame_sequence_pattern(frame_paths)
    if not ffmpeg_available():
        raise BackendUnavailableError("ffmpeg")

    vf_parts = ["scale=trunc(iw/2)*2:trunc(ih/2)*2"]
    if captions is not None:
        vf_parts.append(_subtitle_filter(captions))
    vf_parts.append("format=yuv420p")

    cmd = [
        "ffmpeg", "-y", "-framerate", str(fps), "-start_number_range", "1",
        "-start_number", str(start_number), "-i", pattern,
    ]
    if audio_path is not None:
        cmd += ["-i", str(audio_path)]
    cmd += [
        "-vf", ",".join(vf_parts), "-frames:v", str(len(frame_paths)),
        "-c:v", "libx264", "-r", str(fps),
        "-crf", str(crf), "-preset", preset,
    ]
    if audio_path is not None:
        cmd += ["-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-shortest"]
    with _atomic_output(out_path) as staged:
        cmd.append(str(staged))
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RenderError(
                f"ffmpeg image2 encode failed: {result.stderr.strip()[-800:]}"
            )
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


def _subtitle_filter(captions: Path) -> str:
    """Build a subtitles filter, failing rather than ignoring an explicit request."""
    if not _libass_available():
        raise RenderError("caption burn requires ffmpeg's subtitles (libass) filter")
    # argv bypasses the shell, but ffmpeg still parses an option value inside
    # a filtergraph. Escape each of those two parser levels, in that order.
    option_value = (
        str(captions.resolve())
        .replace("\\", r"\\")
        .replace("'", r"\'")
        .replace(":", r"\:")
    )
    filter_value = (
        option_value.replace("\\", r"\\")
        .replace("'", r"\'")
        .replace("[", r"\[")
        .replace("]", r"\]")
        .replace(",", r"\,")
        .replace(";", r"\;")
    )
    return f"subtitles=filename={filter_value}"


def export_video(
    frame_paths: list[Path],
    audio_path: Path | None,
    out_path: Path,
    *,
    fps: int = 30,
) -> Path:  # pragma: no cover - requires the ffmpeg binary
    """Encode frames (+ optional audio) into an MP4.

    Requires the ``ffmpeg`` binary on ``PATH``. Frames must be contiguous and
    ascending, sharing one directory and numeric suffix naming scheme. Sparse,
    reordered, or mixed-pattern inputs are rejected rather than substituted;
    filesystem neighbors beyond the supplied list are never encoded.

    Args:
        frame_paths: Ordered frame image paths (must live in one directory and
            share a zero-padded numeric stem suffix, e.g. ``frame_0000.png``).
        audio_path: Optional audio track to mux in.
        out_path: Destination ``.mp4`` path.
        fps: Output frame rate.

    Returns:
        ``out_path``.

    Raises:
        BackendUnavailableError: If ffmpeg is unavailable.
        ValueError: If frames are empty, sparse, reordered, or inconsistently named,
            or ``fps`` is not positive.
        RenderError: If a frame is missing or the encode subprocess exits non-zero.
    """
    if not frame_paths:
        raise ValueError("export_video requires at least one frame")
    if fps <= 0:
        raise ValueError(f"fps must be positive, got {fps}")
    pattern, start_number = _frame_sequence_pattern(frame_paths)
    if not ffmpeg_available():
        raise BackendUnavailableError("ffmpeg")

    import subprocess

    with _atomic_output(out_path) as staged:
        cmd = build_ffmpeg_command(
            pattern,
            str(audio_path) if audio_path else None,
            staged,
            fps=fps,
            start_number=start_number,
            frame_count=len(frame_paths),
        )
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RenderError(f"ffmpeg failed: {result.stderr.strip()}")
    return out_path
