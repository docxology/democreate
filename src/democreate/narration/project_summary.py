"""Project-summary script generation: a repo's facts become a narrated ``Demo``.

This is the *describing* generator. Where
:func:`democreate.narration.script.generate_codebase_demo` enumerates one scene
per module with boilerplate narration, this module builds a tightly-paced,
bounded **summary** that actually explains a piece of software — the same
seven-beat structure DemoCreate uses on itself, generalized to read its content
from real repository facts:

1. a **title** card (project name + one-line tagline),
2. a **what-it-is** bullet slide (derived from the real README),
3. an **architecture** slide (optional generated diagram background),
4. a **by-the-numbers** stat card (modules, lines, classes, functions),
5. one **code** scene per key module (real source excerpt, narrated from the
   module's *real* docstring),
6. a **how-to-run** terminal scene, and
7. an **outro** card.

The insight (first-principles): description is *selection + extraction*, not
enumeration. We pick the few load-bearing modules and narrate them with prose the
authors already wrote (docstrings, README) — so the default needs no model, no
network, and no clock: identical :class:`ProjectFacts` produce a byte-identical
:class:`~democreate.schema.Demo`.

The facts are collected (with I/O) by :mod:`democreate.portfolio`; everything in
*this* module is pure and stdlib-only so it round-trips and tests deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .._logging import get_logger
from ..schema import Action, ActionType, Chunk, Demo, Scene, SceneKind

__all__ = [
    "KeyModule",
    "ProjectFacts",
    "generate_project_summary_demo",
]

logger = get_logger(__name__)


@dataclass
class KeyModule:
    """One load-bearing module selected for a code scene.

    Attributes:
        name: Logical module name (e.g. ``"pipeline"``).
        path: Display path shown as the editor tab (e.g. ``"src/pkg/pipeline.py"``).
        docstring: The module's real docstring (or ``None``); its first sentence
            becomes the scene narration.
        code_excerpt: A real, bounded source excerpt to type on screen.
        symbol_count: Functions + classes + methods, for ordering/labels.
    """

    name: str
    path: str
    docstring: str | None = None
    code_excerpt: str = ""
    symbol_count: int = 0


@dataclass
class ProjectFacts:
    """The structured, render-ready facts about one software project.

    This is a pure data carrier — no I/O. :func:`generate_project_summary_demo`
    turns it into a :class:`~democreate.schema.Demo`. It is populated by
    :func:`democreate.portfolio.collect_project_facts`.

    Attributes:
        name: Project name (its directory name).
        tagline: One-line description (the README's first real sentence).
        overview_bullets: Two-to-four value bullets pulled from the README.
        module_count: Number of Python modules summarized.
        loc: Total lines of code across summarized modules.
        class_count: Total top-level classes.
        function_count: Total top-level functions.
        top_packages: Ordered top-level package/dir names (for the diagram + stat).
        key_modules: The selected load-bearing modules (code scenes).
        run_command: A real command a viewer could run, with its sample output.
        language: Primary language label (``"Python"`` for the default walker).
        test_count: Number of test functions discovered (``0`` if none/unknown).
        dependencies: Top external libraries the project is built on (for a
            "built with" beat); empty when none are detectable.
    """

    name: str
    tagline: str = ""
    overview_bullets: list[str] = field(default_factory=list)
    module_count: int = 0
    loc: int = 0
    class_count: int = 0
    function_count: int = 0
    top_packages: list[str] = field(default_factory=list)
    key_modules: list[KeyModule] = field(default_factory=list)
    run_command: tuple[str, str] = ("", "")
    language: str = "Python"
    test_count: int = 0
    dependencies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-ready dict (for the portfolio index)."""
        return {
            "name": self.name,
            "tagline": self.tagline,
            "overview_bullets": list(self.overview_bullets),
            "module_count": self.module_count,
            "loc": self.loc,
            "class_count": self.class_count,
            "function_count": self.function_count,
            "top_packages": list(self.top_packages),
            "key_modules": [m.name for m in self.key_modules],
            "run_command": list(self.run_command),
            "language": self.language,
            "test_count": self.test_count,
            "dependencies": list(self.dependencies),
        }


def _first_sentence(text: str, *, limit: int = 220) -> str:
    """Return the first sentence of ``text``, bounded to ``limit`` characters."""
    clean = " ".join(text.split())
    if not clean:
        return ""
    for stop in (". ", "! ", "? "):
        idx = clean.find(stop)
        if 0 < idx < limit:
            return clean[: idx + 1].strip()
    return (clean[:limit].rstrip() + "…") if len(clean) > limit else clean


def _human_int(value: int) -> str:
    """Format an integer with thousands separators (e.g. ``12,345``)."""
    return f"{value:,}"


def _slide(
    scene_id: str,
    *,
    section: str,
    title: str,
    narration: str,
    subtitle: str = "",
    bullets: list[str] | None = None,
    stats: list[tuple[str, str]] | None = None,
    background_image: str | None = None,
    trigger: str | None = None,
) -> Scene:
    """Build a SLIDE scene (title card / bullets / stats / image background)."""
    scene = Scene(id=scene_id, title=title or section, kind=SceneKind.SLIDE)
    scene.context["section"] = section
    if subtitle:
        scene.context["subtitle"] = subtitle
    if bullets:
        scene.context["bullets"] = list(bullets)
    if stats:
        scene.context["stats"] = [list(s) for s in stats]
    actions: list[Action] = []
    if background_image is not None:
        scene.context["background_image"] = str(background_image)
        actions.append(
            Action(ActionType.OPEN_FILE, {"path": title or section}, trigger_word=trigger)
        )
    scene.chunks.append(Chunk(id=f"{scene_id}-c", text=narration, actions=actions))
    return scene


def _code_scene(
    scene_id: str, *, section: str, path: str, code: str, narration: str,
    trigger: str | None = None,
) -> Scene:
    """Build a CODEBASE scene whose real source types in character-by-character."""
    scene = Scene(id=scene_id, title=path, kind=SceneKind.CODEBASE)
    scene.context["section"] = section
    scene.chunks.append(
        Chunk(
            id=f"{scene_id}-c",
            text=narration,
            actions=[
                Action(
                    ActionType.CREATE_FILE,
                    {"path": path, "code": code},
                    trigger_word=trigger,
                )
            ],
        )
    )
    return scene


def _terminal_scene(
    scene_id: str, *, section: str, command: str, output: str, narration: str,
    trigger: str | None = None,
) -> Scene:
    """Build a TERMINAL scene running one real command with sample output."""
    scene = Scene(id=scene_id, title="terminal", kind=SceneKind.TERMINAL)
    scene.context["section"] = section
    scene.chunks.append(
        Chunk(
            id=f"{scene_id}-c",
            text=narration,
            actions=[
                Action(
                    ActionType.RUN_COMMAND,
                    {"command": command, "output": output},
                    trigger_word=trigger,
                )
            ],
        )
    )
    return scene


# Varied openers so consecutive code scenes don't all begin "Take X." — picked by
# scene index for deterministic, non-repetitive narration.
_MODULE_OPENERS = ("Take", "Next,", "And", "Then", "Consider")


def _module_narration(module: KeyModule, index: int = 0) -> str:
    """Narrate a key module from its *real* docstring, never a constant.

    The opener varies by ``index`` so a run of code scenes reads naturally. Falls
    back to a factual, module-specific line (name + symbol count) when the module
    has no docstring — still specific, never the generic "handles one focused job".

    Args:
        module: The selected module.
        index: 0-based position among the code scenes (drives opener variety).
    """
    opener = _MODULE_OPENERS[index % len(_MODULE_OPENERS)]
    summary = _first_sentence(module.docstring) if module.docstring else ""
    if summary:
        return f"{opener} {module.name}. {summary}"
    plural = "symbol" if module.symbol_count == 1 else "symbols"
    return (
        f"{opener} {module.name} — {module.symbol_count} {plural} of this project's "
        "own code, shown here verbatim."
    )


def generate_project_summary_demo(
    facts: ProjectFacts,
    *,
    title: str | None = None,
    architecture_image: str | None = None,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    voice: str = "default",
    max_modules: int = 3,
) -> Demo:
    """Build a narrated project-summary :class:`Demo` from collected facts.

    Pure and deterministic: identical ``facts`` (and arguments) produce a
    byte-identical demo. No I/O, no clock, no RNG.

    Args:
        facts: The collected :class:`ProjectFacts` for one project.
        title: Demo title; defaults to ``"<name> — a tour"``.
        architecture_image: Path to a pre-rendered architecture PNG to use as the
            architecture slide's full-frame background (written by the orchestrator
            before this call). ``None`` falls back to a text architecture slide.
        width / height / fps: Output geometry passed onto the demo.
        voice: Default narration voice id.
        max_modules: Upper bound on key-module code scenes (selection, not
            enumeration — a 145-module repo still yields a bounded demo).

    Returns:
        A populated, valid :class:`Demo`.

    Raises:
        ValueError: If ``facts.name`` is empty.
    """
    name = facts.name.strip()
    if not name:
        raise ValueError("facts.name must be non-empty")

    demo_title = (title or f"{name} — a tour").strip()
    tagline = facts.tagline or f"A {facts.language} project."
    scenes: list[Scene] = []

    # 1 — Title card
    scenes.append(
        _slide(
            "title",
            section=name,
            title=name,
            subtitle=_first_sentence(tagline, limit=90),
            narration=(
                f"This is {name}. {tagline} Here is a one-look tour of what it is "
                "and how it is built."
            ),
            trigger="tour",
        )
    )

    # 2 — What it is (bullets from the real README)
    bullets = [b for b in facts.overview_bullets if b.strip()][:4]
    if bullets:
        scenes.append(
            _slide(
                "what",
                section="What it is",
                title=f"What {name} is",
                narration=(
                    "From its own README, here is what this project is and what "
                    "it gives you."
                ),
                bullets=bullets,
                trigger="README",
            )
        )

    # 3 — Architecture (diagram background if available, else a text slide)
    pkgs = facts.top_packages[:8]
    if architecture_image is not None:
        scenes.append(
            _slide(
                "arch",
                section="Architecture",
                title=f"{name} — architecture",
                narration=(
                    f"Structurally, {name} is organized into "
                    f"{len(facts.top_packages)} top-level areas. Here is the map of "
                    "its real packages."
                ),
                background_image=architecture_image,
                trigger="map",
            )
        )
    elif pkgs:
        scenes.append(
            _slide(
                "arch",
                section="Architecture",
                title=f"{name} — architecture",
                narration=(
                    f"Structurally, {name} groups its modules into these top-level "
                    "areas, each a focused responsibility."
                ),
                bullets=[f"{p}/" for p in pkgs],
                trigger="areas",
            )
        )

    # 4 — By the numbers (real stats). Show the test count when we found one;
    # otherwise fall back to the package count so the card always has five cells.
    has_tests = facts.test_count > 0
    fifth = (
        (_human_int(facts.test_count), "tests")
        if has_tests
        else (str(len(facts.top_packages)), "packages")
    )
    tests_clause = (
        f", and {_human_int(facts.test_count)} tests" if has_tests else ""
    )
    scenes.append(
        _slide(
            "numbers",
            section="By the numbers",
            title=f"{name} by the numbers",
            narration=(
                "And it is real. "
                f"{_human_int(facts.module_count)} modules, "
                f"{_human_int(facts.loc)} lines of code, "
                f"{_human_int(facts.class_count)} classes and "
                f"{_human_int(facts.function_count)} top-level functions"
                f"{tests_clause}."
            ),
            stats=[
                (_human_int(facts.module_count), "modules"),
                (_human_int(facts.loc), "lines"),
                (_human_int(facts.class_count), "classes"),
                (_human_int(facts.function_count), "functions"),
                fifth,
            ],
            trigger="real",
        )
    )

    # 4b — Built with (top external dependencies), when detectable.
    deps = [d for d in facts.dependencies if d.strip()][:6]
    if deps:
        scenes.append(
            _slide(
                "deps",
                section="Built with",
                title=f"{name} is built with",
                narration=(
                    "It does not reinvent the wheel — here are the main libraries "
                    "it builds on."
                ),
                bullets=deps,
                trigger="libraries",
            )
        )

    # 5 — Key modules (real code, narrated from real docstrings)
    for index, module in enumerate(facts.key_modules[:max_modules]):
        if not module.code_excerpt.strip():
            continue
        scenes.append(
            _code_scene(
                f"mod-{index + 1}",
                section=module.name,
                path=module.path,
                code=module.code_excerpt,
                narration=_module_narration(module, index),
                trigger="code",
            )
        )

    # 6 — How to run it (a real command)
    command, output = facts.run_command
    if command:
        scenes.append(
            _terminal_scene(
                "run",
                section="Run it",
                command=command,
                output=output or "",
                narration=(
                    "And you can run it yourself. One command exercises the project "
                    "end to end."
                ),
                trigger="run",
            )
        )

    # 7 — Outro
    scenes.append(
        _slide(
            "outro",
            section="Summary",
            title=name,
            subtitle=_first_sentence(tagline, limit=90),
            narration=(
                f"That is {name}: {_first_sentence(tagline, limit=120)} "
                "This entire summary was compiled from the repository itself."
            ),
            trigger="summary",
        )
    )

    demo = Demo(
        title=demo_title,
        scenes=scenes,
        width=width,
        height=height,
        fps=fps,
        voice=voice,
        metadata={
            "project": name,
            "generator": "project_summary",
            "language": facts.language,
        },
    )
    logger.info(
        "project-summary generator built demo %r with %d scene(s) for %r",
        demo_title,
        len(demo.scenes),
        name,
    )
    return demo
