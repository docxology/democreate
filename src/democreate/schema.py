"""Declarative demo schema — the deterministic spine of DemoCreate.

A :class:`Demo` is the single source of truth for an audio-visual software
walkthrough. It merges two prior-art ideas into one artifact:

* **CodeVideo's event-sourced model** — content is an ordered stream of typed
  :class:`Action` objects mutating a virtual environment (editor, terminal,
  browser, camera). The same stream re-renders to any output format.
* **VSpeak's chunk/trigger model** — narration is grouped into :class:`Chunk`
  units, and each action carries an optional ``trigger_word`` that anchors it to
  a spoken word so the sync engine can assign a millisecond timestamp from real
  TTS audio rather than guessing timing in advance.

Everything here is pure Python: no I/O, no heavy dependencies. The schema
round-trips losslessly through ``dict``/JSON/YAML and validates its own
structural invariants. Heavy backends (TTS, capture, render) consume and produce
these objects but never define them.

Example
-------
>>> demo = Demo(title="Tour")
>>> scene = Scene(id="s1", title="Intro", kind=SceneKind.CODEBASE)
>>> scene.chunks.append(
...     Chunk(id="c1", text="Here we open main.",
...           actions=[Action(ActionType.OPEN_FILE, {"path": "main.py"},
...                           trigger_word="open")])
... )
>>> demo.scenes.append(scene)
>>> demo.validate()
[]
>>> Demo.from_dict(demo.to_dict()) == demo
True
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

__all__ = [
    "ActionType",
    "SceneKind",
    "Action",
    "Chunk",
    "Scene",
    "WordTimestamp",
    "Demo",
    "SCHEMA_VERSION",
]

SCHEMA_VERSION = "1.0"

# Words-per-minute used to estimate narration duration when no real audio exists
# yet. 150 wpm is a comfortable technical-narration pace.
DEFAULT_WPM = 150


class ActionType(str, Enum):
    """Every primitive change a demo can express against the virtual environment.

    The string values are the on-disk representation; they are stable and must
    not be renamed without a schema-version bump.
    """

    # --- editor -----------------------------------------------------------
    OPEN_FILE = "open_file"
    CREATE_FILE = "create_file"
    TYPE_CODE = "type_code"
    HIGHLIGHT_LINES = "highlight_lines"
    CLOSE_FILE = "close_file"
    # --- terminal ---------------------------------------------------------
    RUN_COMMAND = "run_command"
    PRINT_OUTPUT = "print_output"
    # --- browser ----------------------------------------------------------
    NAVIGATE = "navigate"
    CLICK = "click"
    SCROLL = "scroll"
    FILL = "fill"
    # --- mouse / camera ---------------------------------------------------
    MOVE_MOUSE = "move_mouse"
    ZOOM = "zoom"
    PAN = "pan"
    # --- narration / timing ----------------------------------------------
    SPEAK = "speak"
    WAIT = "wait"


class SceneKind(str, Enum):
    """The capture/render strategy a scene implies."""

    CODEBASE = "codebase"
    WEBSITE = "website"
    TERMINAL = "terminal"
    SLIDE = "slide"


def _coerce_enum(enum_cls: type[Enum], value: Any) -> Any:
    """Return ``value`` as a member of ``enum_cls`` (accepts the member or its value)."""
    if isinstance(value, enum_cls):
        return value
    return enum_cls(value)


@dataclass
class Action:
    """One typed event mutating the virtual environment.

    Attributes:
        type: The kind of action (see :class:`ActionType`).
        params: Action-specific payload (e.g. ``{"path": "main.py"}``). Kept as a
            free-form dict so new actions need no schema change downstream.
        trigger_word: A word in the parent chunk's narration that this action is
            anchored to. The sync engine matches it against real word timestamps.
        timestamp_ms: Absolute time (ms from demo start) the action fires. ``None``
            until the sync engine fills it in.
        duration_ms: How long the action takes to play out (e.g. typing, a zoom).
    """

    type: ActionType
    params: dict[str, Any] = field(default_factory=dict)
    trigger_word: str | None = None
    timestamp_ms: int | None = None
    duration_ms: int | None = None

    def __post_init__(self) -> None:
        self.type = _coerce_enum(ActionType, self.type)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-ready dict (omitting unset optional fields)."""
        out: dict[str, Any] = {"type": self.type.value, "params": dict(self.params)}
        if self.trigger_word is not None:
            out["trigger_word"] = self.trigger_word
        if self.timestamp_ms is not None:
            out["timestamp_ms"] = self.timestamp_ms
        if self.duration_ms is not None:
            out["duration_ms"] = self.duration_ms
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Action:
        """Inverse of :meth:`to_dict`."""
        def _int_or_none(v):
            return int(v) if v is not None else None

        return cls(
            type=_coerce_enum(ActionType, data["type"]),
            params=dict(data.get("params", {})),
            trigger_word=data.get("trigger_word"),
            timestamp_ms=_int_or_none(data.get("timestamp_ms")),
            duration_ms=_int_or_none(data.get("duration_ms")),
        )


@dataclass
class Chunk:
    """A narration unit and the actions it triggers (VSpeak model).

    Attributes:
        id: Stable identifier, unique within the demo.
        text: The narration text spoken for this chunk.
        actions: Actions anchored to words in ``text``.
        voice: Optional per-chunk voice override.
        audio_path: Path to rendered TTS audio, filled by the TTS backend.
        start_ms: Absolute start time of this chunk's audio, filled by sync.
    """

    id: str
    text: str = ""
    actions: list[Action] = field(default_factory=list)
    voice: str | None = None
    audio_path: str | None = None
    start_ms: int | None = None

    def word_count(self) -> int:
        """Number of whitespace-delimited words in the narration."""
        return len(self.text.split())

    def estimated_duration_ms(self, wpm: int = DEFAULT_WPM) -> int:
        """Estimate narration duration from word count at ``wpm`` words/minute.

        Used as a deterministic fallback before real TTS audio exists. A chunk
        with no words still reserves a minimum 300 ms beat.
        """
        words = self.word_count()
        if words == 0:
            return 300
        return int(round(words / wpm * 60_000))

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "id": self.id,
            "text": self.text,
            "actions": [a.to_dict() for a in self.actions],
        }
        if self.voice is not None:
            out["voice"] = self.voice
        if self.audio_path is not None:
            out["audio_path"] = self.audio_path
        if self.start_ms is not None:
            out["start_ms"] = self.start_ms
        return out

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        return cls(
            id=data["id"],
            text=data.get("text", ""),
            actions=[Action.from_dict(a) for a in data.get("actions", [])],
            voice=data.get("voice"),
            audio_path=data.get("audio_path"),
            start_ms=data.get("start_ms"),
        )


@dataclass
class Scene:
    """A logical chapter of the demo with a single capture strategy.

    Attributes:
        id: Stable identifier, unique within the demo.
        title: Human-readable chapter title (used for navigation/chapters).
        kind: The capture/render strategy (see :class:`SceneKind`).
        chunks: Ordered narration+action units.
        context: Free-form scene context (e.g. a file tree snapshot, base URL).
    """

    id: str
    title: str = ""
    kind: SceneKind = SceneKind.CODEBASE
    chunks: list[Chunk] = field(default_factory=list)
    context: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.kind = _coerce_enum(SceneKind, self.kind)

    def estimated_duration_ms(self, wpm: int = DEFAULT_WPM) -> int:
        """Sum of chunk duration estimates."""
        return sum(c.estimated_duration_ms(wpm) for c in self.chunks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind.value,
            "chunks": [c.to_dict() for c in self.chunks],
            "context": dict(self.context),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Scene:
        return cls(
            id=data["id"],
            title=data.get("title", ""),
            kind=_coerce_enum(SceneKind, data.get("kind", SceneKind.CODEBASE)),
            chunks=[Chunk.from_dict(c) for c in data.get("chunks", [])],
            context=dict(data.get("context", {})),
        )


@dataclass
class WordTimestamp:
    """A single word with millisecond start/end, produced by a transcriber."""

    word: str
    start_ms: int
    end_ms: int

    def to_dict(self) -> dict[str, Any]:
        return {"word": self.word, "start_ms": self.start_ms, "end_ms": self.end_ms}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WordTimestamp:
        return cls(
            word=data["word"], start_ms=data["start_ms"], end_ms=data["end_ms"]
        )


@dataclass
class Demo:
    """The top-level declarative artifact for a complete walkthrough.

    A ``Demo`` fully specifies the content; rendering is a pure function of it.
    Mutating-then-re-rendering is the supported edit workflow — never re-record.

    Attributes:
        title: Demo title (used in exports and metadata).
        scenes: Ordered scenes.
        width / height: Output frame dimensions in pixels.
        fps: Output frame rate.
        voice: Default voice id for narration.
        metadata: Free-form metadata (author, source repo, license, ...).
    """

    title: str
    scenes: list[Scene] = field(default_factory=list)
    width: int = 1920
    height: int = 1080
    fps: int = 30
    voice: str = "default"
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = SCHEMA_VERSION

    # -- iteration helpers -------------------------------------------------

    def iter_chunks(self) -> list[Chunk]:
        """Flat, ordered list of every chunk across all scenes."""
        return [c for scene in self.scenes for c in scene.chunks]

    def iter_actions(self) -> list[Action]:
        """Flat, ordered list of every action across all scenes/chunks."""
        return [a for c in self.iter_chunks() for a in c.actions]

    def estimated_duration_ms(self, wpm: int = DEFAULT_WPM) -> int:
        """Total estimated runtime from narration word counts."""
        return sum(s.estimated_duration_ms(wpm) for s in self.scenes)

    # -- validation --------------------------------------------------------

    def validate(self) -> list[str]:
        """Return a list of human-readable structural problems (empty == valid).

        Checks: non-empty title, unique scene ids, unique chunk ids, positive
        frame geometry and fps, and that every action references a known
        ``ActionType``. Does not raise — callers decide how strict to be.
        """
        errors: list[str] = []
        if not self.title.strip():
            errors.append("demo title must be non-empty")
        if self.width <= 0 or self.height <= 0:
            errors.append(f"frame geometry must be positive, got {self.width}x{self.height}")
        if self.fps <= 0:
            errors.append(f"fps must be positive, got {self.fps}")

        seen_scene_ids: set[str] = set()
        seen_chunk_ids: set[str] = set()
        for scene in self.scenes:
            if scene.id in seen_scene_ids:
                errors.append(f"duplicate scene id: {scene.id!r}")
            seen_scene_ids.add(scene.id)
            for chunk in scene.chunks:
                if chunk.id in seen_chunk_ids:
                    errors.append(f"duplicate chunk id: {chunk.id!r}")
                seen_chunk_ids.add(chunk.id)
                for action in chunk.actions:
                    if not isinstance(action.type, ActionType):
                        errors.append(
                            f"chunk {chunk.id!r} has action with invalid type "
                            f"{action.type!r}"
                        )
        return errors

    def is_valid(self) -> bool:
        """``True`` iff :meth:`validate` returns no problems."""
        return not self.validate()

    # -- serialization -----------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "title": self.title,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
            "voice": self.voice,
            "metadata": dict(self.metadata),
            "scenes": [s.to_dict() for s in self.scenes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Demo:
        return cls(
            title=data["title"],
            scenes=[Scene.from_dict(s) for s in data.get("scenes", [])],
            width=data.get("width", 1920),
            height=data.get("height", 1080),
            fps=data.get("fps", 30),
            voice=data.get("voice", "default"),
            metadata=dict(data.get("metadata", {})),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )

    def to_json(self, *, indent: int | None = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    @classmethod
    def from_json(cls, text: str) -> Demo:
        """Parse a :class:`Demo` from a JSON string."""
        return cls.from_dict(json.loads(text))

    def to_yaml(self) -> str:
        """Serialize to a YAML string. Requires PyYAML (a core dependency)."""
        import yaml  # local import keeps the module import-light

        return yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, text: str) -> Demo:
        """Parse a :class:`Demo` from a YAML string."""
        import yaml

        return cls.from_dict(yaml.safe_load(text))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Demo):
            return NotImplemented
        return self.to_dict() == other.to_dict()
