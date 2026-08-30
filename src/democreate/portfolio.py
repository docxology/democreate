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

from dataclasses import dataclass, field
from typing import Any

from ._logging import get_logger
from ._portfolio_facts import (  # noqa: F401 (re-exports)
    PortfolioReport,
    ProjectResult,
    _looks_like_project,
    _readme_summary,
    _strip_md,
    _code_excerpt,
    _count_tests,
    _collect_dependencies,
    _run_command,
    _relpath,
    _substantive_packages,
    collect_project_facts,
    discover_projects,
    utc_stamp,
)
from ._portfolio_render import (  # noqa: F401 (re-exports)
    build_project_demo,
    collect_project_videos,
    render_portfolio,
    render_project,
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
    "collect_project_videos",
]

logger = get_logger(__name__)

# Implementation lives in :mod:`democreate._portfolio_facts` (discovery,
# facts, and the report dataclasses) and :mod:`democreate._portfolio_render`
# (rendering). Every name in ``__all__`` is re-exported here.
