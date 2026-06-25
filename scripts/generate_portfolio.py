#!/usr/bin/env python
"""Thin orchestrator: render a timestamped summary video per project in a folder.

All logic lives in :mod:`democreate.portfolio`; this script is a runnable front
door for the common case — a directory of repositories in, an ``output/<name>/``
folder per project out, plus a portfolio index.

    uv run python scripts/generate_portfolio.py ~/Documents/GitHub/HumOS/projects \
        --output output --resolution 1080p --voice Samantha --max-projects 3
"""

from __future__ import annotations

import argparse
from pathlib import Path

from democreate.config import RenderConfig
from democreate.portfolio import render_portfolio


def main() -> None:
    """Parse args and run the portfolio render."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("projects_dir", type=Path, help="Directory of project subdirectories")
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--theme", default="noir")
    parser.add_argument("--resolution", default="1080p")
    parser.add_argument("--voice", default="")
    parser.add_argument("--tts", default="system")
    parser.add_argument("--max-projects", type=int, default=0)
    parser.add_argument("--max-modules", type=int, default=3)
    parser.add_argument("--skip", default="")
    args = parser.parse_args()

    cfg = RenderConfig.preset(args.theme)
    cfg.set_resolution(args.resolution)
    if args.voice:
        cfg.audio.voice = args.voice
    cfg.audio.backend = args.tts
    skip = tuple(s.strip() for s in args.skip.split(",") if s.strip())

    report = render_portfolio(
        args.projects_dir,
        args.output,
        config=cfg,
        tts=cfg.audio.backend,
        voice=cfg.audio.voice,
        max_projects=args.max_projects,
        max_modules=args.max_modules,
        skip=skip,
    )
    print(f"{report.ok_count}/{len(report.results)} rendered → {report.index_json}")


if __name__ == "__main__":
    main()
