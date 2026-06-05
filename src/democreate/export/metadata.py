"""MP4 container metadata tags — provenance written into the video container.

Players and ``ffprobe`` read standard container metadata (``title``, ``artist``,
``date``, ``comment``, ``description``). This module turns a :class:`~democreate.
schema.Demo` plus an optional :class:`~democreate.config.MetadataConfig` into
those tags and offers three increasingly concrete carriers:

* :func:`build_tags` — pure: the canonical ``dict[str, str]`` of tags.
* :func:`to_ffmetadata` — pure: a round-trippable ``;FFMETADATA1`` document.
* :func:`ffmpeg_metadata_args` — pure: a flat ``-metadata k=v`` argv fragment.
* :func:`embed_tags` — guarded: actually mux the tags into an MP4 via ffmpeg.

Only the final embed step needs the ``ffmpeg`` binary; everything else is pure,
deterministic, and stdlib-only so the tag logic is unit-testable in isolation.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from .._logging import get_logger
from ..errors import BackendUnavailableError, RenderError

if TYPE_CHECKING:
    from ..config import MetadataConfig
    from ..schema import Demo

__all__ = [
    "build_tags",
    "to_ffmetadata",
    "ffmpeg_metadata_args",
    "embed_tags",
]

logger = get_logger(__name__)


def build_tags(
    demo: Demo,
    meta: MetadataConfig | None = None,
    *,
    version: str = "",
) -> dict[str, str]:
    """Build a dict of ffmpeg container metadata tags from a demo (+ config).

    The result maps standard container keys to values: ``title`` (``meta.title``
    falling back to ``demo.title``), ``artist`` (``meta.author``), ``date``
    (``meta.date``), ``comment`` (a compact "made with DemoCreate" credit plus any
    source/url), and ``description`` (the same credit, source, and url joined for
    players that surface a longer field). Empty values are dropped, so callers
    never write blank tags. Pure and deterministic.

    Args:
        demo: The demo whose title seeds the ``title`` tag.
        meta: Optional metadata config supplying author, title override, date,
            source, and url. ``None`` means "use the demo title only".
        version: DemoCreate version string folded into the credit line.

    Returns:
        A dict of non-empty ``tag -> value`` pairs.
    """
    author = source = url = ""
    title_override = date = ""
    if meta is not None:
        author = (meta.author or "").strip()
        source = (meta.source or "").strip()
        url = (meta.url or "").strip()
        title_override = (meta.title or "").strip()
        date = (meta.date or "").strip()

    title = title_override or (demo.title or "").strip()

    credit = "made with DemoCreate"
    if version.strip():
        credit = f"{credit} {version.strip()}"

    comment_parts = [credit]
    if source:
        comment_parts.append(f"source: {source}")
    if url:
        comment_parts.append(url)
    comment = " · ".join(comment_parts)

    tags: dict[str, str] = {
        "title": title,
        "artist": author,
        "date": date,
        "comment": comment,
        "description": comment,
    }
    return {key: value for key, value in tags.items() if value}


def _escape_ffmetadata(value: str) -> str:
    r"""Escape a value for the ``;FFMETADATA1`` format.

    The ffmetadata spec treats ``=``, ``;``, ``#``, ``\``, and a literal newline
    as special; each must be backslash-escaped. The backslash is escaped first so
    its own escapes are not double-processed.

    Args:
        value: Raw key or value text.

    Returns:
        The escaped text, safe to write on a ``key=value`` line.
    """
    out = value.replace("\\", "\\\\")
    out = out.replace("=", "\\=")
    out = out.replace(";", "\\;")
    out = out.replace("#", "\\#")
    out = out.replace("\n", "\\\n")
    return out


def to_ffmetadata(tags: dict[str, str]) -> str:
    """Render tags as an ffmpeg ``;FFMETADATA1`` global-metadata document.

    The document opens with the required ``;FFMETADATA1`` magic line, then one
    escaped ``key=value`` line per tag (sorted for determinism). The shape is
    round-trippable: a reader splitting on the first unescaped ``=`` recovers the
    original keys and values.

    Args:
        tags: The ``tag -> value`` mapping (e.g. from :func:`build_tags`).

    Returns:
        The ffmetadata document text, terminated by a trailing newline.
    """
    lines = [";FFMETADATA1"]
    for key in sorted(tags):
        lines.append(f"{_escape_ffmetadata(key)}={_escape_ffmetadata(tags[key])}")
    return "\n".join(lines) + "\n"


def ffmpeg_metadata_args(tags: dict[str, str]) -> list[str]:
    """Build a flat ``-metadata k=v`` argv fragment for direct ffmpeg use.

    Each tag contributes two argv tokens: the literal ``"-metadata"`` flag and a
    single ``"key=value"`` string (ffmpeg parses the ``=`` itself, so the value is
    not pre-escaped here). Keys are sorted so the fragment is deterministic.

    Args:
        tags: The ``tag -> value`` mapping (e.g. from :func:`build_tags`).

    Returns:
        A flat list alternating ``"-metadata"`` and ``"key=value"``.
    """
    args: list[str] = []
    for key in sorted(tags):
        args.append("-metadata")
        args.append(f"{key}={tags[key]}")
    return args


def embed_tags(mp4_in: Path, mp4_out: Path, tags: dict[str, str]) -> Path:  # pragma: no cover - requires the ffmpeg binary
    """Write container metadata into an MP4 by stream-copying through ffmpeg.

    Runs ``ffmpeg -i mp4_in <-metadata ...> -codec copy mp4_out`` so the video and
    audio streams are copied verbatim (no re-encode) while the global metadata is
    replaced with ``tags``.

    Args:
        mp4_in: Source MP4 to read.
        mp4_out: Destination MP4 to write (parent dirs are created).
        tags: The ``tag -> value`` mapping to embed (e.g. from :func:`build_tags`).

    Returns:
        ``mp4_out``.

    Raises:
        BackendUnavailableError: If the ``ffmpeg`` binary is not on ``PATH``.
        RenderError: If the ffmpeg subprocess exits non-zero.
    """
    if shutil.which("ffmpeg") is None:
        raise BackendUnavailableError("ffmpeg", extra="video")

    mp4_out.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = ["ffmpeg", "-y", "-i", str(mp4_in)]
    cmd += ffmpeg_metadata_args(tags)
    cmd += ["-codec", "copy", str(mp4_out)]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RenderError(f"ffmpeg metadata embed failed: {result.stderr.strip()[-800:]}")
    logger.info("embedded %d metadata tag(s) → %s", len(tags), mp4_out)
    return mp4_out
