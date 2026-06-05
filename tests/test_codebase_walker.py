"""Tests for democreate.codebase.walker (pure stdlib AST summarization)."""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.codebase.walker import (
    ClassInfo,
    FunctionInfo,
    ModuleSummary,
    summarize_module,
    summarize_source,
    walk_repository,
)
from democreate.errors import DemoCreateError

REPO_SRC = Path(__file__).resolve().parent.parent / "src" / "democreate"


def test_summarize_source_extracts_everything(sample_python_source: str) -> None:
    summary = summarize_source(sample_python_source, path="example.py")
    assert summary.name == "example"
    assert summary.path == "example.py"
    assert summary.docstring == "Example module."

    func_names = {f.name for f in summary.functions}
    assert func_names == {"greet"}
    greet = next(f for f in summary.functions if f.name == "greet")
    assert greet.args == ["name"]
    assert greet.docstring == "Return a greeting."
    assert greet.is_method is False
    assert greet.end_lineno >= greet.lineno

    class_names = {c.name for c in summary.classes}
    assert class_names == {"Widget"}
    widget = next(c for c in summary.classes if c.name == "Widget")
    assert widget.docstring == "A widget."
    method_names = {m.name for m in widget.methods}
    assert method_names == {"render"}
    render = widget.methods[0]
    assert render.is_method is True
    assert render.args == ["self"]
    assert render.docstring == "Render it."


def test_summarize_source_imports(sample_python_source: str) -> None:
    summary = summarize_source(sample_python_source)
    assert "os" in summary.imports
    assert "pathlib" in summary.imports
    # Sorted + de-duplicated.
    assert summary.imports == sorted(summary.imports)


def test_summarize_source_loc(sample_python_source: str) -> None:
    summary = summarize_source(sample_python_source)
    assert summary.loc == len(sample_python_source.splitlines())
    assert summary.loc > 0


def test_symbol_count() -> None:
    summary = summarize_source(
        "def a():\n    pass\n\n"
        "def b():\n    pass\n\n"
        "class C:\n    def m(self):\n        pass\n"
        "    def n(self):\n        pass\n"
    )
    # 2 functions + 1 class + 2 methods = 5.
    assert summary.symbol_count == 5


def test_default_name_for_string_source() -> None:
    summary = summarize_source("x = 1\n")
    assert summary.name == "<string>"
    assert summary.path == "<string>"


def test_explicit_name_override() -> None:
    summary = summarize_source("x = 1\n", path="p.py", name="custom.name")
    assert summary.name == "custom.name"


def test_empty_source() -> None:
    summary = summarize_source("")
    assert summary.functions == []
    assert summary.classes == []
    assert summary.imports == []
    assert summary.docstring is None
    assert summary.loc == 0
    assert summary.symbol_count == 0


def test_async_function_and_star_args() -> None:
    summary = summarize_source(
        "async def f(a, b, *args, c=1, **kw):\n    pass\n"
    )
    assert len(summary.functions) == 1
    fn = summary.functions[0]
    assert fn.args == ["a", "b", "*args", "c", "**kw"]


def test_relative_import_collected() -> None:
    summary = summarize_source("from . import sibling\nfrom .pkg import thing\n")
    assert ".sibling" in summary.imports
    assert ".pkg" in summary.imports


def test_to_dict_roundtrip_is_jsonable(sample_python_source: str) -> None:
    import json

    summary = summarize_source(sample_python_source, path="example.py")
    data = summary.to_dict()
    # JSON-serializable.
    text = json.dumps(data)
    reloaded = json.loads(text)
    assert reloaded["name"] == "example"
    assert reloaded["symbol_count"] == summary.symbol_count
    assert reloaded["classes"][0]["methods"][0]["name"] == "render"


def test_dataclass_to_dict_components() -> None:
    fi = FunctionInfo("f", 1, 2, ["x"], "doc", is_method=True)
    assert fi.to_dict()["is_method"] is True
    ci = ClassInfo("C", 1, 5, None, methods=[fi])
    assert ci.to_dict()["methods"][0]["name"] == "f"
    ms = ModuleSummary("p.py", "p", "doc", functions=[fi], classes=[ci])
    assert ms.to_dict()["name"] == "p"


def test_syntax_error_raises_democreate_error() -> None:
    with pytest.raises(DemoCreateError):
        summarize_source("def broken(:\n    pass\n")


def test_summarize_module_reads_file(tmp_path: Path, sample_python_source: str) -> None:
    f = tmp_path / "mod.py"
    f.write_text(sample_python_source, encoding="utf-8")
    summary = summarize_module(f)
    assert summary.name == "mod"
    assert summary.path == str(f)
    assert {c.name for c in summary.classes} == {"Widget"}


def test_summarize_module_missing_file(tmp_path: Path) -> None:
    with pytest.raises(DemoCreateError):
        summarize_module(tmp_path / "does_not_exist.py")


def test_summarize_module_syntax_error(tmp_path: Path) -> None:
    f = tmp_path / "bad.py"
    f.write_text("def x(:\n", encoding="utf-8")
    with pytest.raises(DemoCreateError):
        summarize_module(f)


def test_walk_repository_finds_real_modules() -> None:
    summaries = walk_repository(REPO_SRC)
    names = {s.name for s in summaries}
    assert "schema" in names
    assert "media" in names
    # Deterministic sorted-by-path order.
    paths = [s.path for s in summaries]
    assert paths == sorted(paths)


def test_walk_repository_excludes(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "good.py").write_text("x = 1\n", encoding="utf-8")
    cache = tmp_path / "pkg" / "__pycache__"
    cache.mkdir()
    (cache / "skip.py").write_text("y = 2\n", encoding="utf-8")
    summaries = walk_repository(tmp_path)
    names = {s.name for s in summaries}
    assert "good" in names
    assert "skip" not in names


def test_walk_repository_skips_unparsable(tmp_path: Path) -> None:
    (tmp_path / "ok.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "bad.py").write_text("def f(:\n", encoding="utf-8")
    summaries = walk_repository(tmp_path)
    names = {s.name for s in summaries}
    assert "ok" in names
    assert "bad" not in names
