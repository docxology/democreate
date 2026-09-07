#!/usr/bin/env python3
"""Regenerate ``docs/api.md`` — a Markdown API reference for ``democreate``.

Thin orchestrator: the curated module inventory, introspection, and Markdown
rendering live in :mod:`democreate.api_docs`; this script only bootstraps the
repo paths and delegates. The output is fully deterministic for a given source
tree, so it can be checked in and regenerated as the API evolves.

Run it with the project virtualenv::

    .venv/bin/python scripts/generate_api_docs.py
"""

from __future__ import annotations

from pathlib import Path

from democreate.api_docs import generate

_ROOT = Path(__file__).resolve().parent.parent
_OUT = _ROOT / "docs" / "api.md"


def main() -> None:
    """Write ``docs/api.md`` from the live ``democreate`` package."""
    generate(_OUT)


if __name__ == "__main__":
    main()
