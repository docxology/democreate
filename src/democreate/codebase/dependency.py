"""Module dependency graphs built from import statements.

A :class:`DependencyGraph` is a small directed-graph value type with topological
ordering and cycle detection. :func:`build_import_graph` walks a repository and
wires up intra-package edges: an edge ``a -> b`` means module ``a`` imports
module ``b``, and both must be modules discovered under the walked root. The
result is fully deterministic and pure-stdlib.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..errors import DemoCreateError
from .walker import ModuleSummary, walk_repository

__all__ = ["DependencyGraph", "build_import_graph"]


@dataclass
class DependencyGraph:
    """A directed dependency graph over module names.

    An edge ``(a, b)`` means ``a`` depends on ``b`` (``a`` imports ``b``).

    Attributes:
        nodes: All node names, kept in insertion order, de-duplicated.
        edges: Directed edges as ``(source, target)`` pairs.
    """

    nodes: list[str] = field(default_factory=list)
    edges: list[tuple[str, str]] = field(default_factory=list)

    def add_node(self, node: str) -> None:
        """Add a node if not already present.

        Args:
            node: The node name to add.
        """
        if node not in self.nodes:
            self.nodes.append(node)

    def add_edge(self, source: str, target: str) -> None:
        """Add a directed edge, creating endpoints as needed.

        Duplicate edges are ignored so the graph stays a simple digraph.

        Args:
            source: The dependent node.
            target: The depended-upon node.
        """
        self.add_node(source)
        self.add_node(target)
        if (source, target) not in self.edges:
            self.edges.append((source, target))

    def neighbors(self, node: str) -> list[str]:
        """Return the direct successors of ``node`` (its dependencies).

        Args:
            node: The node whose out-neighbors to return.

        Returns:
            Target nodes of every edge whose source is ``node``, in edge order.
        """
        return [t for (s, t) in self.edges if s == node]

    def _out_degrees(self) -> dict[str, int]:
        """Compute the out-degree of every node.

        Returns:
            Mapping of node name to number of outgoing edges.
        """
        degree: dict[str, int] = {n: 0 for n in self.nodes}
        for src, _dst in self.edges:
            degree[src] = degree.get(src, 0) + 1
        return degree

    def topological_order(self) -> list[str]:
        """Return nodes in dependency order (dependencies before dependents).

        An edge ``(a, b)`` means ``a`` depends on ``b``, so ``b`` precedes ``a``
        in the returned order. Uses Kahn's algorithm over out-degrees (leaves —
        nodes with no dependencies — emitted first) with deterministic
        tie-breaking by node name.

        Returns:
            A topologically sorted list of node names.

        Raises:
            DemoCreateError: If the graph contains a cycle. The error message
                includes the offending cycles from :meth:`find_cycles`.
        """
        out_degree = self._out_degrees()
        # Predecessors map: who depends on each node.
        predecessors: dict[str, list[str]] = {n: [] for n in self.nodes}
        for src, dst in self.edges:
            predecessors[dst].append(src)

        ready = sorted(n for n in self.nodes if out_degree[n] == 0)
        order: list[str] = []
        while ready:
            node = ready.pop(0)
            order.append(node)
            new_ready: list[str] = []
            for src in predecessors[node]:
                out_degree[src] -= 1
                if out_degree[src] == 0:
                    new_ready.append(src)
            if new_ready:
                ready = sorted(ready + new_ready)

        if len(order) != len(self.nodes):
            cycles = self.find_cycles()
            raise DemoCreateError(
                f"dependency graph contains a cycle: {cycles}"
            )
        return order

    def find_cycles(self) -> list[list[str]]:
        """Find directed cycles via depth-first search.

        Returns:
            A list of cycles, each a list of node names forming the loop. The
            list is empty for an acyclic graph. Results are deterministic.
        """
        successors: dict[str, list[str]] = {n: [] for n in self.nodes}
        for src, dst in self.edges:
            successors[src].append(dst)

        cycles: list[list[str]] = []
        seen_signatures: set[frozenset[str]] = set()
        WHITE, GREY, BLACK = 0, 1, 2
        color: dict[str, int] = {n: WHITE for n in self.nodes}

        def dfs(node: str, stack: list[str]) -> None:
            color[node] = GREY
            stack.append(node)
            for nxt in successors[node]:
                if color[nxt] == GREY:
                    cycle = stack[stack.index(nxt):]
                    signature = frozenset(cycle)
                    if signature not in seen_signatures:
                        seen_signatures.add(signature)
                        cycles.append(list(cycle))
                elif color[nxt] == WHITE:
                    dfs(nxt, stack)
            stack.pop()
            color[node] = BLACK

        for start in sorted(self.nodes):
            if color[start] == WHITE:
                dfs(start, [])
        return cycles

    def to_dot(self) -> str:
        """Render the graph as a Graphviz DOT document.

        Returns:
            A complete DOT string with one node per graph node and one arrow
            per edge.
        """
        lines: list[str] = ["digraph dependencies {", "  rankdir=LR;", "  node [shape=box];"]
        for node in self.nodes:
            safe = node.replace('"', '\\"')
            lines.append(f'  "{safe}";')
        for src, dst in self.edges:
            safe_src = src.replace('"', '\\"')
            safe_dst = dst.replace('"', '\\"')
            lines.append(f'  "{safe_src}" -> "{safe_dst}";')
        lines.append("}")
        return "\n".join(lines)


def _module_key(summary: ModuleSummary, root: Path) -> str:
    """Compute the dotted module key for a summary relative to ``root``.

    Args:
        summary: The module summary.
        root: The walked repository root.

    Returns:
        A dotted module path (e.g. ``"democreate.schema"``), with any
        ``__init__`` suffix dropped to the package name.
    """
    try:
        rel = Path(summary.path).resolve().relative_to(root.resolve())
    except ValueError:
        rel = Path(summary.path)
    parts = list(rel.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def build_import_graph(
    root: Path, *, package: str | None = None
) -> DependencyGraph:
    """Build an intra-package import dependency graph for a repository.

    Walks ``root``, assigns each module a dotted key, then adds an edge from a
    module to any imported target that resolves to another discovered module.
    Imports of standard-library or third-party modules (not discovered under
    ``root``) are ignored, keeping the graph focused on internal structure.

    Args:
        root: Repository root to walk.
        package: Optional package prefix used to resolve relative imports. When
            ``None`` it is inferred from the root directory name.

    Returns:
        A deterministic :class:`DependencyGraph` of internal module edges.
    """
    root = Path(root)
    summaries = walk_repository(root)
    if package is None:
        package = root.name

    keys: dict[str, ModuleSummary] = {}
    ordered_keys: list[str] = []
    for summary in summaries:
        key = _module_key(summary, root)
        if key:
            keys[key] = summary
            ordered_keys.append(key)

    # Also index by leaf name and by package-qualified name for matching.
    known = set(keys)

    graph = DependencyGraph()
    for key in ordered_keys:
        graph.add_node(key)

    for key in ordered_keys:
        summary = keys[key]
        for imp in summary.imports:
            target = _resolve_import(imp, key, package, known)
            if target is not None and target != key:
                graph.add_edge(key, target)
    return graph


def _resolve_import(
    imp: str, importer_key: str, package: str, known: set[str]
) -> str | None:
    """Resolve an import string to a discovered module key, if internal.

    Args:
        imp: The raw import target (``"a.b"`` or relative ``".sibling"``).
        importer_key: Dotted key of the module performing the import.
        package: Package prefix for the repository.
        known: Set of all discovered module keys.

    Returns:
        The matching discovered module key, or ``None`` if the import is
        external or unresolvable to a discovered module.
    """
    if imp.startswith("."):
        level = len(imp) - len(imp.lstrip("."))
        remainder = imp.lstrip(".")
        base_parts = importer_key.split(".")
        # A relative import ascends ``level`` package levels from the importer.
        anchor = base_parts[: len(base_parts) - level] if level <= len(base_parts) else []
        candidate_parts = anchor + ([remainder] if remainder else [])
        candidate = ".".join(p for p in candidate_parts if p)
    else:
        candidate = imp

    if candidate in known:
        return candidate
    # Try matching by the package-qualified suffix, e.g. import "democreate.schema"
    # when the discovered key is "schema" under that package.
    if package and candidate.startswith(package + "."):
        stripped = candidate[len(package) + 1:]
        if stripped in known:
            return stripped
    # Try prefixing the discovered keys with the package.
    prefixed = f"{package}.{candidate}"
    for key in known:
        if f"{package}.{key}" == prefixed:
            return key
    return None
