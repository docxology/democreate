"""Tests for democreate.codebase.ast_viz (pure string visualizations)."""

from __future__ import annotations

from democreate.codebase.ast_viz import module_to_tree, repository_to_dot
from democreate.codebase.walker import summarize_source


def test_module_to_tree_structure(sample_python_source: str) -> None:
    summary = summarize_source(sample_python_source, path="example.py")
    tree = module_to_tree(summary)
    lines = tree.splitlines()
    assert lines[0] == "module example"
    assert "    class Widget" in lines
    assert "        def render(self)" in lines
    assert "    def greet(name)" in lines
    # Classes appear before functions.
    assert lines.index("    class Widget") < lines.index("    def greet(name)")
    # No trailing newline.
    assert not tree.endswith("\n")


def test_module_to_tree_empty() -> None:
    summary = summarize_source("x = 1\n", path="m.py")
    tree = module_to_tree(summary)
    assert tree == "module m"


def test_module_to_tree_method_args() -> None:
    summary = summarize_source(
        "class A:\n    def f(self, x, y):\n        pass\n", path="a.py"
    )
    tree = module_to_tree(summary)
    assert "        def f(self, x, y)" in tree


def test_repository_to_dot_structure(sample_python_source: str) -> None:
    s1 = summarize_source(sample_python_source, path="example.py")
    s2 = summarize_source("def lone():\n    pass\n", path="other.py")
    dot = repository_to_dot([s1, s2])
    assert dot.startswith("digraph codebase {")
    assert dot.rstrip().endswith("}")
    assert "subgraph cluster_0" in dot
    assert "subgraph cluster_1" in dot
    assert 'label="example"' in dot
    assert 'label="other"' in dot
    assert "class Widget" in dot
    assert "def greet" in dot
    assert "def lone" in dot


def test_repository_to_dot_empty() -> None:
    dot = repository_to_dot([])
    assert dot.startswith("digraph codebase {")
    assert dot.rstrip().endswith("}")


def test_repository_to_dot_escapes_quotes() -> None:
    summary = summarize_source('def f():\n    pass\n', path='weird".py')
    dot = repository_to_dot([summary])
    # Name with a quote must be escaped, never break the label string.
    assert '\\"' in dot


def test_repository_to_dot_deterministic(sample_python_source: str) -> None:
    s = summarize_source(sample_python_source, path="example.py")
    assert repository_to_dot([s]) == repository_to_dot([s])
