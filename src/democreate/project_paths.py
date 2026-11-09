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

import hashlib
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .errors import RenderError

if TYPE_CHECKING:
    from .schema import Demo

__all__ = ["Workspace", "default_output_root", "relativize_under_root", "stage_demo_assets"]


def default_output_root() -> Path:
    """Return the conventional output root (``./output`` under the cwd)."""
    return Path.cwd() / "output"


#: Dict keys whose string values are filesystem paths that may embed the
#: workspace root. Relativization is restricted to these so an authored title or
#: caption that merely *starts with* the root path is never mistaken for a path
#: and mangled (Forge cross-vendor finding).
_PATH_KEYS = frozenset(
    {"audio_path", "path", "frame_path", "image", "image_path", "background_image"}
)


def relativize_under_root(obj: Any, root: Path | str) -> Any:
    """Rewrite absolute-path strings under ``root`` to ``root``-relative POSIX form.

    Serialized render artifacts (the render manifest, ``demo.json``) embed the
    on-disk path of the audio they reference. That path includes the workspace
    root, which is machine- and run-specific (a fresh temp dir each build), so an
    artifact serialized with it is *not* byte-stable across runs or machines — the
    very ``byte-stable manifest`` property the project claims. This normalizes
    such strings to a ``root``-relative POSIX path (``audio/c1.wav``) while
    leaving every non-path value untouched, restoring byte-stability.

    Only string values stored under a known path key (:data:`_PATH_KEYS`) are
    rewritten, so an authored title/caption that happens to begin with the root
    path is never corrupted. The match is tried both lexically and after
    ``resolve()`` so the macOS ``/var`` → ``/private/var`` symlink does not defeat
    it. Returns a new structure; the input is not mutated.
    """
    root_path = Path(root)
    bases = (root_path, root_path.resolve())

    def relativize_str(value: str) -> str:
        if not (value and Path(value).is_absolute()):
            return value
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

    def fix(value: Any, *, under_path_key: bool = False) -> Any:
        if isinstance(value, str):
            return relativize_str(value) if under_path_key else value
        if isinstance(value, dict):
            return {k: fix(v, under_path_key=k in _PATH_KEYS) for k, v in value.items()}
        if isinstance(value, list):
            return [fix(v, under_path_key=under_path_key) for v in value]
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
        selected = Path(root) if root is not None else default_output_root()
        if selected.is_symlink():
            raise RenderError("workspace root must not be a symbolic link")
        self.root = selected.resolve()
        self.ensure_safe()

    def ensure_safe(self) -> None:
        """Refuse existing links in generated namespaces before local writes.

        This guards cooperative builds, not malicious concurrent replacement by
        another process with the same user's filesystem privileges.
        """
        for name in (
            "demos", "audio", "frames", "video", "captions", "web", "manifests",
            "provenance", "chapters", "assets", "pages",
        ):
            path = self.root / name
            if path.is_symlink():
                raise RenderError(f"symbolic link in workspace output: {path}")
            if path.is_dir():
                for child in path.rglob("*"):
                    if child.is_symlink():
                        raise RenderError(f"symbolic link in workspace output: {child}")

    def _sub(self, name: str) -> Path:
        path = self.root / name
        if path.is_symlink():
            raise RenderError(f"symbolic link in workspace output: {path}")
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


def stage_demo_assets(demo: Demo, workspace: Workspace, asset_root: Path) -> None:
    """Confine required backgrounds to an explicit root and stage portable copies.

    Args:
        demo: Demo whose background paths are updated to staged assets.
        workspace: Caller-owned generated output tree.
        asset_root: Trusted input root, also the base of relative image paths.

    Raises:
        RenderError: If a required image is missing, fails verification or RGB
            decoding, is outside the allowed roots, or changes while staged.
    """
    allowed = asset_root.resolve()
    staged: dict[Path, Path] = {}
    for scene in demo.scenes:
        for key in ("background_image",):
            raw = scene.context.get(key)
            if not raw:
                continue
            source = Path(str(raw))
            source = (source if source.is_absolute() else allowed / source).resolve()
            if not (source.is_relative_to(allowed) or source.is_relative_to(workspace.root)):
                raise RenderError(f"background image is outside the asset root: {raw}")
            if not source.is_file():
                raise RenderError(f"required background image is missing: {raw}")
            if source not in staged:
                from PIL import Image

                try:
                    with Image.open(source) as image:
                        image.verify()
                    # Container verification alone need not decompress pixel data.
                    # Reopen, as required by Pillow after verify(), and perform the
                    # same RGB conversion as the renderer before narration writes.
                    with Image.open(source) as image:
                        image.convert("RGB").close()
                except (OSError, SyntaxError, ValueError, Image.DecompressionBombError) as exc:
                    raise RenderError(f"cannot decode background image: {raw}") from exc
                with source.open("rb") as stream:
                    digest = hashlib.file_digest(stream, "sha256").hexdigest()
                assets = workspace._sub("assets")
                destination = assets / f"{digest}{source.suffix.lower()}"
                if source != destination:
                    temporary: Path | None = None
                    try:
                        with tempfile.NamedTemporaryFile(dir=assets, delete=False) as temp:
                            temporary = Path(temp.name)
                            with source.open("rb") as stream:
                                shutil.copyfileobj(stream, temp)
                        with temporary.open("rb") as check:
                            if hashlib.file_digest(check, "sha256").hexdigest() != digest:
                                raise RenderError("background image changed while staging")
                        temporary.replace(destination)
                    finally:
                        if temporary is not None:
                            temporary.unlink(missing_ok=True)
                staged[source] = destination
            scene.context[key] = str(staged[source])
