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

from pathlib import Path

from ._logging import get_logger
from ._portfolio_facts import (  # noqa: F401 (re-exports)
    PortfolioReport,
    ProjectResult,
    _code_excerpt,
    _collect_dependencies,
    _count_tests,
    _looks_like_project,
    _readme_summary,
    _relpath,
    _run_command,
    _strip_md,
    _substantive_packages,
    collect_project_facts,
    discover_projects,
    utc_stamp,
)
from ._portfolio_render import (  # noqa: F401 (re-exports)
    _write_index_html,
    _write_index_json,
    build_project_demo,
    collect_project_videos,
    render_project,
)
from .config import RenderConfig  # noqa: F401

__all__ = [
    "ProjectResult",
    "PortfolioReport",
    "utc_stamp",
    "discover_projects",
    "collect_project_facts",
    "build_project_demo",
    "render_project",
    "render_portfolio",
    "collect_project_videos",
]

logger = get_logger(__name__)

def render_portfolio(
    projects_dir: Path,
    output_root: Path,
    *,
    config=None,
    tts: str = "system",
    voice: str = "",
    max_projects: int = 0,
    max_modules: int = 6,
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
    report.project_videos_dir = collect_project_videos(output_root, results)
    report.index_json = _write_index_json(output_root, report)
    report.index_html = _write_index_html(output_root, report)
    logger.info(
        "portfolio complete: %d/%d ok → %s",
        report.ok_count,
        len(results),
        output_root,
    )
    return report


# Implementation lives in :mod:`democreate._portfolio_facts` (discovery,
# facts, and the report dataclasses) and :mod:`democreate._portfolio_render`
# (rendering). Every name in ``__all__`` is re-exported here.
