"""Tests for the pure project-summary generator.

No mocks: the generator is a pure function of :class:`ProjectFacts`, so these
assert structure, determinism, README-derived content, real-docstring narration,
the bounded selection, and graceful degradation — all with plain data.
"""

from __future__ import annotations

from democreate.narration.project_summary import (
    KeyModule,
    ProjectFacts,
    generate_project_summary_demo,
)
from democreate.schema import ActionType, SceneKind


def _facts(**overrides) -> ProjectFacts:
    """A representative, fully-populated facts object."""
    base = ProjectFacts(
        name="acme",
        tagline="Acme is a deterministic widget compiler.",
        overview_bullets=[
            "Compiles widget specs into binaries with zero network.",
            "Every backend has a pure-Python default.",
        ],
        module_count=12,
        loc=3456,
        class_count=8,
        function_count=40,
        top_packages=["core", "cli", "io"],
        key_modules=[
            KeyModule(
                name="compiler",
                path="src/acme/compiler.py",
                docstring="The compiler turns a spec into a binary. It is pure.",
                code_excerpt="class Compiler:\n    def run(self) -> bytes:\n        return b''",
                symbol_count=9,
            ),
            KeyModule(
                name="registry",
                path="src/acme/registry.py",
                docstring=None,
                code_excerpt="def register(name):\n    REGISTRY[name] = True",
                symbol_count=3,
            ),
        ],
        run_command=("uv run pytest -q", "all tests pass"),
    )
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def test_generator_produces_valid_demo() -> None:
    demo = generate_project_summary_demo(_facts())
    assert demo.validate() == []
    assert demo.metadata["project"] == "acme"


def test_first_scene_is_title_slide() -> None:
    demo = generate_project_summary_demo(_facts())
    first = demo.scenes[0]
    assert first.kind == SceneKind.SLIDE
    assert first.title == "acme"
    assert first.context.get("subtitle")


def test_bullets_come_from_readme_not_constant() -> None:
    facts = _facts()
    demo = generate_project_summary_demo(facts)
    what = next(s for s in demo.scenes if s.id == "what")
    assert what.context["bullets"] == facts.overview_bullets[:4]


def test_stat_card_has_real_numbers() -> None:
    demo = generate_project_summary_demo(_facts())
    numbers = next(s for s in demo.scenes if s.id == "numbers")
    stats = {label: value for value, label in numbers.context["stats"]}
    assert stats["modules"] == "12"
    assert stats["lines"] == "3,456"
    assert stats["classes"] == "8"


def test_code_scene_shows_real_source_and_docstring_narration() -> None:
    demo = generate_project_summary_demo(_facts())
    code_scenes = [s for s in demo.scenes if s.kind == SceneKind.CODEBASE]
    assert code_scenes, "expected at least one code scene"
    first = code_scenes[0]
    action = first.chunks[0].actions[0]
    assert action.type == ActionType.CREATE_FILE
    assert action.params["code"].startswith("class Compiler")
    # narration uses the real docstring first sentence
    assert "turns a spec into a binary" in first.chunks[0].text


def test_module_without_docstring_is_still_specific() -> None:
    demo = generate_project_summary_demo(_facts())
    reg = next(s for s in demo.scenes if s.title == "src/acme/registry.py")
    text = reg.chunks[0].text
    assert "registry" in text
    assert "handles one focused job" not in text  # anti-criterion


def test_anti_generic_boilerplate_anywhere() -> None:
    demo = generate_project_summary_demo(_facts())
    for chunk in demo.iter_chunks():
        assert "handles one focused job" not in chunk.text


def test_terminal_scene_has_real_command() -> None:
    demo = generate_project_summary_demo(_facts())
    term = next(s for s in demo.scenes if s.kind == SceneKind.TERMINAL)
    assert term.chunks[0].actions[0].params["command"] == "uv run pytest -q"


def test_has_outro() -> None:
    demo = generate_project_summary_demo(_facts())
    assert demo.scenes[-1].id == "outro"


def test_determinism_byte_identical() -> None:
    a = generate_project_summary_demo(_facts())
    b = generate_project_summary_demo(_facts())
    assert a.to_json() == b.to_json()


def test_max_modules_bounds_code_scenes() -> None:
    many = [
        KeyModule(
            name=f"m{i}",
            path=f"src/m{i}.py",
            docstring=f"Module {i} does thing {i}.",
            code_excerpt=f"def f{i}():\n    return {i}",
            symbol_count=i,
        )
        for i in range(20)
    ]
    demo = generate_project_summary_demo(_facts(key_modules=many), max_modules=3)
    code_scenes = [s for s in demo.scenes if s.kind == SceneKind.CODEBASE]
    assert len(code_scenes) == 3


def test_no_readme_degrades_gracefully() -> None:
    facts = _facts(overview_bullets=[], tagline="")
    demo = generate_project_summary_demo(facts)
    assert demo.validate() == []
    assert all(s.id != "what" for s in demo.scenes)  # no bullet slide without README


def test_no_python_modules_still_valid() -> None:
    facts = ProjectFacts(name="docsonly", tagline="A docs-only repo.", language="mixed")
    demo = generate_project_summary_demo(facts)
    assert demo.validate() == []
    # title, numbers, outro at minimum
    ids = {s.id for s in demo.scenes}
    assert {"title", "numbers", "outro"} <= ids


def test_stat_card_shows_tests_when_present() -> None:
    demo = generate_project_summary_demo(_facts(test_count=42))
    numbers = next(s for s in demo.scenes if s.id == "numbers")
    stats = {label: value for value, label in numbers.context["stats"]}
    assert stats["tests"] == "42"
    assert "42 tests" in numbers.chunks[0].text


def test_no_tests_falls_back_to_packages_stat() -> None:
    demo = generate_project_summary_demo(_facts(test_count=0))
    numbers = next(s for s in demo.scenes if s.id == "numbers")
    labels = {label for _v, label in numbers.context["stats"]}
    assert "packages" in labels and "tests" not in labels


def test_dependencies_beat_present() -> None:
    demo = generate_project_summary_demo(_facts(dependencies=["numpy", "pandas"]))
    deps = next(s for s in demo.scenes if s.id == "deps")
    assert deps.context["bullets"] == ["numpy", "pandas"]


def test_no_dependencies_no_beat() -> None:
    demo = generate_project_summary_demo(_facts(dependencies=[]))
    assert all(s.id != "deps" for s in demo.scenes)


def test_module_narration_openers_vary() -> None:
    from democreate.narration.project_summary import _module_narration

    module = KeyModule(
        name="engine", path="x.py", docstring="Drives the loop.", symbol_count=4
    )
    first = _module_narration(module, 0)
    second = _module_narration(module, 1)
    assert first != second
    assert "engine" in first and "engine" in second
    assert "Drives the loop." in first


def test_code_scene_narrations_are_distinct() -> None:
    many = [
        KeyModule(
            name=f"m{i}", path=f"m{i}.py", docstring=f"Module {i} does X.",
            code_excerpt=f"def f{i}():\n    return {i}", symbol_count=10 - i,
        )
        for i in range(3)
    ]
    demo = generate_project_summary_demo(_facts(key_modules=many), max_modules=3)
    code_texts = [
        s.chunks[0].text for s in demo.scenes if s.kind == SceneKind.CODEBASE
    ]
    assert len(code_texts) == 3
    assert len(set(code_texts)) == 3  # no two code scenes read identically


def test_empty_name_rejected() -> None:
    import pytest

    with pytest.raises(ValueError):
        generate_project_summary_demo(ProjectFacts(name="  "))
