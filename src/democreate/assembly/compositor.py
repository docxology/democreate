"""Timeline construction and compositor backends.

The :class:`Timeline` is the pure, central data structure of the assembly
subsystem: a fully-resolved, gap-free sequence of :class:`TimelineEntry` objects,
each pairing an absolute time window with a renderable
:class:`~democreate.media.FrameState`. :func:`build_timeline` walks a
:class:`~democreate.schema.Demo` and produces this structure deterministically,
with no I/O and only core dependencies.

Compositors turn a timeline into rendered output. The deterministic default,
:class:`ManifestCompositor`, writes a JSON render manifest plus one representative
PNG per entry using only Pillow. :class:`MoviePyCompositor` is a guarded legacy
adapter slot behind the ``video`` extra and is excluded from coverage.
"""

from __future__ import annotations

import abc
import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .._logging import get_logger, log_stage
from ..errors import BackendUnavailableError, RenderError
from ..media import FrameState
from ..project_paths import relativize_under_root
from ..schema import ActionType, Demo, SceneKind

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..project_paths import Workspace

logger = get_logger(__name__)

__all__ = [
    "TimelineEntry",
    "Timeline",
    "build_timeline",
    "Compositor",
    "ManifestCompositor",
    "MoviePyCompositor",
]


@dataclass
class TimelineEntry:
    """One contiguous slice of the timeline.

    Attributes:
        index: Zero-based position of this entry in the timeline.
        start_ms: Absolute start time (ms from demo start).
        end_ms: Absolute end time (ms from demo start), exclusive.
        state: The renderable :class:`~democreate.media.FrameState` for the slice.
        audio_path: Path to the chunk's narration audio, if any.
        chunk_id: Id of the source chunk, if this entry maps to one.
    """

    index: int
    start_ms: int
    end_ms: int
    state: FrameState
    audio_path: str | None = None
    chunk_id: str | None = None

    @property
    def duration_ms(self) -> int:
        """Length of this entry's time window in milliseconds."""
        return self.end_ms - self.start_ms

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-ready dict."""
        return {
            "index": self.index,
            "start_ms": self.start_ms,
            "end_ms": self.end_ms,
            "duration_ms": self.duration_ms,
            "state": self.state.to_dict(),
            "audio_path": self.audio_path,
            "chunk_id": self.chunk_id,
        }


@dataclass
class Timeline:
    """A fully-resolved, gap-free render timeline.

    Attributes:
        entries: Ordered, non-overlapping timeline entries.
        total_ms: Total runtime (end of the last entry).
        fps: Frame rate the timeline will be rendered at.
    """

    entries: list[TimelineEntry]
    total_ms: int
    fps: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize the whole timeline to a JSON-ready dict."""
        return {
            "total_ms": self.total_ms,
            "fps": self.fps,
            "frame_count": self.frame_count(),
            "entries": [e.to_dict() for e in self.entries],
        }

    def frame_count(self) -> int:
        """Total number of frames at this timeline's fps.

        Returns:
            ``round(total_ms / 1000 * fps)``.
        """
        return int(round(self.total_ms / 1000 * self.fps))

    def entry_at_ms(self, t: int) -> TimelineEntry | None:
        """Return the entry whose window contains ``t``.

        Args:
            t: Absolute time in milliseconds.

        Returns:
            The matching :class:`TimelineEntry`, or ``None`` if ``t`` falls
            outside every entry (e.g. negative, or at/after ``total_ms``).
        """
        for entry in self.entries:
            if entry.start_ms <= t < entry.end_ms:
                return entry
        return None


def _state_for_chunk(
    demo: Demo,
    scene_kind: SceneKind,
    scene_title: str,
    scene_context: dict[str, Any],
    chunk: Any,
) -> FrameState:
    """Build the :class:`FrameState` a single chunk renders to.

    The chunk's actions mutate a fresh frame state appropriate to the scene kind:
    file opens populate an editor frame, ``run_command`` populates a terminal
    frame, ``navigate`` populates a browser frame, and so on. The chunk text is
    always carried as the caption.

    Args:
        demo: The owning demo (unused today, reserved for global context).
        scene_kind: The kind of the owning scene.
        scene_title: The owning scene's title (used as a default frame title).
        scene_context: The owning scene's free-form context dict.
        chunk: The chunk whose actions shape the frame.

    Returns:
        A populated :class:`FrameState`.
    """
    state = FrameState(scene_kind=scene_kind, title=scene_title, caption=chunk.text)

    if scene_context:
        base_url = str(scene_context.get("base_url", ""))
        if base_url:
            state.url = base_url
        if scene_context.get("section"):
            state.section = str(scene_context["section"])
        if scene_context.get("subtitle"):
            state.subtitle = str(scene_context["subtitle"])
        if scene_context.get("background_image"):
            state.background_image = str(scene_context["background_image"])
        if scene_context.get("bullets"):
            state.bullets = [str(b) for b in scene_context["bullets"]]
        if scene_context.get("stats"):
            # Tolerate a malformed authored `stats:` (e.g. a flat list) instead of
            # crashing mid-render: keep only well-formed (value, label) pairs.
            state.stats = [
                (str(e[0]), str(e[1]))
                for e in scene_context["stats"]
                if isinstance(e, (list, tuple)) and len(e) == 2
            ]

    for action in chunk.actions:
        params = action.params or {}
        atype = action.type
        if atype in (ActionType.OPEN_FILE, ActionType.CREATE_FILE):
            path = str(params.get("path", ""))
            if path:
                state.file_path = path
                state.title = path
            code = params.get("code")
            if isinstance(code, str):
                state.code_lines = code.splitlines() or [code]
            elif isinstance(code, list):
                state.code_lines = [str(line) for line in code]
        elif atype == ActionType.TYPE_CODE:
            code = params.get("code", "")
            if isinstance(code, list):
                new_lines = [str(line) for line in code]
            else:
                new_lines = str(code).splitlines() or [str(code)]
            state.code_lines = state.code_lines + new_lines
        elif atype == ActionType.HIGHLIGHT_LINES:
            lines = params.get("lines", [])
            if isinstance(lines, (list, tuple)):
                state.highlight_lines = [int(n) for n in lines]
            elif isinstance(lines, int):
                state.highlight_lines = [lines]
        elif atype in (ActionType.RUN_COMMAND, ActionType.PRINT_OUTPUT):
            if state.scene_kind == SceneKind.CODEBASE:
                state.scene_kind = SceneKind.TERMINAL
            command = params.get("command")
            output = params.get("output")
            if command is not None:
                state.terminal_lines = state.terminal_lines + [f"$ {command}"]
            if output is not None:
                extra = (
                    [str(line) for line in output]
                    if isinstance(output, (list, tuple))
                    else str(output).splitlines()
                )
                state.terminal_lines = state.terminal_lines + extra
        elif atype == ActionType.NAVIGATE:
            if state.scene_kind == SceneKind.CODEBASE:
                state.scene_kind = SceneKind.WEBSITE
            url = params.get("url")
            if url:
                state.url = str(url)
        elif atype == ActionType.MOVE_MOUSE:
            xy = params.get("xy") or params.get("position")
            if isinstance(xy, (list, tuple)) and len(xy) == 2:
                state.cursor_xy = (int(xy[0]), int(xy[1]))
        elif atype in (ActionType.ZOOM, ActionType.PAN):
            scale = params.get("scale")
            if scale is not None:
                state.scale = float(scale)

    return state


def build_timeline(
    demo: Demo, *, fps: int | None = None, wpm: int = 150
) -> Timeline:
    """Build a gap-free render timeline from a demo (pure, deterministic).

    Walks scenes then chunks in order. Each chunk becomes exactly one
    :class:`TimelineEntry`. A chunk's start time is its synced ``start_ms`` when
    present (post-sync), otherwise the running cumulative estimate. Each entry's
    duration is the chunk's estimated narration duration. Entries are laid down
    back-to-back with no gaps, so ``total_ms`` is the end of the last entry.

    Args:
        demo: The source demo.
        fps: Frame rate for the timeline; defaults to ``demo.fps``.
        wpm: Words-per-minute used to estimate chunk duration when no synced
            timing exists.

    Returns:
        A resolved :class:`Timeline`.
    """
    use_fps = fps if fps is not None else demo.fps
    entries: list[TimelineEntry] = []
    cursor_ms = 0
    index = 0

    with log_stage("build_timeline", logger):
        for scene in demo.scenes:
            for chunk in scene.chunks:
                duration = chunk.estimated_duration_ms(wpm)
                start = chunk.start_ms if chunk.start_ms is not None else cursor_ms
                # Guard against synced starts that would create a backwards gap;
                # never emit overlapping/decreasing entries.
                if start < cursor_ms:
                    start = cursor_ms
                end = start + duration
                state = _state_for_chunk(
                    demo, scene.kind, scene.title, scene.context, chunk
                )
                entries.append(
                    TimelineEntry(
                        index=index,
                        start_ms=start,
                        end_ms=end,
                        state=state,
                        audio_path=chunk.audio_path,
                        chunk_id=chunk.id,
                    )
                )
                cursor_ms = end
                index += 1

    total_ms = entries[-1].end_ms if entries else 0
    return Timeline(entries=entries, total_ms=total_ms, fps=use_fps)


class Compositor(abc.ABC):
    """Abstract base for everything that turns a :class:`Timeline` into output."""

    @abc.abstractmethod
    def compose(self, timeline: Timeline, workspace: Workspace) -> Path:
        """Render ``timeline`` into ``workspace`` and return the primary artifact.

        Args:
            timeline: The resolved timeline to render.
            workspace: Output locations for this build.

        Returns:
            Path to the primary output artifact this compositor produced.
        """
        raise NotImplementedError


class ManifestCompositor(Compositor):
    """The deterministic default compositor (core deps only).

    Writes ``render_manifest.json`` (the full :meth:`Timeline.to_dict`) into
    ``workspace.manifests`` and one representative PNG per timeline entry into
    ``workspace.frames``. Frame rendering is delegated to
    ``democreate.capture.screen.render_frame`` when that module is importable;
    otherwise a built-in Pillow fallback renders a simple labelled placeholder so
    the default path always produces real images with only core dependencies.
    """

    def __init__(self, *, width: int = 1280, height: int = 720, theme=None) -> None:
        """Initialize the compositor.

        Args:
            width: Fallback frame width in pixels (when the real renderer is
                unavailable).
            height: Fallback frame height in pixels.
            theme: Optional :class:`~democreate.config.Theme` for frame colors.
        """
        self.width = width
        self.height = height
        self.theme = theme

    def compose(self, timeline: Timeline, workspace: Workspace) -> Path:
        """Write the render manifest and per-entry frames.

        Args:
            timeline: The resolved timeline to render.
            workspace: Output locations for this build.

        Returns:
            Path to ``render_manifest.json``.

        Raises:
            RenderError: If the manifest or any frame could not be written.
        """
        render_frame = self._resolve_render_frame()
        try:
            manifest_path = workspace.manifests / "render_manifest.json"
            # Relativize embedded audio paths against the workspace root so the
            # manifest is byte-stable across runs/machines (see sec:evaluation).
            manifest = relativize_under_root(timeline.to_dict(), workspace.root)
            manifest_path.write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            frames_dir = workspace.frames
            size = (self.width, self.height)
            for entry in timeline.entries:
                frame_path = frames_dir / f"frame_{entry.index:04d}.png"
                if render_frame is not None:
                    image = render_frame(entry.state, size, theme=self.theme)
                    image.save(frame_path, format="PNG")
                else:  # pragma: no cover - core-only fallback path
                    self._render_fallback(entry.state, frame_path)
        except OSError as exc:
            raise RenderError(f"failed to compose timeline: {exc}") from exc

        logger.info(
            "composed %d frame(s) + manifest at %s",
            len(timeline.entries),
            manifest_path,
        )
        return manifest_path

    @staticmethod
    def _resolve_render_frame() -> Any | None:
        """Return ``capture.screen.render_frame`` if importable, else ``None``."""
        if importlib.util.find_spec("democreate.capture.screen") is None:
            return None
        try:
            from democreate.capture.screen import render_frame
        except Exception:  # pragma: no cover - defensive, build-order dependent
            return None
        return render_frame

    def _render_fallback(self, state: FrameState, path: Path) -> None:
        """Render a deterministic placeholder PNG with only Pillow.

        Args:
            state: The frame state to depict.
            path: Destination PNG path.
        """
        from PIL import Image, ImageDraw

        backgrounds = {
            SceneKind.CODEBASE: (30, 30, 46),
            SceneKind.TERMINAL: (12, 12, 12),
            SceneKind.WEBSITE: (245, 245, 245),
            SceneKind.SLIDE: (20, 40, 70),
        }
        bg = backgrounds.get(state.scene_kind, (30, 30, 46))
        fg = (20, 20, 20) if state.scene_kind == SceneKind.WEBSITE else (220, 220, 220)
        img = Image.new("RGB", (self.width, self.height), bg)
        draw = ImageDraw.Draw(img)

        lines: list[str] = [f"[{state.scene_kind.value}] {state.title}".strip()]
        if state.url:
            lines.append(state.url)
        if state.file_path:
            lines.append(state.file_path)
        lines.extend(state.code_lines[:20])
        lines.extend(state.terminal_lines[:20])
        if state.caption:
            lines.append("")
            lines.append(state.caption)

        y = 20
        for line in lines:
            draw.text((24, y), line, fill=fg)
            y += 18
        img.save(path, format="PNG")


class MoviePyCompositor(Compositor):
    """Guarded legacy MoviePy compositor slot (extra: ``video``)."""

    def compose(self, timeline: Timeline, workspace: Workspace) -> Path:  # pragma: no cover
        """Detect the legacy MoviePy compositor dependency.

        Args:
            timeline: The resolved timeline to render.
            workspace: Output locations for this build.

        Returns:
            Path to the assembled video if a future implementation is wired.

        Raises:
            BackendUnavailableError: If MoviePy is not installed.
            NotImplementedError: If MoviePy is installed; the real compositor is
                not wired yet.
        """
        if importlib.util.find_spec("moviepy") is None:
            raise BackendUnavailableError("moviepy", extra="video")
        raise NotImplementedError("MoviePyCompositor real assembly not yet implemented")
