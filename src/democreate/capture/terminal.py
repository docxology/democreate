"""Terminal recordings in asciinema asciicast v2 format (pure Python).

This module models a terminal session as a stream of timed events and serializes
it to the `asciicast v2 <https://docs.asciinema.org/manual/asciicast/v2/>`_
format: a header JSON object on the first line, followed by one ``[time, kind,
data]`` JSON array per event line. The whole thing is dependency-free and
deterministic, so a list of ``(command, output)`` pairs can be turned into a
recording — and into renderable terminal :class:`~democreate.media.FrameState`
snapshots — without ever launching a real shell.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field

from ..errors import CaptureError
from ..media import FrameState
from ..schema import SceneKind

__all__ = [
    "AsciicastEvent",
    "AsciicastRecording",
    "record_commands",
    "recording_to_frame_states",
]

# Deterministic synthetic timing model (seconds).
_TYPE_TIME = 0.04  # time to "type" one command, charged per command
_OUTPUT_DELAY = 0.20  # gap between input and its output


@dataclass
class AsciicastEvent:
    """One terminal event at a relative time.

    Attributes:
        time: Seconds since the start of the recording.
        kind: Event channel — ``"o"`` for output, ``"i"`` for input.
        data: The UTF-8 text written on that channel.
    """

    time: float
    kind: str
    data: str

    def to_list(self) -> list:
        """Return the ``[time, kind, data]`` triple used on disk."""
        return [self.time, self.kind, self.data]

    @classmethod
    def from_list(cls, item: list) -> AsciicastEvent:
        """Build an event from a ``[time, kind, data]`` triple.

        Args:
            item: A 3-element sequence ``[time, kind, data]``.

        Returns:
            The parsed :class:`AsciicastEvent`.
        """
        if not isinstance(item, list) or len(item) != 3:
            raise CaptureError("asciicast event must be a [time, kind, data] triple")
        time, kind, data = item
        if type(time) not in (int, float):
            raise CaptureError("asciicast event time must be numeric")
        try:
            seconds = float(time)
        except (ValueError, OverflowError) as exc:
            raise CaptureError("asciicast event time must be finite") from exc
        if not math.isfinite(seconds) or seconds < 0:
            raise CaptureError("asciicast event time must be finite and nonnegative")
        if not isinstance(kind, str) or not isinstance(data, str):
            raise CaptureError("asciicast event kind and data must be strings")
        return cls(time=seconds, kind=kind, data=data)


@dataclass
class AsciicastRecording:
    """An asciicast v2 recording: a header plus a stream of events.

    Attributes:
        version: asciicast format version (always 2).
        width: Terminal width in columns.
        height: Terminal height in rows.
        events: Ordered terminal events.
    """

    version: int = 2
    width: int = 80
    height: int = 24
    events: list[AsciicastEvent] = field(default_factory=list)

    def duration(self) -> float:
        """Return the time of the last event (0.0 for an empty recording)."""
        if not self.events:
            return 0.0
        return self.events[-1].time

    def header(self) -> dict:
        """Return the asciicast v2 header object."""
        return {"version": self.version, "width": self.width, "height": self.height}

    def to_json(self) -> str:
        """Serialize to asciicast v2 newline-delimited JSON.

        The first line is the header object; each subsequent line is one
        ``[time, kind, data]`` event array.

        Returns:
            The recording as a newline-delimited JSON string.
        """
        lines = [json.dumps(self.header(), ensure_ascii=False)]
        for event in self.events:
            lines.append(json.dumps(event.to_list(), ensure_ascii=False))
        return "\n".join(lines)

    @classmethod
    def from_json(cls, text: str) -> AsciicastRecording:
        """Parse a recording from asciicast v2 newline-delimited JSON.

        Args:
            text: The serialized recording (as produced by :meth:`to_json`).

        Returns:
            The parsed :class:`AsciicastRecording`.

        Raises:
            CaptureError: If the text is empty, the header is not valid JSON,
                or any event line is malformed — i.e. the terminal capture
                step failed.
        """
        stripped = [ln for ln in text.splitlines() if ln.strip()]
        if not stripped:
            raise CaptureError("asciicast recording is empty: no header line")
        try:
            header = json.loads(stripped[0])
        except ValueError as exc:
            raise CaptureError(f"asciicast header is not valid JSON: {exc}") from exc
        if not isinstance(header, dict):
            raise CaptureError("asciicast header must be a JSON object")
        geometry: dict[str, int] = {}
        for name in ("version", "width", "height"):
            value = header.get(name)
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise CaptureError(f"asciicast header {name} must be a positive integer")
            geometry[name] = value
        if geometry["version"] != 2:
            raise CaptureError("asciicast header version must be 2")
        events: list[AsciicastEvent] = []
        for line in stripped[1:]:
            try:
                events.append(AsciicastEvent.from_list(json.loads(line)))
            except (ValueError, CaptureError) as exc:
                raise CaptureError(
                    f"malformed asciicast event line {line[:40]!r}: {exc}"
                ) from exc
        return cls(
            version=geometry["version"],
            width=geometry["width"],
            height=geometry["height"],
            events=events,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AsciicastRecording):
            return NotImplemented
        return (
            self.version == other.version
            and self.width == other.width
            and self.height == other.height
            and [e.to_list() for e in self.events]
            == [e.to_list() for e in other.events]
        )


def record_commands(
    commands: list[tuple[str, str]], *, prompt: str = "$ "
) -> AsciicastRecording:
    """Build a deterministic recording from ``(command, output)`` pairs.

    Each pair contributes an input event (the prompt plus the typed command and a
    newline) followed, after a fixed delay, by an output event (the command's
    output). Timestamps increase monotonically.

    Args:
        commands: Ordered ``(command, output)`` pairs. An empty ``output`` emits
            no output event.
        prompt: The shell prompt rendered before each command.

    Returns:
        The constructed :class:`AsciicastRecording`.
    """
    events: list[AsciicastEvent] = []
    t = 0.0
    for command, output in commands:
        events.append(AsciicastEvent(time=round(t, 6), kind="i", data=f"{prompt}{command}\r\n"))
        t += _TYPE_TIME
        if output:
            t += _OUTPUT_DELAY
            data = output if output.endswith("\n") else output + "\n"
            events.append(AsciicastEvent(time=round(t, 6), kind="o", data=data))
    return AsciicastRecording(events=events)


def recording_to_frame_states(rec: AsciicastRecording) -> list[FrameState]:
    """Project a recording into terminal frame states for the renderer.

    Walks the event stream, accumulating rendered terminal lines, and emits a
    :class:`~democreate.media.FrameState` after each event so the renderer can
    show the terminal growing line by line.

    Args:
        rec: The recording to project.

    Returns:
        One terminal :class:`FrameState` per event (empty list if no events).
    """
    states: list[FrameState] = []
    lines: list[str] = []
    for event in rec.events:
        for raw in event.data.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            if raw == "" and not event.data.endswith("\n"):
                continue
            lines.append(raw)
        # drop a trailing empty line produced by a terminating newline
        rendered = [ln for ln in lines if ln != ""] or lines
        states.append(
            FrameState(
                scene_kind=SceneKind.TERMINAL,
                title="terminal",
                terminal_lines=list(rendered),
            )
        )
    return states
