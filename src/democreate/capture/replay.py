"""Input record/replay — a pure event model with guarded real backends.

Real mouse/keyboard recording and replay need OS-level hooks (``pynput`` to
record, ``pyautogui`` to replay) and a live desktop, so they live behind the
``replay`` extra. The *event model* — :class:`InputEvent` and :class:`EventLog`
— is pure, serializable, and maps cleanly onto schema :class:`~democreate.schema.Action`
objects, so recorded sessions can be edited and re-rendered through the
deterministic pipeline like any other demo content.
"""

from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .._logging import get_logger
from ..errors import BackendUnavailableError
from ..schema import Action, ActionType

__all__ = [
    "InputEvent",
    "EventLog",
    "record_session",
    "replay_session",
]

logger = get_logger(__name__)


def _have(dep: str) -> bool:
    """Return ``True`` if an optional dependency is importable."""
    return importlib.util.find_spec(dep) is not None


@dataclass
class InputEvent:
    """A single recorded input event.

    Attributes:
        t_ms: Milliseconds since the start of the session.
        kind: One of ``"move"``, ``"click"``, or ``"key"``.
        payload: Event-specific data (e.g. ``{"x": 10, "y": 20}`` for a move,
            ``{"key": "a"}`` for a key).
    """

    t_ms: int
    kind: str
    payload: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-ready dict."""
        return {"t_ms": self.t_ms, "kind": self.kind, "payload": dict(self.payload)}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InputEvent:
        """Inverse of :meth:`to_dict`."""
        return cls(
            t_ms=int(data["t_ms"]),
            kind=str(data["kind"]),
            payload=dict(data.get("payload", {})),
        )


@dataclass
class EventLog:
    """An ordered log of input events.

    Attributes:
        events: The recorded events in capture order.
    """

    events: list[InputEvent] = field(default_factory=list)

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize the log to a JSON string."""
        return json.dumps(
            {"events": [e.to_dict() for e in self.events]},
            indent=indent,
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, text: str) -> EventLog:
        """Parse an :class:`EventLog` from a JSON string."""
        data = json.loads(text)
        return cls(events=[InputEvent.from_dict(e) for e in data.get("events", [])])

    def to_actions(self) -> list[Action]:
        """Map events onto schema actions for the render pipeline.

        Mapping:

        * ``move``  -> :attr:`~democreate.schema.ActionType.MOVE_MOUSE`
        * ``click`` -> :attr:`~democreate.schema.ActionType.CLICK`
        * ``key``   -> :attr:`~democreate.schema.ActionType.TYPE_CODE`

        Each action carries the event's ``t_ms`` as its ``timestamp_ms`` and the
        original payload as its ``params``. Unknown kinds are skipped.

        Returns:
            The mapped, time-stamped actions in order.
        """
        mapping = {
            "move": ActionType.MOVE_MOUSE,
            "click": ActionType.CLICK,
            "key": ActionType.TYPE_CODE,
        }
        actions: list[Action] = []
        for event in self.events:
            action_type = mapping.get(event.kind)
            if action_type is None:
                logger.debug("skipping unknown input event kind: %s", event.kind)
                continue
            actions.append(
                Action(
                    type=action_type,
                    params=dict(event.payload),
                    timestamp_ms=event.t_ms,
                )
            )
        return actions


def record_session(
    duration_s: float = 5.0, *, out_path: Path | str | None = None
) -> EventLog:
    """Record a live mouse/keyboard session (extra: ``replay``).

    Args:
        duration_s: How long to record, in seconds.
        out_path: Optional path to write the resulting :class:`EventLog` JSON.

    Returns:
        The recorded :class:`EventLog`.

    Raises:
        BackendUnavailableError: If ``pynput`` is not installed.
    """
    if not _have("pynput"):
        raise BackendUnavailableError("pynput", extra="replay")
    return _record_session_impl(duration_s, out_path)  # pragma: no cover - requires a live desktop


def _record_session_impl(  # pragma: no cover - requires a live desktop
    duration_s: float, out_path: Path | str | None
) -> EventLog:
    import time

    from pynput import keyboard, mouse

    log = EventLog()
    start = time.perf_counter()

    def _ms() -> int:
        return int((time.perf_counter() - start) * 1000)

    def on_move(x: int, y: int) -> None:
        log.events.append(InputEvent(_ms(), "move", {"x": x, "y": y}))

    def on_click(x: int, y: int, button: Any, pressed: bool) -> None:
        if pressed:
            log.events.append(
                InputEvent(_ms(), "click", {"x": x, "y": y, "button": str(button)})
            )

    def on_press(key: Any) -> None:
        log.events.append(InputEvent(_ms(), "key", {"key": str(key)}))

    mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
    key_listener = keyboard.Listener(on_press=on_press)
    mouse_listener.start()
    key_listener.start()
    time.sleep(duration_s)
    mouse_listener.stop()
    key_listener.stop()

    if out_path is not None:
        Path(out_path).write_text(log.to_json(), encoding="utf-8")
    return log


def replay_session(log: EventLog, *, speed: float = 1.0) -> None:
    """Replay a recorded session onto the live desktop (extra: ``replay``).

    Args:
        log: The event log to replay.
        speed: Playback speed multiplier (``2.0`` is twice as fast).

    Raises:
        BackendUnavailableError: If ``pyautogui`` is not installed.
    """
    if not _have("pyautogui"):
        raise BackendUnavailableError("pyautogui", extra="replay")
    _replay_session_impl(log, speed)  # pragma: no cover - requires a live desktop


def _replay_session_impl(log: EventLog, speed: float) -> None:  # pragma: no cover - requires a live desktop
    import time

    import pyautogui

    last_ms = 0
    for event in log.events:
        delay = max(0.0, (event.t_ms - last_ms) / 1000.0 / max(speed, 1e-6))
        time.sleep(delay)
        last_ms = event.t_ms
        if event.kind == "move":
            pyautogui.moveTo(event.payload.get("x", 0), event.payload.get("y", 0))
        elif event.kind == "click":
            pyautogui.click(event.payload.get("x", 0), event.payload.get("y", 0))
        elif event.kind == "key":
            key = str(event.payload.get("key", "")).strip("'")
            if key:
                pyautogui.press(key)
