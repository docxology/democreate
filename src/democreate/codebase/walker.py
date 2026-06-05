"""AST-based source walking for the codebase subsystem.

This module summarizes Python source using only the standard library ``ast``
module. It extracts the module docstring, top-level functions, classes (with
their methods), imports, and line count into plain dataclasses that round-trip
to JSON-ready dicts. ``tree-sitter`` is an *optional* upgrade for multi-language
parsing; the deterministic default here is pure stdlib and always available.

The produced :class:`ModuleSummary` is the shared currency consumed by
:mod:`democreate.codebase.ast_viz` (text/DOT visualization) and
:mod:`democreate.codebase.dependency` (import graphs).
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .._logging import get_logger
from ..errors import DemoCreateError

__all__ = [
    "FunctionInfo",
    "ClassInfo",
    "ModuleSummary",
    "summarize_source",
    "summarize_module",
    "walk_repository",
]

logger = get_logger(__name__)


@dataclass
class FunctionInfo:
    """A summarized function or method.

    Attributes:
        name: The function/method name.
        lineno: 1-based line where the ``def`` begins.
        end_lineno: 1-based line where the function body ends.
        args: Ordered list of argument names (including ``self``/``cls``).
        docstring: The function docstring, or ``None`` if absent.
        is_method: ``True`` when this function is defined inside a class body.
    """

    name: str
    lineno: int
    end_lineno: int
    args: list[str]
    docstring: str | None
    is_method: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-ready dict.

        Returns:
            A dict with every field of this function summary.
        """
        return {
            "name": self.name,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "args": list(self.args),
            "docstring": self.docstring,
            "is_method": self.is_method,
        }


@dataclass
class ClassInfo:
    """A summarized class and its methods.

    Attributes:
        name: The class name.
        lineno: 1-based line where the ``class`` begins.
        end_lineno: 1-based line where the class body ends.
        docstring: The class docstring, or ``None`` if absent.
        methods: Summaries of the methods defined directly on the class.
    """

    name: str
    lineno: int
    end_lineno: int
    docstring: str | None
    methods: list[FunctionInfo] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-ready dict.

        Returns:
            A dict with class fields and nested method dicts.
        """
        return {
            "name": self.name,
            "lineno": self.lineno,
            "end_lineno": self.end_lineno,
            "docstring": self.docstring,
            "methods": [m.to_dict() for m in self.methods],
        }


@dataclass
class ModuleSummary:
    """A structural summary of one Python module.

    Attributes:
        path: Filesystem path (or ``"<string>"`` for in-memory sources).
        name: Logical module name (e.g. ``"democreate.schema"``).
        docstring: The module-level docstring, or ``None`` if absent.
        functions: Top-level function summaries.
        classes: Top-level class summaries.
        imports: Imported module names referenced by the source.
        loc: Number of lines of code in the source.
    """

    path: str
    name: str
    docstring: str | None
    functions: list[FunctionInfo] = field(default_factory=list)
    classes: list[ClassInfo] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    loc: int = 0

    @property
    def symbol_count(self) -> int:
        """Total number of named symbols (functions + classes + methods)."""
        method_total = sum(len(c.methods) for c in self.classes)
        return len(self.functions) + len(self.classes) + method_total

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain JSON-ready dict.

        Returns:
            A dict with module fields plus nested function/class dicts and the
            derived ``symbol_count``.
        """
        return {
            "path": self.path,
            "name": self.name,
            "docstring": self.docstring,
            "functions": [f.to_dict() for f in self.functions],
            "classes": [c.to_dict() for c in self.classes],
            "imports": list(self.imports),
            "loc": self.loc,
            "symbol_count": self.symbol_count,
        }


def _arg_names(func: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    """Collect every argument name from a function definition.

    Args:
        func: The function/async-function AST node.

    Returns:
        Ordered argument names: positional-only, positional, ``*args``,
        keyword-only, and ``**kwargs``.
    """
    a = func.args
    names: list[str] = []
    names.extend(p.arg for p in a.posonlyargs)
    names.extend(p.arg for p in a.args)
    if a.vararg is not None:
        names.append("*" + a.vararg.arg)
    names.extend(p.arg for p in a.kwonlyargs)
    if a.kwarg is not None:
        names.append("**" + a.kwarg.arg)
    return names


def _end_line(node: ast.AST, fallback: int) -> int:
    """Return ``node.end_lineno`` if present, else ``fallback``.

    Args:
        node: An AST node that may carry ``end_lineno``.
        fallback: Value to use when ``end_lineno`` is unset.

    Returns:
        The resolved 1-based end line number.
    """
    end = getattr(node, "end_lineno", None)
    return end if end is not None else fallback


def _summarize_function(
    node: ast.FunctionDef | ast.AsyncFunctionDef, *, is_method: bool
) -> FunctionInfo:
    """Build a :class:`FunctionInfo` from a function AST node.

    Args:
        node: The function/async-function node.
        is_method: Whether this is a method on a class.

    Returns:
        The populated function summary.
    """
    return FunctionInfo(
        name=node.name,
        lineno=node.lineno,
        end_lineno=_end_line(node, node.lineno),
        args=_arg_names(node),
        docstring=ast.get_docstring(node),
        is_method=is_method,
    )


def _summarize_class(node: ast.ClassDef) -> ClassInfo:
    """Build a :class:`ClassInfo` from a class AST node.

    Args:
        node: The class node.

    Returns:
        The populated class summary, including its methods in source order.
    """
    methods: list[FunctionInfo] = []
    for child in node.body:
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
            methods.append(_summarize_function(child, is_method=True))
    return ClassInfo(
        name=node.name,
        lineno=node.lineno,
        end_lineno=_end_line(node, node.lineno),
        docstring=ast.get_docstring(node),
        methods=methods,
    )


def _collect_imports(tree: ast.Module) -> list[str]:
    """Collect imported module names from an AST module.

    ``import a.b`` yields ``"a.b"``. ``from a.b import c`` yields both ``"a.b"``
    and ``"a.b.c"`` so an imported submodule can be resolved as an edge target.
    Relative imports (``from . import x``) yield ``".x"`` (the imported sibling
    name); ``from .pkg import y`` yields ``".pkg"`` and ``".pkg.y"``.

    Args:
        tree: The parsed module AST.

    Returns:
        Sorted, de-duplicated import target names.
    """
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            if node.module:
                base = prefix + node.module
                found.add(base)
                for alias in node.names:
                    found.add(f"{base}.{alias.name}")
            else:
                # Pure relative `from . import x, y` — each name is a sibling.
                for alias in node.names:
                    found.add(prefix + alias.name)
    return sorted(found)


def summarize_source(
    source: str, *, path: str = "<string>", name: str | None = None
) -> ModuleSummary:
    """Summarize Python source text into a :class:`ModuleSummary`.

    Args:
        source: The Python source code.
        path: Logical path label recorded on the summary.
        name: Logical module name; defaults to the stem of ``path``.

    Returns:
        The structural summary of the source.

    Raises:
        DemoCreateError: If the source is not valid Python.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise DemoCreateError(
            f"failed to parse Python source from {path!r}: {exc}"
        ) from exc

    if name is None:
        name = Path(path).stem if path != "<string>" else "<string>"

    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(_summarize_function(node, is_method=False))
        elif isinstance(node, ast.ClassDef):
            classes.append(_summarize_class(node))

    loc = len(source.splitlines())
    return ModuleSummary(
        path=path,
        name=name,
        docstring=ast.get_docstring(tree),
        functions=functions,
        classes=classes,
        imports=_collect_imports(tree),
        loc=loc,
    )


def summarize_module(path: Path) -> ModuleSummary:
    """Read a Python file and summarize it.

    Args:
        path: Path to a ``.py`` file.

    Returns:
        The structural summary of the file.

    Raises:
        DemoCreateError: If the file cannot be read or is not valid Python.
    """
    path = Path(path)
    try:
        source = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise DemoCreateError(f"cannot read module {path}: {exc}") from exc
    return summarize_source(source, path=str(path), name=path.stem)


def walk_repository(
    root: Path,
    *,
    pattern: str = "**/*.py",
    exclude: tuple[str, ...] = ("__pycache__", ".venv", "build", "dist"),
) -> list[ModuleSummary]:
    """Summarize every matching Python file under ``root``.

    Files whose path contains any excluded directory part are skipped. Results
    are returned in a deterministic (sorted by path) order. Individual files
    that fail to parse are logged and skipped rather than aborting the walk.

    Args:
        root: Repository root to walk.
        pattern: Glob pattern for files to include.
        exclude: Directory-name parts to skip.

    Returns:
        Module summaries sorted by path.
    """
    root = Path(root)
    exclude_set = set(exclude)
    summaries: list[ModuleSummary] = []
    for file_path in sorted(root.glob(pattern)):
        if not file_path.is_file():
            continue
        if exclude_set.intersection(file_path.parts):
            continue
        try:
            summaries.append(summarize_module(file_path))
        except DemoCreateError as exc:
            logger.warning("skipping unparsable file %s: %s", file_path, exc)
    return summaries
