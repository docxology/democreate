"""Tests for democreate.codebase.dependency (graph + import-graph builder)."""

from __future__ import annotations

from pathlib import Path

import pytest

from democreate.codebase.dependency import DependencyGraph, build_import_graph
from democreate.errors import DemoCreateError

REPO_SRC = Path(__file__).resolve().parent.parent / "src" / "democreate"


def test_add_edge_creates_nodes() -> None:
    g = DependencyGraph()
    g.add_edge("a", "b")
    assert "a" in g.nodes
    assert "b" in g.nodes
    assert ("a", "b") in g.edges


def test_add_edge_dedup() -> None:
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("a", "b")
    assert g.edges.count(("a", "b")) == 1


def test_neighbors() -> None:
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("a", "c")
    assert g.neighbors("a") == ["b", "c"]
    assert g.neighbors("b") == []


def test_topological_order_respects_edges() -> None:
    g = DependencyGraph()
    # a -> b -> c : dependencies (targets) come before dependents (sources).
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    order = g.topological_order()
    assert order.index("c") < order.index("b")
    assert order.index("b") < order.index("a")


def test_topological_order_deterministic() -> None:
    g = DependencyGraph()
    g.add_node("z")
    g.add_node("y")
    g.add_node("x")
    # No edges: deterministic alphabetical order.
    assert g.topological_order() == ["x", "y", "z"]


def test_topological_order_cycle_raises() -> None:
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "a")
    with pytest.raises(DemoCreateError):
        g.topological_order()


def test_find_cycles_none() -> None:
    g = DependencyGraph()
    g.add_edge("a", "b")
    assert g.find_cycles() == []


def test_find_cycles_detects_injected_cycle() -> None:
    g = DependencyGraph()
    g.add_edge("a", "b")
    g.add_edge("b", "c")
    g.add_edge("c", "a")
    cycles = g.find_cycles()
    assert len(cycles) == 1
    assert set(cycles[0]) == {"a", "b", "c"}


def test_find_cycles_self_loop() -> None:
    g = DependencyGraph()
    g.add_edge("a", "a")
    cycles = g.find_cycles()
    assert cycles == [["a"]]


def test_to_dot() -> None:
    g = DependencyGraph()
    g.add_edge("a", "b")
    dot = g.to_dot()
    assert dot.startswith("digraph dependencies {")
    assert '"a" -> "b";' in dot
    assert dot.rstrip().endswith("}")


def test_build_import_graph_real_package() -> None:
    g = build_import_graph(REPO_SRC, package="democreate")
    assert "schema" in g.nodes
    assert "media" in g.nodes
    # media.py imports from .schema -> edge media -> schema.
    assert ("media", "schema") in g.edges


def test_build_import_graph_infers_package() -> None:
    g = build_import_graph(REPO_SRC)
    assert "schema" in g.nodes
    # External imports (json, dataclasses) must not appear as nodes.
    assert "json" not in g.nodes
    assert "dataclasses" not in g.nodes


def test_build_import_graph_is_acyclic_for_real_package() -> None:
    g = build_import_graph(REPO_SRC, package="democreate")
    # The real spine should have no internal import cycles.
    order = g.topological_order()
    assert set(order) == set(g.nodes)


def test_build_import_graph_synthetic(tmp_path: Path) -> None:
    pkg = tmp_path / "mypkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("from . import b\n", encoding="utf-8")
    (pkg / "b.py").write_text("import os\n", encoding="utf-8")
    g = build_import_graph(pkg, package="mypkg")
    assert "a" in g.nodes
    assert "b" in g.nodes
    assert ("a", "b") in g.edges
    # os is external; not a node.
    assert "os" not in g.nodes


def test_build_import_graph_absolute_internal_import(tmp_path: Path) -> None:
    pkg = tmp_path / "proj"
    pkg.mkdir()
    (pkg / "core.py").write_text("VALUE = 1\n", encoding="utf-8")
    (pkg / "app.py").write_text("from proj import core\n", encoding="utf-8")
    g = build_import_graph(pkg, package="proj")
    assert ("app", "core") in g.edges
