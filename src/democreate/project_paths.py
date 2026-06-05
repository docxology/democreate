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

__all__ = ["Workspace", "default_output_root"]


def default_output_root() -> Path:
    """Return the conventional output root (``./output`` under the cwd)."""
    return Path.cwd() / "output"


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
