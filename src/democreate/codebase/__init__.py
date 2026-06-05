"""Codebase analysis subsystem for DemoCreate.

Pure-stdlib AST traversal, visualization, and dependency-graph tooling that turns
a Python repository into structured summaries a codebase scene can narrate. The
default backend uses the standard library ``ast`` module only; ``tree-sitter`` is
an optional multi-language upgrade (extra: ``codebase``) that this subsystem
detects at call time and never imports at module top level.

Public API:
    * :class:`FunctionInfo`, :class:`ClassInfo`, :class:`ModuleSummary`
    * :func:`summarize_source`, :func:`summarize_module`, :func:`walk_repository`
    * :func:`module_to_tree`, :func:`repository_to_dot`
    * :class:`DependencyGraph`, :func:`build_import_graph`
"""

from __future__ import annotations

from .ast_viz import module_to_tree, repository_to_dot
from .dependency import DependencyGraph, build_import_graph
from .walker import (
    ClassInfo,
    FunctionInfo,
    ModuleSummary,
    summarize_module,
    summarize_source,
    walk_repository,
)

__all__ = [
    "FunctionInfo",
    "ClassInfo",
    "ModuleSummary",
    "summarize_source",
    "summarize_module",
    "walk_repository",
    "module_to_tree",
    "repository_to_dot",
    "DependencyGraph",
    "build_import_graph",
]
