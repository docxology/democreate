#!/usr/bin/env python
"""Preflight check: confirm the package imports and report backend availability.

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
    ("kokoro_onnx", "tts"),
    ("whisper", "whisper"),
    ("mss", "capture"),
    ("playwright", "browser"),
    ("manim", "animation"),
    ("moviepy", "video"),
    ("tree_sitter", "codebase"),
    ("pynput", "replay"),
]


def main() -> int:
    """Import core modules and print a backend availability report."""
    ok = True
    for mod in CORE_MODULES:
        try:
            __import__(mod)
            print(f"  ok   {mod}")
        except Exception as exc:  # noqa: BLE001 - report all import failures
            ok = False
            print(f"  FAIL {mod}: {exc}")

    print("\nOptional backends:")
    for module, extra in OPTIONAL_BACKENDS:
        present = importlib.util.find_spec(module) is not None
        state = "installed" if present else f"default (uv sync --extra {extra})"
        print(f"  {module:14s} {state}")

    print("\ncore import:", "OK" if ok else "BROKEN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
