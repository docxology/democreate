"""Portfolio orchestration: a directory of repositories becomes a shelf of videos.

This is a thin orchestration sibling of :mod:`democreate.pipeline`. It carries no
spine logic — it walks a project with the codebase subsystem, derives
:class:`~democreate.narration.project_summary.ProjectFacts`, renders an
architecture diagram with the animation subsystem, asks the (pure) project-summary
generator for a :class:`~democreate.schema.Demo`, and runs the existing render
pipeline to a content-verified MP4.

Two surfaces:

* :func:`render_project` — one repository → one timestamped, verified
  ``output/<name>/video/<name>-summary-<UTC>.mp4`` (plus the full workspace:
  frames, captions, player, transcript, chapters, provenance).
* :func:`render_portfolio` — a directory of repositories → one
  ``output/<name>/`` subfolder per project, a ``portfolio_index.json`` and a
  ``portfolio_index.html`` gallery. A single project that fails to render is
  recorded as failed and the batch continues — one bad repo never aborts the run.

Facts collection (:func:`collect_project_facts`) and project discovery
(:func:`discover_projects`) are deterministic given a repository; only the output
*paths* carry a timestamp, so the generated demo itself stays byte-stable.
"""

from __future__ import annotations

import html
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ._logging import get_logger
from .narration.project_summary import (
    KeyModule,
    ProjectFacts,
    generate_project_summary_demo,
)

__all__ = [
    "ProjectResult",
    "PortfolioReport",
    "utc_stamp",
    "discover_projects",
    "collect_project_facts",
    "build_project_demo",
    "render_project",
    "render_portfolio",
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
            "projects": [r.to_dict() for r in self.results],
        }


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


def collect_project_facts(repo: Path, *, max_modules: int = 3) -> ProjectFacts:
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
        key_modules.append(
            KeyModule(
                name=s.name,
                path=_relpath(Path(s.path), repo),
                docstring=s.docstring,
                code_excerpt=excerpt,
                symbol_count=s.symbol_count,
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
    )


def _relpath(path: Path, repo: Path) -> str:
    """Return ``path`` relative to ``repo`` as a forward-slash string."""
    try:
        return path.resolve().relative_to(repo.resolve()).as_posix()
    except ValueError:
        return path.name


def build_project_demo(
    repo: Path,
    workspace,
    *,
    config=None,
    max_modules: int = 3,
    title: str | None = None,
):
    """Collect facts, render an architecture diagram, and build the summary demo.

    Args:
        repo: Repository root.
        workspace: A :class:`~democreate.project_paths.Workspace` to write the
            architecture PNG into.
        config: Optional :class:`~democreate.config.RenderConfig` (for geometry).
        max_modules: Key-module bound.
        title: Optional demo title.

    Returns:
        ``(demo, facts)`` — the built :class:`~democreate.schema.Demo` and its
        :class:`ProjectFacts`.
    """
    from .config import RenderConfig

    cfg = config or RenderConfig()
    facts = collect_project_facts(repo, max_modules=max_modules)
    arch_image = _render_architecture(repo, workspace, facts, cfg)
    demo = generate_project_summary_demo(
        facts,
        title=title,
        architecture_image=str(arch_image) if arch_image else None,
        width=cfg.video.width,
        height=cfg.video.height,
        voice=cfg.audio.voice or "default",
        max_modules=max_modules,
    )
    return demo, facts


def _render_architecture(repo: Path, workspace, facts: ProjectFacts, cfg) -> Path | None:
    """Render a real architecture diagram PNG for the repo, or ``None``."""
    from .animation.diagram import DiagramNode, render_architecture_diagram
    from .codebase.walker import walk_repository
    from .paper.script import _group_modules

    summaries = walk_repository(repo)
    columns = [
        (pkg, [DiagramNode(label=m) for m in mods[:6]])
        for pkg, mods in _group_modules(summaries)
    ]
    if not columns:
        return None
    arch_dir = Path(workspace.root) / "assets"
    arch_dir.mkdir(parents=True, exist_ok=True)
    arch_path = arch_dir / "architecture.png"
    image = render_architecture_diagram(
        (cfg.video.width, cfg.video.height),
        title=f"{facts.name} — architecture",
        columns=columns[:5],
    )
    image.save(arch_path)
    return arch_path


def render_project(
    repo: Path,
    output_root: Path,
    *,
    config=None,
    tts: str = "system",
    voice: str = "",
    max_modules: int = 3,
    timestamp: str | None = None,
    verify: bool = True,
) -> ProjectResult:
    """Render one repository to a timestamped, verified summary MP4.

    The video lands at ``output_root/<name>/video/<name>-summary-<UTC>.mp4`` and
    the full workspace (frames, captions, player, transcript, provenance) sits
    alongside it under ``output_root/<name>/``.

    Args:
        repo: Repository root.
        output_root: Parent directory; a ``<name>/`` subfolder is created under it.
        config: Optional :class:`~democreate.config.RenderConfig`.
        tts: TTS backend (``"system"`` for a real OS voice; ``"silent"`` for none).
        voice: Optional voice id override.
        max_modules: Key-module bound.
        timestamp: Optional fixed UTC stamp (deterministic tests); else now.
        verify: Run content verification on the produced MP4.

    Returns:
        A :class:`ProjectResult` (``ok`` reflects content verification).
    """
    from .config import RenderConfig
    from .narration.tts import get_tts_backend
    from .pipeline import Pipeline, render_video
    from .project_paths import Workspace

    repo = Path(repo)
    name = repo.name
    cfg = config or RenderConfig()
    if voice:
        cfg.audio.voice = voice
    cfg.audio.backend = tts
    cfg.metadata.source = name

    ws = Workspace(Path(output_root) / name)
    demo, facts = build_project_demo(
        repo, ws, config=cfg, max_modules=max_modules, title=f"{name} — a tour"
    )

    use_voice = cfg.audio.voice if cfg.audio.backend != "silent" else None
    backend = get_tts_backend(cfg.audio.backend, voice=use_voice)
    result = Pipeline(tts_backend=backend, strict=False, config=cfg).run(demo, ws)

    stamp = timestamp or utc_stamp()
    video_path = ws.video / f"{name}-summary-{stamp}.mp4"
    _out, report = render_video(result, out_path=video_path, verify=verify, config=cfg)

    ok = bool(report.ok) if report is not None else video_path.exists()
    duration = float(report.duration_s) if report is not None else 0.0
    if report is not None and not report.ok:
        logger.warning("project %s verification problems: %s", name, report.problems)
    return ProjectResult(
        name=name,
        ok=ok,
        video_path=video_path,
        duration_s=duration,
        scenes=len(demo.scenes),
        facts=facts.to_dict(),
    )


def render_portfolio(
    projects_dir: Path,
    output_root: Path,
    *,
    config=None,
    tts: str = "system",
    voice: str = "",
    max_projects: int = 0,
    max_modules: int = 3,
    skip: tuple[str, ...] = (),
    timestamp: str | None = None,
    verify: bool = True,
) -> PortfolioReport:
    """Render a summary video for every project under ``projects_dir``.

    Each project gets its own ``output_root/<name>/`` subfolder. One project's
    failure is isolated: it is recorded as ``ok=False`` with its error and the
    batch continues. Writes ``portfolio_index.json`` and ``portfolio_index.html``.

    Args:
        projects_dir: Directory of project subdirectories.
        output_root: Output parent directory.
        config: Optional :class:`~democreate.config.RenderConfig`.
        tts: TTS backend.
        voice: Optional voice id override.
        max_projects: Cap on number of projects (``0`` = all discovered).
        max_modules: Key-module bound per project.
        skip: Project names to exclude.
        timestamp: Shared UTC stamp for this batch (deterministic tests); else now.
        verify: Run content verification per project.

    Returns:
        A :class:`PortfolioReport`.
    """
    output_root = Path(output_root)
    output_root.mkdir(parents=True, exist_ok=True)
    stamp = timestamp or utc_stamp()

    projects = discover_projects(projects_dir, skip=skip)
    if max_projects > 0:
        projects = projects[:max_projects]

    results: list[ProjectResult] = []
    for repo in projects:
        logger.info("portfolio: rendering %s", repo.name)
        try:
            results.append(
                render_project(
                    repo,
                    output_root,
                    config=config,
                    tts=tts,
                    voice=voice,
                    max_modules=max_modules,
                    timestamp=stamp,
                    verify=verify,
                )
            )
        except Exception as exc:  # noqa: BLE001 - one repo must never abort the batch
            logger.warning("portfolio: %s failed: %s", repo.name, exc)
            results.append(ProjectResult(name=repo.name, ok=False, error=str(exc)))

    report = PortfolioReport(results=results, timestamp=stamp)
    report.index_json = _write_index_json(output_root, report)
    report.index_html = _write_index_html(output_root, report)
    logger.info(
        "portfolio complete: %d/%d ok → %s",
        report.ok_count,
        len(results),
        output_root,
    )
    return report


def _write_index_json(output_root: Path, report: PortfolioReport) -> Path:
    """Write the machine-readable portfolio index."""
    path = output_root / "portfolio_index.json"
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path


def _write_index_html(output_root: Path, report: PortfolioReport) -> Path:
    """Write a minimal self-contained HTML gallery linking each project video."""
    rows: list[str] = []
    for r in sorted(report.results, key=lambda x: x.name):
        name = html.escape(r.name)
        if r.ok and r.video_path is not None:
            try:
                rel = r.video_path.relative_to(output_root).as_posix()
            except ValueError:
                rel = r.video_path.as_posix()
            link = f'<a href="{html.escape(rel)}">▶ {name}</a>'
            meta = f"{r.duration_s:.0f}s · {r.scenes} scenes"
            status = "ok"
        else:
            link = name
            meta = html.escape(r.error or "not rendered")
            status = "failed"
        rows.append(
            f'<li class="{status}">{link} '
            f'<span class="meta">{html.escape(meta)}</span></li>'
        )
    body = "\n".join(rows)
    doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>DemoCreate portfolio — {html.escape(report.timestamp)}</title>
<style>
 body{{background:#0a0a0a;color:#e6edf3;font:16px/1.5 system-ui,sans-serif;margin:2rem auto;max-width:48rem}}
 h1{{font-weight:600}} ul{{list-style:none;padding:0}}
 li{{padding:.6rem .8rem;border-radius:.4rem;margin:.3rem 0;background:#141414}}
 li.failed{{opacity:.6}} a{{color:#ff4d4d;text-decoration:none}} a:hover{{text-decoration:underline}}
 .meta{{color:#8b949e;font-size:.85em;float:right}}
</style></head><body>
<h1>DemoCreate portfolio</h1>
<p>{report.ok_count} of {len(report.results)} projects rendered · batch {html.escape(report.timestamp)}</p>
<ul>
{body}
</ul></body></html>
"""
    path = output_root / "portfolio_index.html"
    path.write_text(doc, encoding="utf-8")
    return path
