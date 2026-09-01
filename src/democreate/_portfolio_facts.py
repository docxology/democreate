"""Project discovery and facts collection for the portfolio subsystem.

Split out of :mod:`democreate.portfolio` (agent refactoring lane); the public
surface remains importable from :mod:`democreate.portfolio`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._logging import get_logger
from .narration.project_summary import (
    KeyModule,
    ProjectFacts,
)

__all__ = [
    "ProjectResult",
    "PortfolioReport",
    "utc_stamp",
    "discover_projects",
    "collect_project_facts",
]

logger = get_logger(__name__)

# Directory names never treated as a project (build artifacts, vcs, metadata).
_NEVER_PROJECTS = frozenset(
    {
        "output",
        "node_modules",
        "__pycache__",
        "build",
        "dist",
        "site",
        "venv",
        ".venv",
    }
)


def utc_stamp(now: datetime | None = None) -> str:
    """Return a filesystem-safe UTC timestamp like ``20260625T164530Z``.

    Args:
        now: Optional fixed time (for deterministic tests); defaults to the
            current UTC time.
    """
    moment = now or datetime.now(timezone.utc)
    return moment.strftime("%Y%m%dT%H%M%SZ")


def _looks_like_project(path: Path) -> bool:
    """Whether ``path`` is a directory that looks like a software project."""
    if not path.is_dir() or path.name in _NEVER_PROJECTS or path.name.startswith("."):
        return False
    if (path / "README.md").exists() or (path / "pyproject.toml").exists():
        return True
    if (path / "package.json").exists():
        return True
    return any(True for _ in path.glob("*.py"))


def discover_projects(
    projects_dir: Path, *, skip: tuple[str, ...] = ()
) -> list[Path]:
    """Return the sorted project directories under ``projects_dir``.

    A directory is a project when it carries a ``README.md``, ``pyproject.toml``,
    ``package.json``, or top-level ``.py`` files. Build/vcs/metadata directories
    and anything in ``skip`` are excluded. Sorted for deterministic batch order.

    Args:
        projects_dir: Directory containing project subdirectories.
        skip: Project names to exclude.

    Returns:
        Sorted list of project directory paths.
    """
    projects_dir = Path(projects_dir)
    skip_set = set(skip)
    found = [
        child
        for child in sorted(projects_dir.iterdir())
        if child.name not in skip_set and _looks_like_project(child)
    ]
    logger.info("discovered %d project(s) under %s", len(found), projects_dir)
    return found


def _readme_summary(repo: Path) -> tuple[str, list[str]]:
    """Extract a one-line tagline and value bullets from the repo's README.

    Markdown is stripped to plain prose. The tagline is the first non-heading
    sentence; bullets come first from the README's own bullet list, then fall
    back to its leading sentences. Returns ``("", [])`` when no README exists.
    """
    readme = repo / "README.md"
    if not readme.exists():
        return "", []
    try:
        raw = readme.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return "", []

    tagline = ""
    bullets: list[str] = []
    sentences: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(
            ("#", "![", "[!", "!", "|", "```", "> ", "<", "=", "-->")
        ):
            continue
        is_bullet = stripped.startswith(("- ", "* ", "+ "))
        body = stripped[2:].strip() if is_bullet else stripped
        text = _strip_md(body)
        if not _is_prose(text):
            continue
        if is_bullet:
            if 12 <= len(text) <= 200:
                bullets.append(text)
            continue
        if not tagline and len(text.split()) >= 4:
            tagline = text
        if len(text) >= 24:
            sentences.append(text)
        if len(bullets) >= 4 and tagline:
            break

    if not bullets:
        bullets = [s for s in sentences[:4] if s != tagline][:3]
    return tagline, bullets[:4]


def _is_prose(text: str) -> bool:
    """Whether a stripped line reads as real prose (not badge/link residue)."""
    if len(text) < 12 or not text[:1].isalpha():
        return False
    # Reject lines dominated by punctuation/URL fragments left by badge rows.
    letters = sum(c.isalpha() or c.isspace() for c in text)
    return letters / len(text) >= 0.75


def _strip_md(text: str) -> str:
    """Strip the common inline markdown noise from a line of prose."""
    out = text
    # Drop image markdown ``![alt](url)`` entirely before collapsing links.
    while "![" in out:
        start = out.find("![")
        end = out.find(")", start)
        if end < 0:
            break
        out = out[:start] + out[end + 1 :]
    for token in ("**", "`", "*", "__", "_"):
        out = out.replace(token, "")
    # Collapse [label](url) → label
    while "](" in out and "[" in out:
        start = out.find("[")
        mid = out.find("](", start)
        end = out.find(")", mid)
        if start < 0 or mid < 0 or end < 0:
            break
        out = out[:start] + out[start + 1 : mid] + out[end + 1 :]
    return " ".join(out.split())


def _code_excerpt(summary: Any, *, max_lines: int = 18) -> str:
    """Return a real, bounded source excerpt for a module summary.

    Picks the **most substantive** top-level symbol (the class or function whose
    body spans the most lines) so the scene shows the module's real substance, not
    just whatever happens to come first; falls back to the head of the file. Lines
    are length-bounded so the excerpt autosizes on a code frame without cropping.
    """
    try:
        source = Path(summary.path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    lines = source.splitlines()

    candidates = list(summary.classes) + list(summary.functions)
    start = end = None
    if candidates:
        node = max(candidates, key=lambda n: (n.end_lineno - n.lineno, -n.lineno))
        start, end = node.lineno, node.end_lineno

    if start is None or end is None:
        chosen = lines[:max_lines]
    else:
        chosen = lines[start - 1 : min(end, start - 1 + max_lines)]

    trimmed = [ln[:96].rstrip() for i, ln in enumerate(chosen) if ln.strip() or i == 0]
    return "\n".join(trimmed).strip()


def _count_tests(summaries: list[Any]) -> int:
    """Count ``test_*`` functions in test modules (a deterministic proxy)."""
    total = 0
    for s in summaries:
        stem = Path(s.path).name
        is_test_file = stem.startswith("test_") or "test" in Path(s.path).parts
        if not is_test_file:
            continue
        total += sum(1 for f in s.functions if f.name.startswith("test"))
    return total


# Dev/test/build tooling — real dependencies, but not what the project is "built
# with" for a viewer, so they are kept out of the "Built with" beat.
_DEV_DEPS = frozenset(
    {
        "pytest", "_pytest", "hypothesis", "respx", "mock", "tox", "nox",
        "ruff", "mypy", "black", "isort", "flake8", "coverage", "pytest_cov",
        "setuptools", "pip", "wheel", "build", "twine", "pre_commit",
    }
)


def _collect_dependencies(summaries: list[Any], self_names: set[str]) -> list[str]:
    """Return the project's top external runtime libraries, most-imported first.

    Takes the first component of each absolute import, then drops: relative
    imports, the project's own packages/modules (``self_names``), the standard
    library, dunder/private names, and dev/test/build tooling. Ranks the rest by
    how many modules import them (breadth), so the result reads as "what this is
    built on", not an exhaustive requirements list.
    """
    import sys
    from collections import Counter

    stdlib = set(getattr(sys, "stdlib_module_names", set()))
    counts: Counter[str] = Counter()
    for s in summaries:
        seen_here: set[str] = set()
        for imp in s.imports:
            if not imp or imp.startswith("."):
                continue
            top = imp.split(".", 1)[0]
            if (
                top in self_names
                or top in stdlib
                or top in _DEV_DEPS
                or top.startswith("_")
            ):
                continue
            seen_here.add(top)
        counts.update(seen_here)  # count once per module that imports it
    # Tie-break alphabetically so the order is deterministic across runs.
    return [name for name, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))][:6]


def _run_command(repo: Path) -> tuple[str, str]:
    """Choose a real, runnable command (and sample output) for the repo."""
    if (repo / "pyproject.toml").exists():
        return "uv run pytest -q", "all tests pass"
    if (repo / "package.json").exists():
        return "npm install && npm test", "tests passed"
    if (repo / "Makefile").exists():
        return "make", "build complete"
    return "ls -R | head", f"{repo.name} contents"


def collect_project_facts(repo: Path, *, max_modules: int = 6) -> ProjectFacts:
    """Walk ``repo`` and assemble its render-ready :class:`ProjectFacts`.

    Deterministic given the repository contents. Uses the stdlib codebase walker
    (Python-only by default); non-Python repos still get a README/tree/stat
    summary with no key-module code scenes.

    Args:
        repo: Repository root directory.
        max_modules: How many load-bearing modules to select for code scenes.

    Returns:
        The populated facts.
    """
    from .codebase.walker import walk_repository
    from .paper.script import _group_modules

    repo = Path(repo)
    name = repo.name
    tagline, bullets = _readme_summary(repo)

    summaries = walk_repository(repo)
    loc = sum(s.loc for s in summaries)
    class_count = sum(len(s.classes) for s in summaries)
    function_count = sum(len(s.functions) for s in summaries)

    groups = _group_modules(summaries) if summaries else []
    top_packages = [g[0] for g in groups]

    # Select load-bearing modules: most symbols first, skipping package markers
    # and test modules so the code scenes show the project's real substance.
    def _is_substantive(s: Any) -> bool:
        stem = Path(s.path).name
        return (
            stem not in {"__init__.py", "__main__.py"}
            and not stem.startswith("test_")
            and s.symbol_count > 0
        )

    # Rank by symbol count (substance), then public-over-private (a leading "_"
    # module is an implementation detail), then documented-over-undocumented, then
    # path for a stable, deterministic order.
    ranked = sorted(
        (s for s in summaries if _is_substantive(s)),
        key=lambda s: (
            -s.symbol_count,
            1 if s.name.startswith("_") else 0,
            0 if s.docstring else 1,
            s.path,
        ),
    )
    key_modules: list[KeyModule] = []
    seen_names: set[str] = set()
    for s in ranked:
        if s.name in seen_names:  # dedupe by module name for variety
            continue
        excerpt = _code_excerpt(s)
        if not excerpt:
            continue
        seen_names.add(s.name)
        # Named public symbols (classes first, then functions), for richer narration.
        public = [c.name for c in s.classes if not c.name.startswith("_")]
        public += [f.name for f in s.functions if not f.name.startswith("_")]
        key_modules.append(
            KeyModule(
                name=s.name,
                path=_relpath(Path(s.path), repo),
                docstring=s.docstring,
                code_excerpt=excerpt,
                symbol_count=s.symbol_count,
                symbols=public[:6],
                class_count=len(s.classes),
                function_count=len(s.functions),
            )
        )
        if len(key_modules) >= max_modules:
            break

    # Everything internal to the repo, so intra-repo absolute imports (e.g.
    # ``from models import X``, ``import export_nexus_kg``) are not mistaken for
    # third-party dependencies: the repo name, every module name, and every
    # directory name on a summarized path.
    self_names = {name, name.replace("-", "_"), *top_packages}
    for s in summaries:
        self_names.add(s.name)
        self_names.update(Path(s.path).parts)
    return ProjectFacts(
        name=name,
        tagline=tagline,
        overview_bullets=bullets,
        module_count=len(summaries),
        loc=loc,
        class_count=class_count,
        function_count=function_count,
        top_packages=top_packages,
        key_modules=key_modules,
        run_command=_run_command(repo),
        language="Python" if summaries else "mixed",
        test_count=_count_tests(summaries),
        dependencies=_collect_dependencies(summaries, self_names),
        packages=_substantive_packages(groups),
    )


def _substantive_packages(
    groups: list[tuple[str, list[str]]],
) -> list[tuple[str, list[str]]]:
    """Filter/rank package groups to the real, tour-worthy areas.

    Drops date/numeric-named dirs (e.g. dated experiment folders), excludes
    ``__init__``/test modules from each listing, keeps only areas with at least two
    substantive modules, and orders by module count (largest first).
    """

    out: list[tuple[str, list[str]]] = []
    for pkg, mods in groups:
        if re.match(r"^\d", pkg) or pkg.startswith("."):
            continue
        clean = [m for m in mods if m != "__init__" and not m.startswith("test")]
        if len(clean) >= 2:
            out.append((pkg, clean))
    return sorted(out, key=lambda pm: (-len(pm[1]), pm[0]))


def _relpath(path: Path, repo: Path) -> str:
    """Return ``path`` relative to ``repo`` as a forward-slash string."""
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.name


@dataclass
class ProjectResult:
    """Outcome of rendering one project.

    Attributes:
        name: Project directory name.
        ok: Whether a content-verified video was produced.
        video_path: Path to the produced MP4 (``None`` on failure).
        duration_s: Verified video duration in seconds (``0`` on failure).
        scenes: Number of scenes in the generated demo.
        error: Error message when ``ok`` is ``False``.
        facts: The collected facts as a dict (for the index), if available.
    """

    name: str
    ok: bool = False
    video_path: Path | None = None
    duration_s: float = 0.0
    scenes: int = 0
    error: str = ""
    facts: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-ready dict for the portfolio index."""
        return {
            "name": self.name,
            "ok": self.ok,
            "video_path": str(self.video_path) if self.video_path else None,
            "duration_s": round(self.duration_s, 2),
            "scenes": self.scenes,
            "error": self.error,
            "facts": self.facts,
        }


@dataclass
class PortfolioReport:
    """The result of a whole-directory portfolio run.

    Attributes:
        results: One :class:`ProjectResult` per attempted project.
        index_json: Path to the written ``portfolio_index.json``.
        index_html: Path to the written ``portfolio_index.html``.
        timestamp: The UTC stamp shared by this batch's output filenames.
    """

    results: list[ProjectResult] = field(default_factory=list)
    index_json: Path | None = None
    index_html: Path | None = None
    project_videos_dir: Path | None = None
    timestamp: str = ""

    @property
    def ok_count(self) -> int:
        """Number of projects that produced a verified video."""
        return sum(1 for r in self.results if r.ok)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-ready dict."""
        return {
            "timestamp": self.timestamp,
            "ok_count": self.ok_count,
            "total": len(self.results),
            "project_videos_dir": (
                str(self.project_videos_dir) if self.project_videos_dir else None
            ),
            "projects": [r.to_dict() for r in self.results],
        }
