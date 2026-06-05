"""Text and Graphviz visualization of module summaries.

Pure string builders that turn the :class:`~democreate.codebase.walker.ModuleSummary`
structures produced by the walker into human-readable artifacts: an indented text
tree (one module) and a Graphviz DOT graph (a whole repository). No I/O and no
heavy dependencies — these are deterministic pure functions suitable for direct
embedding in a codebase scene's context.
"""

from __future__ import annotations

from .walker import ModuleSummary

__all__ = ["module_to_tree", "repository_to_dot"]

_INDENT = "    "


def module_to_tree(summary: ModuleSummary) -> str:
    """Render one module summary as an indented text tree.

    Layout::

        module <name>
            class <ClassName>
                def <method>(<args>)
            def <function>(<args>)

    Args:
        summary: The module summary to render.

    Returns:
        A multi-line string (no trailing newline).
    """
    lines: list[str] = [f"module {summary.name}"]
    for cls in summary.classes:
        lines.append(f"{_INDENT}class {cls.name}")
        for method in cls.methods:
            args = ", ".join(method.args)
            lines.append(f"{_INDENT * 2}def {method.name}({args})")
    for func in summary.functions:
        args = ", ".join(func.args)
        lines.append(f"{_INDENT}def {func.name}({args})")
    return "\n".join(lines)


def _dot_escape(text: str) -> str:
    """Escape a string for use inside a DOT double-quoted label.

    Args:
        text: Raw label text.

    Returns:
        The escaped text (backslashes and quotes neutralized).
    """
    return text.replace("\\", "\\\\").replace('"', '\\"')


def repository_to_dot(summaries: list[ModuleSummary]) -> str:
    """Render a repository's module summaries as a Graphviz DOT graph.

    Each module becomes a subgraph cluster containing one node per top-level
    class and function. The output is deterministic given the input order.

    Args:
        summaries: Module summaries to render.

    Returns:
        A complete DOT document as a string.
    """
    lines: list[str] = ["digraph codebase {", "  rankdir=LR;", "  node [shape=box];"]
    for idx, summary in enumerate(summaries):
        label = _dot_escape(summary.name)
        lines.append(f'  subgraph cluster_{idx} {{')
        lines.append(f'    label="{label}";')
        for cls in summary.classes:
            node_id = f"{idx}_class_{_dot_escape(cls.name)}"
            lines.append(
                f'    "{node_id}" [label="class {_dot_escape(cls.name)}", '
                f"shape=box, style=filled];"
            )
        for func in summary.functions:
            node_id = f"{idx}_func_{_dot_escape(func.name)}"
            lines.append(
                f'    "{node_id}" [label="def {_dot_escape(func.name)}"];'
            )
        lines.append("  }")
    lines.append("}")
    return "\n".join(lines)
