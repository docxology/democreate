#!/usr/bin/env python
"""Thin orchestrator: build a demo artifact end-to-end.

All logic lives in :mod:`democreate.pipeline`; this script is just a runnable
front door for the common case.

    uv run python scripts/generate_demo.py path/to/demo.json --output output
"""

from __future__ import annotations

import argparse
from pathlib import Path

from democreate.pipeline import build_demo
from democreate.project_paths import Workspace
from democreate.schema import Demo


def load_demo(path: Path) -> Demo:
    """Load a demo from JSON or YAML by extension."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return Demo.from_yaml(text)
    return Demo.from_json(text)


def main() -> None:
    """Parse args and run the pipeline."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("demo", type=Path, help="Path to a demo .json/.yaml")
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--no-strict", action="store_true")
    args = parser.parse_args()

    demo = load_demo(args.demo)
    result = build_demo(demo, Workspace(args.output), strict=not args.no_strict)
    print(result.summary())


if __name__ == "__main__":
    main()
