"""Pure subtitle/caption formatting.

Turns a :class:`~democreate.schema.Demo` into standard subtitle formats — SRT,
WebVTT, and ASS — with one cue per narration chunk. Timing uses each chunk's
synced ``start_ms`` when present, falling back to a deterministic cumulative
estimate from word counts otherwise. A karaoke-granularity helper renders
word-level timestamps to SRT.

Everything here is pure string formatting with no I/O or heavy dependencies.
"""

from __future__ import annotations

from .._logging import get_logger
from ..schema import Chunk, Demo, WordTimestamp

logger = get_logger(__name__)

__all__ = [
    "to_srt",
    "to_vtt",
    "to_ass",
    "word_timestamps_to_srt",
]


def _fmt_ts(ms: int, *, sep: str) -> str:
    """Format ``ms`` as ``HH:MM:SS<sep>mmm``.

    Args:
        ms: Milliseconds from the start.
        sep: Separator between seconds and milliseconds (``,`` for SRT,
            ``.`` for VTT).

    Returns:
        A zero-padded timecode string.
    """
    if ms < 0:
        ms = 0
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{sep}{millis:03d}"


def _cue_windows(demo: Demo, wpm: int = 150) -> list[tuple[Chunk, int, int]]:
    """Resolve ``(chunk, start_ms, end_ms)`` windows for every chunk.

    Uses synced ``start_ms`` when present, otherwise a gap-free cumulative
    estimate. Windows never overlap or move backwards.

    Args:
        demo: The source demo.
        wpm: Words-per-minute for duration estimates.

    Returns:
        One ``(chunk, start_ms, end_ms)`` tuple per chunk, in demo order.
    """
    windows: list[tuple[Chunk, int, int]] = []
    cursor = 0
    for chunk in demo.iter_chunks():
        duration = chunk.estimated_duration_ms(wpm)
        start = chunk.start_ms if chunk.start_ms is not None else cursor
        if start < cursor:
            start = cursor
        end = start + duration
        windows.append((chunk, start, end))
        cursor = end
    return windows


def to_srt(demo: Demo, *, wpm: int = 150) -> str:
    """Render the demo's narration as a SubRip (``.srt``) document.

    Args:
        demo: The source demo.
        wpm: Words-per-minute for duration estimates.

    Returns:
        A complete SRT document (one cue per chunk).
    """
    blocks: list[str] = []
    for n, (chunk, start, end) in enumerate(_cue_windows(demo, wpm), start=1):
        blocks.append(
            f"{n}\n"
            f"{_fmt_ts(start, sep=',')} --> {_fmt_ts(end, sep=',')}\n"
            f"{chunk.text}\n"
        )
    return "\n".join(blocks)


def to_vtt(demo: Demo, *, wpm: int = 150) -> str:
    """Render the demo's narration as a WebVTT (``.vtt``) document.

    Args:
        demo: The source demo.
        wpm: Words-per-minute for duration estimates.

    Returns:
        A complete WebVTT document with the mandatory header.
    """
    blocks: list[str] = ["WEBVTT\n"]
    for chunk, start, end in _cue_windows(demo, wpm):
        blocks.append(
            f"{_fmt_ts(start, sep='.')} --> {_fmt_ts(end, sep='.')}\n"
            f"{chunk.text}\n"
        )
    return "\n".join(blocks)


def _fmt_ass_ts(ms: int) -> str:
    """Format ``ms`` as an ASS timecode ``H:MM:SS.cc`` (centiseconds)."""
    if ms < 0:
        ms = 0
    hours, rem = divmod(ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    seconds, millis = divmod(rem, 1_000)
    centis = millis // 10
    return f"{hours:d}:{minutes:02d}:{seconds:02d}.{centis:02d}"


def to_ass(demo: Demo, *, wpm: int = 150) -> str:
    """Render the demo's narration as a minimal Advanced SubStation (``.ass``).

    Produces a valid file with ``[Script Info]``, ``[V4+ Styles]``, and
    ``[Events]`` sections and one ``Dialogue`` line per chunk.

    Args:
        demo: The source demo.
        wpm: Words-per-minute for duration estimates.

    Returns:
        A complete ASS document.
    """
    header = (
        "[Script Info]\n"
        f"Title: {demo.title}\n"
        "ScriptType: v4.00+\n"
        f"PlayResX: {demo.width}\n"
        f"PlayResY: {demo.height}\n"
        "\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, "
        "ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, "
        "MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,48,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "0,0,0,0,100,100,0,0,1,2,1,2,10,10,30,1\n"
        "\n"
        "[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, "
        "Effect, Text\n"
    )
    lines: list[str] = [header]
    for chunk, start, end in _cue_windows(demo, wpm):
        text = chunk.text.replace("\n", "\\N")
        lines.append(
            f"Dialogue: 0,{_fmt_ass_ts(start)},{_fmt_ass_ts(end)},"
            f"Default,,0,0,0,,{text}"
        )
    return "\n".join(lines) + "\n"


def word_timestamps_to_srt(words: list[WordTimestamp]) -> str:
    """Render word-level timestamps as a karaoke-granularity SRT document.

    Each word becomes its own cue, useful for word-by-word highlighting.

    Args:
        words: Word timestamps from a transcriber.

    Returns:
        A complete SRT document (one cue per word).
    """
    blocks: list[str] = []
    for n, wt in enumerate(words, start=1):
        blocks.append(
            f"{n}\n"
            f"{_fmt_ts(wt.start_ms, sep=',')} --> {_fmt_ts(wt.end_ms, sep=',')}\n"
            f"{wt.word}\n"
        )
    return "\n".join(blocks)
