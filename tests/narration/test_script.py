"""Tests for script generation (template default, codebase helper, LLM guard)."""

from __future__ import annotations

import pytest

from democreate.errors import BackendUnavailableError
from democreate.narration.script import (
    LLMScriptGenerator,
    ScriptGenerator,
    TemplateScriptGenerator,
    generate_codebase_demo,
)
from democreate.schema import Action, ActionType, Demo, SceneKind

# --- TemplateScriptGenerator ----------------------------------------------


def test_template_builds_valid_demo() -> None:
    context = {
        "title": "My Tour",
        "steps": [
            {
                "narration": "We open the entry point.",
                "kind": "codebase",
                "title": "Intro",
                "actions": [
                    {
                        "type": "open_file",
                        "params": {"path": "main.py"},
                        "trigger_word": "open",
                    }
                ],
            },
            {
                "narration": "Now we run it.",
                "kind": "terminal",
                "actions": [{"type": "run_command", "params": {"command": "go"}}],
            },
        ],
    }
    demo = TemplateScriptGenerator().generate(context)
    assert isinstance(demo, Demo)
    assert demo.title == "My Tour"
    assert demo.validate() == []
    assert len(demo.scenes) == 2
    assert demo.scenes[0].kind == SceneKind.CODEBASE
    assert demo.scenes[1].kind == SceneKind.TERMINAL
    first_action = demo.scenes[0].chunks[0].actions[0]
    assert first_action.type == ActionType.OPEN_FILE
    assert first_action.trigger_word == "open"


def test_template_round_trips_through_dict() -> None:
    demo = TemplateScriptGenerator().generate(
        {"title": "RT", "steps": [{"narration": "hi"}]}
    )
    assert Demo.from_dict(demo.to_dict()) == demo


def test_template_missing_title_raises() -> None:
    with pytest.raises(ValueError):
        TemplateScriptGenerator().generate({"steps": []})
    with pytest.raises(ValueError):
        TemplateScriptGenerator().generate({"title": "   "})


def test_template_empty_steps_makes_titled_demo() -> None:
    demo = TemplateScriptGenerator().generate({"title": "Bare"})
    assert demo.scenes == []
    assert demo.title == "Bare"


def test_template_custom_geometry_and_voice() -> None:
    demo = TemplateScriptGenerator().generate(
        {"title": "G", "width": 800, "height": 600, "voice": "nova", "steps": []}
    )
    assert (demo.width, demo.height) == (800, 600)
    assert demo.voice == "nova"


def test_template_accepts_action_objects() -> None:
    action = Action(ActionType.CLICK, {"sel": "#x"})
    demo = TemplateScriptGenerator().generate(
        {"title": "T", "steps": [{"narration": "go", "actions": [action]}]}
    )
    assert demo.scenes[0].chunks[0].actions[0] is action


def test_template_action_dict_missing_type_raises() -> None:
    with pytest.raises(ValueError):
        TemplateScriptGenerator().generate(
            {"title": "T", "steps": [{"narration": "x", "actions": [{"params": {}}]}]}
        )


def test_template_unknown_kind_defaults_codebase() -> None:
    demo = TemplateScriptGenerator().generate(
        {"title": "T", "steps": [{"narration": "x", "kind": "weird"}]}
    )
    assert demo.scenes[0].kind == SceneKind.CODEBASE


def test_template_respects_explicit_scene_id() -> None:
    demo = TemplateScriptGenerator().generate(
        {"title": "T", "steps": [{"id": "custom", "narration": "x"}]}
    )
    assert demo.scenes[0].id == "custom"
    assert demo.scenes[0].chunks[0].id == "custom-c1"


def test_template_unique_chunk_ids() -> None:
    demo = TemplateScriptGenerator().generate(
        {"title": "T", "steps": [{"narration": "a"}, {"narration": "b"}]}
    )
    ids = [c.id for c in demo.iter_chunks()]
    assert len(ids) == len(set(ids))


# --- generate_codebase_demo -----------------------------------------------


class _FakeSummary:
    """Duck-typed stand-in for codebase.walker.ModuleSummary."""

    def __init__(self, name, path, functions, classes) -> None:
        self.name = name
        self.path = path
        self.functions = functions
        self.classes = classes


def test_codebase_demo_from_objects() -> None:
    summaries = [
        _FakeSummary("greeter.py", "src/greeter.py", ["greet", "wave"], ["Widget"]),
    ]
    demo = generate_codebase_demo(summaries, title="Tour")
    assert demo.validate() == []
    assert len(demo.scenes) == 1
    scene = demo.scenes[0]
    assert scene.title == "greeter.py"
    # open chunk + 1 class + 2 functions = 4 chunks
    assert len(scene.chunks) == 4
    types = [a.type for c in scene.chunks for a in c.actions]
    assert ActionType.OPEN_FILE in types
    assert types.count(ActionType.HIGHLIGHT_LINES) == 3


def test_codebase_demo_from_dicts() -> None:
    summaries = [
        {"name": "a.py", "path": "a.py", "functions": ["f"], "classes": []},
        {"name": "b.py", "path": "b.py", "functions": [], "classes": ["C"]},
    ]
    demo = generate_codebase_demo(summaries, title="Dict Tour")
    assert len(demo.scenes) == 2
    assert demo.validate() == []


def test_codebase_demo_empty_module_gets_chunk() -> None:
    summaries = [{"name": "empty.py", "functions": [], "classes": []}]
    demo = generate_codebase_demo(summaries, title="Empty")
    scene = demo.scenes[0]
    # open chunk + empty-note chunk
    assert len(scene.chunks) == 2
    assert any("small" in c.text for c in scene.chunks)


def test_codebase_demo_duck_typed_callable_names() -> None:
    # functions/classes given as dicts with a 'name' key
    summaries = [
        {
            "name": "x.py",
            "functions": [{"name": "run"}],
            "classes": [{"name": "Thing"}],
        }
    ]
    demo = generate_codebase_demo(summaries, title="DT")
    texts = " ".join(c.text for c in demo.scenes[0].chunks)
    assert "run" in texts
    assert "Thing" in texts


def test_codebase_demo_no_summaries() -> None:
    demo = generate_codebase_demo([], title="Nothing")
    assert demo.scenes == []
    assert demo.title == "Nothing"


def test_codebase_demo_empty_title_raises() -> None:
    with pytest.raises(ValueError):
        generate_codebase_demo([], title="  ")


def test_codebase_demo_missing_fields_defaults() -> None:
    # a summary with only a name; functions/classes absent
    demo = generate_codebase_demo([{"name": "solo.py"}], title="Solo")
    assert demo.scenes[0].title == "solo.py"
    assert demo.validate() == []


# --- LLMScriptGenerator ---------------------------------------------------


def test_llm_unconfigured_raises() -> None:
    gen = LLMScriptGenerator()
    with pytest.raises(BackendUnavailableError) as exc:
        gen.generate({"title": "x"})
    assert exc.value.backend == "llm"


def test_llm_stores_provider_and_model() -> None:
    gen = LLMScriptGenerator(provider="anthropic", model="claude")
    assert gen.provider == "anthropic"
    assert gen.model == "claude"


def test_script_generator_base_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        ScriptGenerator().generate({})
