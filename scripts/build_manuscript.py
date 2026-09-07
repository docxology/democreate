#!/usr/bin/env python
"""Build the DemoCreate manuscript PDF from its declarative ``config.yaml``.

Thin orchestrator: all gate + build logic (config load, citation/figure gates,
Pandoc invocation, engine discovery) lives in :mod:`democreate.manuscript`.
This script only parses arguments, bootstraps the repo paths, and delegates.

    uv run python scripts/build_manuscript.py            # build docs/manuscript/output/*.pdf
    uv run python scripts/build_manuscript.py --check     # gates only, no PDF
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from democreate.manuscript import build_manuscript

_REPO = Path(__file__).resolve().parents[1]
_MANUSCRIPT = _REPO / "docs" / "manuscript"


def main() -> int:
    """Parse args and delegate to :func:`democreate.manuscript.build_manuscript`."""
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", type=Path, default=_MANUSCRIPT / "config.yaml")
    ap.add_argument("--check", action="store_true",
                    help="run the citation + figure gates only; do not build the PDF")
    ap.add_argument("-o", "--output", type=Path,
                    default=_MANUSCRIPT / "output" / "democreate_manuscript.pdf")
    args = ap.parse_args()
    return build_manuscript(
        config=args.config,
        manuscript_dir=_MANUSCRIPT,
        output=args.output,
        check=args.check,
    )


if __name__ == "__main__":
    sys.exit(main())
