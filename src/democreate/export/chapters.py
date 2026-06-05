"""Chapter-marker export for narrated demos.

Turns a :class:`~democreate.schema.Demo` into two complementary chapter formats:

* **YouTube chapters** — a plain-text block of ``M:SS Title`` (or ``H:MM:SS``)
  lines, one per scene, with the first line forced to ``0:00`` as YouTube
  requires.
* **ffmpeg metadata** — an ``FFMETADATA1`` document with one ``[CHAPTER]`` block
  per scene, ready to be muxed into an MP4 with ``-map_metadata``.

The timeline is derived from
:func:`democreate.export.interactive.build_timeline`, so chapter timings stay
consistent with the interactive player and the rendered video. All builders are
pure (string/filesystem only). Embedding chapters into an MP4 is a guarded
optional step that shells out to ``ffmpeg``.
"""

from __future__ import annotations

from pathlib import Path
from shutil import which
from subprocess import run

from .._logging import get_logger
from ..errors import BackendUnavailableError, RenderError
from ..schema import Demo
from .interactive import build_timeline

__all__ = [
    "measured_chapters",
    "to_youtube_chapters",
    "to_ffmetadata",
    "write_chapters",
    "embed_chapters",
]

logger = get_logger(__name__)


def _format_timestamp(ms: int) -> str:
    """Format milliseconds as a YouTube chapter timestamp.

    Renders ``M:SS`` when under an hour and ``H:MM:SS`` once the hour mark is
    reached. Minutes and seconds are zero-padded to two digits except for the
    leading field.

    Args:
        ms: Offset from the start of the video, in milliseconds.

    Returns:
        A chapter timestamp string such as ``"0:00"``, ``"4:05"``, or
        ``"1:02:03"``.
    """
    total_seconds = max(0, ms) // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes}:{seconds:02d}"


def measured_chapters(demo: Demo, clips, *, lead_ms=0, gap_ms=0, trail_ms=0):
    """Return scene chapters aligned to the *measured* audio timeline.

    The animated render holds each scene for the real (measured) duration of its
    narration clip, concatenated with the configured lead/gap/trail silence. This
    builds the per-scene chapter starts from exactly that concatenated timeline
    (via :func:`~democreate.assembly.animator.chunk_timing`), so chapter markers
    land on the true on-screen scene transitions rather than a word-count
    estimate. Returns ``(chapters, total_ms)`` where ``chapters`` is a list of
    ``{title, scene_id, start_ms}`` (one per scene, in order).

    Args:
        demo: The demo whose scenes become chapters.
        clips: The rendered narration clips, in chunk order (one per chunk).
        lead_ms/gap_ms/trail_ms: The same silence model the renderer used.
    """
    from ..assembly.animator import chunk_timing

    windows, total_ms = chunk_timing(
        clips, lead_ms=lead_ms, gap_ms=gap_ms, trail_ms=trail_ms)
    chapters: list[dict] = []
    idx = 0
    prev_start = 0
    for scene in demo.scenes:
        if not scene.chunks:
            continue
        # If clip/chunk counts diverge so idx runs past the windows, keep chapters
        # MONOTONIC (reuse the previous start) rather than snapping back to 0:00.
        start = int(windows[idx][0]) if idx < len(windows) else prev_start
        chapters.append({
            "title": scene.title or scene.id,
            "scene_id": scene.id,
            "start_ms": start,
        })
        prev_start = start
        idx += len(scene.chunks)
    return chapters, int(total_ms)


def to_youtube_chapters(demo: Demo, *, chapters=None) -> str:
    """Build a YouTube chapter list from a demo's scenes.

    Produces one ``"<timestamp> <title>"`` line per scene in scene order. The
    first line is always anchored to ``0:00`` (YouTube rejects chapter lists
    whose first entry is not at the very start), regardless of the first scene's
    computed offset.

    Args:
        demo: The demo to lay out.
        chapters: Optional pre-computed chapter list (e.g. from
            :func:`measured_chapters`) to use instead of the estimated timeline.

    Returns:
        A newline-joined chapter block (no trailing newline). Returns an empty
        string when the demo has no chapters.
    """
    if chapters is None:
        chapters = build_timeline(demo)["chapters"]
    lines: list[str] = []
    for index, chapter in enumerate(chapters):
        start_ms = 0 if index == 0 else int(chapter["start_ms"])
        title = str(chapter["title"])
        lines.append(f"{_format_timestamp(start_ms)} {title}")
    return "\n".join(lines)


def _escape_ffmetadata(value: str) -> str:
    """Escape a value for an ``FFMETADATA1`` document.

    ffmpeg treats ``=``, ``;``, ``#``, ``\\`` and newlines as special and
    requires them to be backslash-escaped inside keys and values.

    Args:
        value: Raw text to escape.

    Returns:
        The escaped text, safe to place after ``key=`` in a metadata block.
    """
    out = value.replace("\\", "\\\\")
    for char in ("=", ";", "#"):
        out = out.replace(char, "\\" + char)
    return out.replace("\n", "\\\n")


def to_ffmetadata(demo: Demo, *, chapters=None, total_ms=None) -> str:
    """Build an ffmpeg ``FFMETADATA1`` document from a demo's scenes.

    Emits the ``;FFMETADATA1`` header followed by one ``[CHAPTER]`` block per
    scene. Each block uses a millisecond timebase (``TIMEBASE=1/1000``); its
    ``START`` is the scene's chapter start and its ``END`` is the next scene's
    start (or the timeline's total length for the final scene), guaranteeing a
    monotonic, non-overlapping sequence.

    Args:
        demo: The demo to lay out.
        chapters: Optional pre-computed chapter list (e.g. from
            :func:`measured_chapters`) to use instead of the estimated timeline.
        total_ms: The timeline length for the final chapter's ``END`` (required
            when ``chapters`` is supplied).

    Returns:
        A complete metadata document terminated by a trailing newline.
    """
    if chapters is None:
        timeline = build_timeline(demo)
        chapters = timeline["chapters"]
        total_ms = int(timeline["total_ms"])
    else:
        total_ms = int(total_ms if total_ms is not None else (
            chapters[-1]["start_ms"] if chapters else 0))

    lines: list[str] = [";FFMETADATA1"]
    for index, chapter in enumerate(chapters):
        start = int(chapter["start_ms"])
        if index + 1 < len(chapters):
            end = int(chapters[index + 1]["start_ms"])
        else:
            end = total_ms
        if end < start:
            end = start
        title = _escape_ffmetadata(str(chapter["title"]))
        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start}",
                f"END={end}",
                f"title={title}",
            ]
        )
    return "\n".join(lines) + "\n"


def write_chapters(demo: Demo, out_dir: Path, *, chapters=None, total_ms=None) -> dict[str, Path]:
    """Write both chapter formats to disk.

    Creates ``out_dir`` if needed and writes ``youtube_chapters.txt`` and
    ``ffmetadata.txt`` into it.

    Args:
        demo: The demo to lay out.
        out_dir: Destination directory for the chapter files.

    Returns:
        A mapping with keys ``"youtube"`` and ``"ffmetadata"`` pointing at the
        written file paths.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    youtube_path = out_dir / "youtube_chapters.txt"
    ffmetadata_path = out_dir / "ffmetadata.txt"

    youtube_path.write_text(
        to_youtube_chapters(demo, chapters=chapters) + "\n", encoding="utf-8")
    ffmetadata_path.write_text(
        to_ffmetadata(demo, chapters=chapters, total_ms=total_ms), encoding="utf-8")

    logger.info("wrote chapter files → %s", out_dir)
    return {"youtube": youtube_path, "ffmetadata": ffmetadata_path}


def embed_chapters(
    mp4_in: Path,
    ffmetadata: Path,
    mp4_out: Path,
) -> Path:  # pragma: no cover
    """Mux chapter metadata into an MP4 with ffmpeg.

    Runs ``ffmpeg -i mp4_in -i ffmetadata -map_metadata 1 -codec copy mp4_out``,
    copying every stream verbatim and taking metadata (including chapters) from
    the second input.

    Args:
        mp4_in: Source MP4 path.
        ffmetadata: Path to an ``FFMETADATA1`` document (see
            :func:`to_ffmetadata`).
        mp4_out: Destination MP4 path.

    Returns:
        ``mp4_out``.

    Raises:
        BackendUnavailableError: If the ``ffmpeg`` binary is not on ``PATH``.
        RenderError: If ffmpeg exits with a non-zero status.
    """
    if which("ffmpeg") is None:
        raise BackendUnavailableError("ffmpeg", extra="video")

    mp4_out = Path(mp4_out)
    mp4_out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(mp4_in),
        "-i",
        str(ffmetadata),
        "-map_metadata",
        "1",
        "-codec",
        "copy",
        str(mp4_out),
    ]
    completed = run(cmd, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        raise RenderError(
            f"ffmpeg failed to embed chapters (exit {completed.returncode}): "
            f"{completed.stderr.strip()}"
        )

    logger.info("embedded chapters → %s", mp4_out)
    return mp4_out
