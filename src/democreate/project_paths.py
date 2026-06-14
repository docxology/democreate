"""Path resolution for DemoCreate runs.

A :class:`Workspace` centralizes every output location for a single demo build so
no module hardcodes machine paths. Layout under a chosen root::

    <root>/
      demos/        serialized Demo artifacts (.json / .yaml)
      audio/        rendered TTS audio (.wav)
      frames/       rendered still frames (.png)
      video/        assembled video (.mp4 / .gif / .webm)
      captions/     subtitle files (.srt / .ass / .vtt)
      web/          interactive HTML player
      manifests/    deterministic render manifests (.json)

All directories are created lazily on first access.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

__all__ = ["Workspace", "default_output_root", "relativize_under_root"]


def default_output_root() -> Path:
    """Return the conventional output root (``./output`` under the cwd)."""
    return Path.cwd() / "output"


def relativize_under_root(obj: Any, root: Path | str) -> Any:
    """Rewrite absolute-path strings under ``root`` to ``root``-relative POSIX form.

    Serialized render artifacts (the render manifest, ``demo.json``) embed the
    on-disk path of the audio they reference. That path includes the workspace
    root, which is machine- and run-specific (a fresh temp dir each build), so an
    artifact serialized with it is *not* byte-stable across runs or machines — the
    very ``byte-stable manifest`` property the project claims. This normalizes
    every such string to a ``root``-relative POSIX path (``audio/c1.wav``) while
    leaving every non-path value untouched, restoring byte-stability.

    The match is tried both lexically and after ``resolve()`` so the macOS
    ``/var`` → ``/private/var`` symlink does not defeat it. Returns a new
    structure; the input is not mutated.
    """
    root_path = Path(root)
    bases = (root_path, root_path.resolve())

    def fix(value: Any) -> Any:
        if isinstance(value, str) and value and Path(value).is_absolute():
            candidate = Path(value)
            for base in bases:
                try:
                    return candidate.relative_to(base).as_posix()
                except ValueError:
                    continue
            try:
                return candidate.resolve().relative_to(root_path.resolve()).as_posix()
            except ValueError:
                return value
        if isinstance(value, dict):
            return {k: fix(v) for k, v in value.items()}
        if isinstance(value, list):
            return [fix(v) for v in value]
        return value

    return fix(obj)


@dataclass
class Workspace:
    """Resolved output locations for one demo build.

    Args:
        root: Base directory under which all subdirectories live.
    """

    root: Path

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root is not None else default_output_root()

    def _sub(self, name: str) -> Path:
        path = self.root / name
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def demos(self) -> Path:
        """Directory for serialized :class:`~democreate.schema.Demo` artifacts."""
        return self._sub("demos")

    @property
    def audio(self) -> Path:
        """Directory for rendered TTS audio."""
        return self._sub("audio")

    @property
    def frames(self) -> Path:
        """Directory for rendered still frames."""
        return self._sub("frames")

    @property
    def video(self) -> Path:
        """Directory for assembled video output."""
        return self._sub("video")

    @property
    def captions(self) -> Path:
        """Directory for subtitle/caption files."""
        return self._sub("captions")

    @property
    def web(self) -> Path:
        """Directory for the interactive HTML player."""
        return self._sub("web")

    @property
    def manifests(self) -> Path:
        """Directory for deterministic render manifests."""
        return self._sub("manifests")

    def clean(self) -> None:
        """Remove the entire workspace root if it exists (idempotent)."""
        import shutil

        if self.root.exists():
            shutil.rmtree(self.root)
