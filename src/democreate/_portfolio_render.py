"""Portfolio rendering: one repository or a directory becomes summary videos.

Split out of :mod:`democreate.portfolio` (agent refactoring lane); the public
surface remains importable from :mod:`democreate.portfolio`.
"""

from __future__ import annotations

import html
import json
import shutil
from pathlib import Path
from typing import Any

from ._logging import get_logger
from .narration.project_summary import (
    ProjectFacts,
    generate_project_summary_demo,
)
from ._portfolio_facts import (
    PortfolioReport,
    ProjectResult,
    collect_project_facts,
    discover_projects,
    utc_stamp,
)
from ._portfolio_facts import PortfolioReport, ProjectResult

logger = get_logger(__name__)

def build_project_demo(
    repo: Path,
    workspace,
    *,
    config=None,
    max_modules: int = 6,
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
    max_modules: int = 6,
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


def collect_project_videos(
    output_root: Path, results: list[ProjectResult]
) -> Path:
    """Copy every rendered project video into a flat ``project_videos/`` folder.

    Each project keeps its own ``output_root/<name>/`` workspace; this gathers a
    copy of every successful summary MP4 into ``output_root/project_videos/`` so
    all videos — for any number of projects — sit in one browsable place. The
    folder is gitignored (it lives under ``output/`` and is also named in
    ``.gitignore``); failed projects are skipped.

    Returns:
        The ``project_videos`` directory path.
    """
    dest = Path(output_root) / "project_videos"
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0
    for result in results:
        if result.ok and result.video_path and Path(result.video_path).exists():
            shutil.copy2(result.video_path, dest / Path(result.video_path).name)
            copied += 1
    logger.info("collected %d project video(s) into %s", copied, dest)
    return dest


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
