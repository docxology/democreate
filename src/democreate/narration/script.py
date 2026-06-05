"""Script generation: turning structured context into a declarative Demo.

A :class:`ScriptGenerator` builds a :class:`~democreate.schema.Demo` from some
input context. The default :class:`TemplateScriptGenerator` is deterministic and
needs only the standard library: it maps a plain context dict into scenes,
chunks, and actions with no model in the loop.

:func:`generate_codebase_demo` is a convenience that walks a list of module
summaries (duck-typed — works with either
``democreate.codebase.walker.ModuleSummary`` or plain dicts) and narrates each
module's functions and classes with ``OPEN_FILE`` and ``HIGHLIGHT_LINES``
actions. It deliberately does *not* import the codebase subsystem, so there is no
build-order coupling between the two.

The optional :class:`LLMScriptGenerator` wraps an LLM provider; it never touches
the network in tests and raises :class:`~democreate.errors.BackendUnavailableError`
when no provider is configured.
"""

from __future__ import annotations

from typing import Any

from .._logging import get_logger
from ..errors import BackendUnavailableError
from ..schema import Action, ActionType, Chunk, Demo, Scene, SceneKind

__all__ = [
    "ScriptGenerator",
    "TemplateScriptGenerator",
    "LLMScriptGenerator",
    "generate_codebase_demo",
]

logger = get_logger(__name__)

# Map a context step's "kind" string to a SceneKind, defaulting to CODEBASE.
_KIND_ALIASES: dict[str, SceneKind] = {
    "codebase": SceneKind.CODEBASE,
    "code": SceneKind.CODEBASE,
    "website": SceneKind.WEBSITE,
    "web": SceneKind.WEBSITE,
    "terminal": SceneKind.TERMINAL,
    "shell": SceneKind.TERMINAL,
    "slide": SceneKind.SLIDE,
}


def _coerce_scene_kind(value: Any) -> SceneKind:
    """Coerce a free-form kind value into a :class:`SceneKind`.

    Args:
        value: A :class:`SceneKind`, its string value, or a friendly alias.

    Returns:
        The resolved :class:`SceneKind`, defaulting to ``CODEBASE``.
    """
    if isinstance(value, SceneKind):
        return value
    if value is None:
        return SceneKind.CODEBASE
    key = str(value).lower()
    if key in _KIND_ALIASES:
        return _KIND_ALIASES[key]
    try:
        return SceneKind(key)
    except ValueError:
        return SceneKind.CODEBASE


def _build_action(spec: Any) -> Action:
    """Build an :class:`Action` from a dict or an existing :class:`Action`.

    Args:
        spec: Either an :class:`Action`, or a dict with at least ``type`` and
            optional ``params``/``trigger_word``/``duration_ms`` keys.

    Returns:
        A constructed :class:`Action`.

    Raises:
        ValueError: If a dict spec lacks a ``type`` key.
    """
    if isinstance(spec, Action):
        return spec
    if "type" not in spec:
        raise ValueError(f"action spec missing 'type': {spec!r}")
    return Action(
        type=spec["type"],
        params=dict(spec.get("params", {})),
        trigger_word=spec.get("trigger_word"),
        duration_ms=spec.get("duration_ms"),
    )


class ScriptGenerator:
    """Abstract base for building a :class:`Demo` from input context."""

    name: str = "abstract"

    def generate(self, context: dict[str, Any]) -> Demo:
        """Build and return a :class:`Demo` from ``context``.

        Args:
            context: Generator-specific input.

        Returns:
            A fully-formed :class:`Demo`.
        """
        raise NotImplementedError


class TemplateScriptGenerator(ScriptGenerator):
    """Deterministic generator that maps a context dict to a :class:`Demo`.

    Context shape::

        {
            "title": "My Tour",
            "width": 1920,            # optional
            "height": 1080,           # optional
            "voice": "default",       # optional
            "steps": [
                {
                    "narration": "We open the entry point.",
                    "kind": "codebase",          # optional, defaults codebase
                    "title": "Intro",            # optional scene title
                    "id": "intro",               # optional, auto-generated
                    "actions": [
                        {"type": "open_file", "params": {"path": "main.py"},
                         "trigger_word": "open"},
                    ],
                },
            ],
        }

    Each step becomes one :class:`Scene` containing a single :class:`Chunk` (the
    narration) plus that step's actions. This one-scene-per-step mapping keeps
    chunk ids stable and predictable for downstream sync and captioning.
    """

    name = "template"

    def generate(self, context: dict[str, Any]) -> Demo:
        """Build a :class:`Demo` from the template context dict.

        Args:
            context: A dict with ``title`` and a list of ``steps`` (see class
                docstring).

        Returns:
            A populated :class:`Demo`.

        Raises:
            ValueError: If ``title`` is missing or empty.
        """
        title = str(context.get("title", "")).strip()
        if not title:
            raise ValueError("context must include a non-empty 'title'")

        demo = Demo(
            title=title,
            width=int(context.get("width", 1920)),
            height=int(context.get("height", 1080)),
            voice=str(context.get("voice", "default")),
        )

        steps = context.get("steps", [])
        for index, step in enumerate(steps):
            scene_id = str(step.get("id", f"scene-{index + 1}"))
            scene = Scene(
                id=scene_id,
                title=str(step.get("title", f"Step {index + 1}")),
                kind=_coerce_scene_kind(step.get("kind")),
                context=dict(step.get("context", {})),
            )
            actions = [_build_action(a) for a in step.get("actions", [])]
            scene.chunks.append(
                Chunk(
                    id=f"{scene_id}-c1",
                    text=str(step.get("narration", "")),
                    actions=actions,
                    voice=step.get("voice"),
                )
            )
            demo.scenes.append(scene)

        logger.info(
            "template generator built demo %r with %d scene(s)",
            title,
            len(demo.scenes),
        )
        return demo


def _as_list(value: Any) -> list[Any]:
    """Return ``value`` as a list (treating ``None`` as empty)."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _summary_field(summary: Any, name: str, default: Any) -> Any:
    """Duck-typed accessor for a summary attribute or dict key.

    Args:
        summary: A module-summary object or a plain dict.
        name: The field name to read.
        default: Value returned when the field is absent.

    Returns:
        The field value, or ``default``.
    """
    if isinstance(summary, dict):
        return summary.get(name, default)
    return getattr(summary, name, default)


def _callable_name(item: Any) -> str:
    """Extract a display name from a function/class summary (duck-typed).

    Args:
        item: A string, an object with ``.name``, or a dict with ``"name"``.

    Returns:
        A best-effort human name.
    """
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return str(item.get("name", item))
    return str(getattr(item, "name", item))


def generate_codebase_demo(summaries: list[Any], *, title: str) -> Demo:
    """Build a codebase-tour :class:`Demo` from a list of module summaries.

    Each summary is duck-typed: it may expose ``.name``, ``.functions``, and
    ``.classes`` as attributes (e.g. ``ModuleSummary``) or as dict keys. For each
    module a scene is produced that opens the file and narrates its functions and
    classes, emitting an ``OPEN_FILE`` action plus ``HIGHLIGHT_LINES`` actions for
    each function/class found.

    Args:
        summaries: Module summaries (objects or dicts) to narrate.
        title: Title for the generated demo.

    Returns:
        A populated :class:`Demo`, one scene per module.

    Raises:
        ValueError: If ``title`` is empty.
    """
    clean_title = title.strip()
    if not clean_title:
        raise ValueError("title must be non-empty")

    demo = Demo(title=clean_title)

    for index, summary in enumerate(summaries):
        name = str(_summary_field(summary, "name", f"module_{index + 1}"))
        path = str(_summary_field(summary, "path", name))
        functions = _as_list(_summary_field(summary, "functions", []))
        classes = _as_list(_summary_field(summary, "classes", []))

        scene_id = f"mod-{index + 1}"
        scene = Scene(
            id=scene_id,
            title=name,
            kind=SceneKind.CODEBASE,
            context={"module": name, "path": path},
        )

        fn_names = [_callable_name(f) for f in functions]
        cls_names = [_callable_name(c) for c in classes]

        # Opening chunk: open the file.
        open_text = f"Let's open {name} and see what it provides."
        open_chunk = Chunk(
            id=f"{scene_id}-open",
            text=open_text,
            actions=[
                Action(
                    ActionType.OPEN_FILE,
                    {"path": path},
                    trigger_word="open",
                )
            ],
        )
        scene.chunks.append(open_chunk)

        # Narrate classes, then functions, each with a highlight action.
        line_cursor = 1
        for cls_name in cls_names:
            scene.chunks.append(
                Chunk(
                    id=f"{scene_id}-cls-{cls_name}",
                    text=f"The class {cls_name} groups related behavior together.",
                    actions=[
                        Action(
                            ActionType.HIGHLIGHT_LINES,
                            {"lines": [line_cursor]},
                            trigger_word="class",
                        )
                    ],
                )
            )
            line_cursor += 1

        for fn_name in fn_names:
            scene.chunks.append(
                Chunk(
                    id=f"{scene_id}-fn-{fn_name}",
                    text=f"The function {fn_name} handles one focused job.",
                    actions=[
                        Action(
                            ActionType.HIGHLIGHT_LINES,
                            {"lines": [line_cursor]},
                            trigger_word="function",
                        )
                    ],
                )
            )
            line_cursor += 1

        # If a module is empty, still give it a closing narration chunk.
        if not fn_names and not cls_names:
            scene.chunks.append(
                Chunk(
                    id=f"{scene_id}-empty",
                    text=f"The module {name} is small with no top-level symbols.",
                )
            )

        demo.scenes.append(scene)

    logger.info(
        "codebase generator built demo %r from %d module(s)",
        clean_title,
        len(summaries),
    )
    return demo


class LLMScriptGenerator(ScriptGenerator):
    """LLM-backed script generator (optional; never used in tests).

    This is a guarded provider abstraction. With no provider configured it raises
    :class:`~democreate.errors.BackendUnavailableError` from :meth:`generate`,
    keeping the package import-safe and offline-testable.

    Args:
        provider: Provider name (e.g. ``"anthropic"``, ``"openai"``). ``None``
            means unconfigured.
        model: Model identifier to request from the provider.
    """

    name = "llm"

    def __init__(
        self, *, provider: str | None = None, model: str | None = None
    ) -> None:
        self.provider = provider
        self.model = model

    def generate(self, context: dict[str, Any]) -> Demo:
        """Generate a demo via the configured LLM provider.

        Args:
            context: Provider-specific prompt context.

        Returns:
            A generated :class:`Demo` (only reachable with a real provider).

        Raises:
            BackendUnavailableError: If no provider is configured.
        """
        if not self.provider:
            raise BackendUnavailableError("llm", extra="llm")
        return self._generate_with_provider(context)  # pragma: no cover

    def _generate_with_provider(  # pragma: no cover - requires a provider
        self, context: dict[str, Any]
    ) -> Demo:
        """Call the real provider (only runs when one is configured)."""
        raise BackendUnavailableError("llm", extra="llm")
