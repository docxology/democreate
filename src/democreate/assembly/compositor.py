"""Timeline construction and compositor backends.

The :class:`Timeline` is the pure, central data structure of the assembly
subsystem: a fully-resolved, non-overlapping sequence of :class:`TimelineEntry` objects,
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
from copy import deepcopy
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import TYPE_CHECKING, Any

from .._logging import get_logger, log_stage
from ..errors import BackendUnavailableError, RenderError
from ..media import FrameState
from ..project_paths import relativize_under_root
from ..schema import Action, ActionType, Demo, SceneKind

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
    """One narration window, with a final still and scheduled scene playback.

    ``state`` is a representative final snapshot for per-chunk stills, not the
    state shown throughout animated playback. ``initial_state`` is the scene's
    opening state; ``actions`` is its shared, absolute-time event stream. Replay
    starts from that opening state so actions spanning chunks remain in flight.
    """

    index: int
    start_ms: int
    end_ms: int
    state: FrameState
    audio_path: str | None = None
    chunk_id: str | None = None
    initial_state: FrameState | None = None
    actions: tuple[Action, ...] = field(default_factory=tuple)

    def state_at_ms(self, t_ms: int, *, typing: bool = True) -> FrameState:
        """Return an independent scene snapshot at absolute ``t_ms``.

        Events are invisible before their trigger. With ``typing=True``, code
        interpolates over its duration; otherwise complete code appears at its
        trigger. Camera/pointer motion and command completion retain their
        durations in either mode. Untimed entries constructed directly retain
        their still.
        """
        if self.initial_state is None:
            return deepcopy(self.state)
        state = _replay(self.initial_state, self.actions, t_ms, typing=typing)
        state.caption = self.state.caption
        return state

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
            "initial_state": (
                self.initial_state.to_dict() if self.initial_state is not None else None
            ),
            "actions": [action.to_dict() for action in self.actions],
        }


@dataclass
class Timeline:
    """A fully-resolved, non-overlapping render timeline.

    Attributes:
        entries: Ordered, non-overlapping timeline entries.
        total_ms: Total runtime, including trailing silence after the last entry.
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


def _scene_state(
    scene_kind: SceneKind, scene_title: str, scene_context: dict[str, Any]
) -> FrameState:
    """Construct the opening surface once per scene, without applying events."""
    state = FrameState(scene_kind=scene_kind, title=scene_title)

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

    return state


def _code_lines(value: Any, progress: float) -> list[str]:
    """Reveal a code payload without hiding previously displayed code."""
    lines = [str(line) for line in value] if isinstance(value, list) else (
        str(value).split("\n")
    )
    if progress >= 1:
        return lines
    text = "\n".join(lines)
    visible = text[:int(len(text) * progress)]
    return visible.split("\n") if visible else []


def _apply_action(
    state: FrameState, action: Action, progress: float, files: dict[str, list[str]]
) -> None:
    """Apply one triggered event to a private replay state."""
    params = action.params or {}
    atype = action.type
    if atype in (ActionType.OPEN_FILE, ActionType.CREATE_FILE):
        path = str(params.get("path", ""))
        state.file_path = path
        state.title = path
        if state.scene_kind != SceneKind.SLIDE:
            state.scene_kind = SceneKind.CODEBASE
        state.highlight_lines = []
        code = params.get("code")
        if isinstance(code, (str, list)):
            state.code_lines = _code_lines(code, progress)
        elif atype == ActionType.CREATE_FILE:
            state.code_lines = []
        else:
            state.code_lines = list(files.get(path, []))
    elif atype == ActionType.TYPE_CODE:
        if state.scene_kind != SceneKind.SLIDE:
            state.scene_kind = SceneKind.CODEBASE
        code = params.get("code", "")
        if isinstance(code, list):
            state.code_lines = state.code_lines + _code_lines(code, progress)
        else:
            text = str(code)
            visible = text[:int(len(text) * progress)]
            content = "\n".join(state.code_lines) + visible
            state.code_lines = content.split("\n") if content else []
    elif atype == ActionType.CLOSE_FILE:
        if str(params.get("path", state.file_path)) == state.file_path:
            state.file_path = ""
            state.title = ""
            state.code_lines = []
            state.highlight_lines = []
    elif atype == ActionType.HIGHLIGHT_LINES:
        lines = params.get("lines", [])
        if isinstance(lines, (list, tuple)):
            state.highlight_lines = [int(n) for n in lines]
        elif isinstance(lines, int):
            state.highlight_lines = [lines]
    elif atype in (ActionType.RUN_COMMAND, ActionType.PRINT_OUTPUT):
        state.scene_kind = SceneKind.TERMINAL
        command = params.get("command")
        if command is not None:
            state.terminal_lines.append(f"$ {command}")
    elif atype == ActionType.NAVIGATE:
        state.scene_kind = SceneKind.WEBSITE
        if params.get("url"):
            state.url = str(params["url"])
    elif atype in (ActionType.MOVE_MOUSE, ActionType.CLICK):
        xy = params.get("xy") or params.get("position")
        if isinstance(xy, (list, tuple)) and len(xy) == 2:
            origin = state.cursor_xy or (int(xy[0]), int(xy[1]))
            state.cursor_xy = (
                round(origin[0] + (int(xy[0]) - origin[0]) * progress),
                round(origin[1] + (int(xy[1]) - origin[1]) * progress),
            )
    elif atype in (ActionType.ZOOM, ActionType.PAN):
        scale = params.get("scale")
        if scale is not None:
            state.scale += (float(scale) - state.scale) * progress
    if state.file_path:
        files[state.file_path] = list(state.code_lines)


def _replay(
    initial: FrameState, actions: tuple[Action, ...], t_ms: int | None,
    *, typing: bool = True,
) -> FrameState:
    """Replay starts and terminal completions in stable chronological order."""
    state = deepcopy(initial)
    files: dict[str, list[str]] = {}
    effects: list[tuple[int, int, bool, Action]] = []
    for index, action in enumerate(actions):
        start = action.timestamp_ms if action.timestamp_ms is not None else 0
        effects.append((start, index, False, action))
        if action.type in (ActionType.RUN_COMMAND, ActionType.PRINT_OUTPUT):
            if (action.params or {}).get("output") is not None:
                effects.append((
                    start + max(0, action.duration_ms or 0), index, True, action,
                ))
    # Scene action order breaks timestamp ties; a zero-duration action's prompt
    # precedes its own output. Completion appends without changing the surface.
    for when, _, completion, action in sorted(effects):
        if t_ms is not None and t_ms < when:
            break
        if completion:
            output = action.params["output"]
            state.terminal_lines.extend(
                [str(line) for line in output]
                if isinstance(output, (list, tuple)) else str(output).splitlines()
            )
            continue
        duration = max(0, action.duration_ms or 0)
        progress = (
            1.0 if t_ms is None or duration == 0
            else min(1.0, (t_ms - when) / duration)
        )
        if not typing and action.type in (
            ActionType.OPEN_FILE, ActionType.CREATE_FILE, ActionType.TYPE_CODE,
        ):
            progress = 1.0
        _apply_action(state, action, progress, files)
    return state


def build_timeline(
    demo: Demo, *, fps: int | None = None, wpm: int = 150, trail_ms: int = 0
) -> Timeline:
    """Build measured narration windows and an event-sourced scene timeline.

    Synced starts retain lead/gap silence and are clamped only to prevent overlap.
    Each final still includes prior scene events, while scheduled playback replays
    absolute action timestamps and durations independently of chunk boundaries.

    Args:
        demo: The source demo.
        fps: Frame rate for the timeline; defaults to ``demo.fps``.
        wpm: Words-per-minute used to estimate chunk duration when no synced
            timing exists.
        trail_ms: Silent tail included in total runtime, not subtitle windows.

    Returns:
        A resolved :class:`Timeline`.
    """
    use_fps = fps if fps is not None else demo.fps
    if use_fps <= 0:
        raise ValueError("fps must be positive")
    if isinstance(trail_ms, bool) or not isinstance(trail_ms, int) or trail_ms < 0:
        raise ValueError("trail_ms must be a nonnegative integer")
    entries: list[TimelineEntry] = []
    cursor_ms = 0
    index = 0

    with log_stage("build_timeline", logger):
        for scene in demo.scenes:
            initial = _scene_state(scene.kind, scene.title, scene.context)
            scene_entries: list[TimelineEntry] = []
            scene_actions: list[Action] = []
            for chunk in scene.chunks:
                duration = chunk.playback_duration_ms(wpm)
                start = max(
                    cursor_ms, chunk.start_ms if chunk.start_ms is not None else cursor_ms
                )
                end = start + duration
                action_cursor = start
                for authored in chunk.actions:
                    action = deepcopy(authored)
                    if action.timestamp_ms is None:
                        action.timestamp_ms = action_cursor
                    action_cursor = max(
                        action_cursor, action.timestamp_ms + max(0, action.duration_ms or 0)
                    )
                    scene_actions.append(action)
                ordered = tuple(sorted(
                    scene_actions, key=lambda action: action.timestamp_ms or 0
                ))
                state = _replay(initial, ordered, None)
                state.caption = chunk.text
                entry = TimelineEntry(
                    index=index, start_ms=start, end_ms=end, state=state,
                    audio_path=chunk.audio_path, chunk_id=chunk.id,
                    initial_state=initial,
                )
                entries.append(entry)
                scene_entries.append(entry)
                cursor_ms = end
                index += 1
            # Share one immutable scene event sequence, never rendered images or
            # mutable snapshots; delayed events can continue into later chunks.
            actions = tuple(sorted(
                scene_actions, key=lambda action: action.timestamp_ms or 0
            ))
            for entry in scene_entries:
                entry.actions = actions

    total_ms = entries[-1].end_ms + trail_ms if entries else 0
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
    ``workspace.frames``. The required core synthetic renderer writes captionless
    base images; timed HTML cues or explicit SRT burning supply narration text.
    Broken core imports and image errors propagate, never become placeholders.
    """

    def __init__(self, *, width: int = 1280, height: int = 720, theme=None) -> None:
        """Initialize the compositor.

        Args:
            width: Frame width in pixels.
            height: Frame height in pixels.
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
        from ..capture.screen import render_frame
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
                state = replace(entry.state, caption="")
                image = render_frame(state, size, theme=self.theme)
                image.save(frame_path, format="PNG")
        except OSError as exc:
            raise RenderError(f"failed to compose timeline: {exc}") from exc

        logger.info(
            "composed %d frame(s) + manifest at %s",
            len(timeline.entries),
            manifest_path,
        )
        return manifest_path



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
