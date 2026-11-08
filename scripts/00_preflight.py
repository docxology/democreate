#!/usr/bin/env python
"""Preflight check: import core modules and report optional dependency presence.

Run from the project root::

    uv run python scripts/00_preflight.py

Exits non-zero if the core package cannot be imported.
"""

from __future__ import annotations

import importlib.util
import sys

CORE_MODULES = [
    "democreate",
    "democreate.schema",
    "democreate.media",
    "democreate.config",
    "democreate.pipeline",
    "democreate.cli",
    "democreate.narration.tts",
    "democreate.narration.sync",
    "democreate.capture.screen",
    "democreate.animation.zoom",
    "democreate.animation.waveform",
    "democreate.animation.diagram",
    "democreate.codebase.walker",
    "democreate.assembly.compositor",
    "democreate.assembly.animator",
    "democreate.assembly.audio",
    "democreate.export.interactive",
    "democreate.export.verify",
    "democreate.export.chapters",
    "democreate.export.poster",
    "democreate.export.stego",
    "democreate.export.overlay",
    "democreate.export.metadata",
    "democreate.paper.pdf",
    "democreate.paper.extract",
    "democreate.paper.structure",
    "democreate.paper.script",
    "democreate.narration.llm",
]

OPTIONAL_BACKENDS = [
    "kokoro_onnx",
    "whisper",
    "mss",
    "playwright",
    "manim",
    "moviepy",
    "tree_sitter",
    "pynput",
]


def main() -> int:
    """Import core modules and probe dependencies, not backend readiness."""
    ok = True
    for mod in CORE_MODULES:
        try:
            __import__(mod)
            print(f"  ok   {mod}")
        except Exception as exc:  # noqa: BLE001 - report all import failures
            ok = False
            print(f"  FAIL {mod}: {exc}")

    print("\nOptional dependencies (presence is not backend readiness):")
    for module in OPTIONAL_BACKENDS:
        present = importlib.util.find_spec(module) is not None
        print(f"  {module:14s} {'present' if present else 'absent'}")

    print("\ncore import:", "OK" if ok else "BROKEN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
