#!/usr/bin/env python3
"""Generate ``docs/api.md`` — a Markdown API reference for ``democreate``.

This script imports the installed ``democreate`` package, walks a curated set of
public modules, and emits, for each, its public classes and functions together
with the one-line summary of their docstrings. It deliberately uses only the
standard library so it runs with the project's core dependencies alone.

Run it with the project virtualenv::

    .venv/bin/python scripts/generate_api_docs.py

The output is fully deterministic for a given source tree, so it can be checked
in and regenerated as the API evolves.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import is_dataclass
from pathlib import Path

import democreate

# Curated public surface: import-safe modules that make up the documented API.
# (Heavy/optional backends import cleanly on core deps, so listing them is fine.)
MODULES: list[str] = [
    "democreate",
    "democreate.schema",
    "democreate.config",
    "democreate.media",
    "democreate.pipeline",
    "democreate.project_paths",
    "democreate.errors",
    "democreate.cli",
    "democreate.narration.script",
    "democreate.narration.tts",
    "democreate.narration.sync",
    "democreate.narration.llm",
    "democreate.assembly.animator",
    "democreate.assembly.audio",
    "democreate.assembly.captions",
    "democreate.assembly.compositor",
    "democreate.capture.screen",
    "democreate.animation.waveform",
    "democreate.animation.diagram",
    "democreate.animation.fonts",
    "democreate.codebase.walker",
    "democreate.paper.extract",
    "democreate.paper.structure",
    "democreate.paper.script",
    "democreate.paper.pdf",
    "democreate.export.video",
    "democreate.export.verify",
    "democreate.export.chapters",
    "democreate.export.poster",
    "democreate.export.interactive",
    "democreate.export.formats",
]

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "api.md"


def summary(obj: object) -> str:
    """Return the first non-empty line of an object's docstring, or a placeholder."""
    doc = inspect.getdoc(obj) or ""
    for line in doc.splitlines():
        line = line.strip()
        if line:
            return line
    return "_(no docstring)_"


def is_public(name: str) -> bool:
    """Public names do not start with an underscore."""
    return not name.startswith("_")


def _clean_default(default: object) -> object:
    """Replace Typer ``Option``/``Argument`` sentinel defaults with clean values.

    Typer commands declare defaults as ``OptionInfo``/``ArgumentInfo`` objects
    whose ``repr`` is a non-deterministic memory address (e.g.
    ``<typer.models.OptionInfo object at 0x…>``). Rendering that into the API
    docs leaks object identities and breaks reproducibility. Detect those
    sentinels by module/class name (without importing typer, to keep this script
    stdlib-only) and surface the real default they carry instead.
    """
    cls = type(default)
    if cls.__module__.startswith("typer") or cls.__name__ in {
        "OptionInfo",
        "ArgumentInfo",
        "ParameterInfo",
    }:
        inner = getattr(default, "default", inspect.Parameter.empty)
        # Typer marks a required parameter with ``...`` (Ellipsis).
        if inner is ... or inner is inspect.Parameter.empty:
            return inspect.Parameter.empty
        return inner
    return default


def signature_of(obj: object) -> str:
    """Best-effort one-line signature; empty string if it cannot be introspected.

    Typer sentinel defaults are folded to their real values (or to "required")
    so the rendered signature is clean and deterministic.
    """
    try:
        sig = inspect.signature(obj)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    params = []
    changed = False
    for param in sig.parameters.values():
        cleaned = _clean_default(param.default)
        if cleaned is not param.default:
            changed = True
            param = param.replace(default=cleaned)
        params.append(param)
    if not changed:
        return str(sig)
    try:
        return str(sig.replace(parameters=params))
    except (TypeError, ValueError):
        return str(sig)


def members(module: object, kind: str) -> list[tuple[str, object]]:
    """Return sorted ``(name, obj)`` members of ``module`` that are defined in it.

    ``kind`` is ``"class"`` or ``"function"``. Re-exported names (defined in a
    different module) are skipped so each symbol is documented under its home
    module — except for the top-level ``democreate`` package, whose job *is* to
    re-export, where we keep everything in ``__all__``.
    """
    mod_name = getattr(module, "__name__", "")
    is_facade = mod_name == "democreate"
    exported = set(getattr(module, "__all__", []) or [])
    out: list[tuple[str, object]] = []
    for name, obj in inspect.getmembers(module):
        if not is_public(name):
            continue
        if kind == "class" and not inspect.isclass(obj):
            continue
        if kind == "function" and not inspect.isfunction(obj):
            continue
        home = getattr(obj, "__module__", "")
        if is_facade:
            if name not in exported:
                continue
        elif home != mod_name:
            continue
        out.append((name, obj))
    out.sort(key=lambda pair: pair[0])
    return out


def module_anchor(mod_name: str) -> str:
    """Return the stable Markdown anchor used for a documented module."""
    return mod_name.replace(".", "").replace("`", "")


def render_module(mod_name: str) -> str:
    """Render the Markdown section for a single module."""
    module = importlib.import_module(mod_name)
    lines: list[str] = [f"## `{mod_name}` {{#{module_anchor(mod_name)}}}", ""]
    lines.append(summary(module))
    lines.append("")

    classes = members(module, "class")
    functions = members(module, "function")

    if classes:
        lines.append("### Classes")
        lines.append("")
        for name, obj in classes:
            tag = " *(dataclass)*" if is_dataclass(obj) else ""
            lines.append(f"- **`{name}`**{tag} — {summary(obj)}")
            # Document public methods of the class (defined on the class itself).
            for mname, mobj in inspect.getmembers(obj, inspect.isfunction):
                if not is_public(mname):
                    continue
                if mobj.__qualname__.split(".")[0] != name:
                    continue
                lines.append(f"  - `{mname}{signature_of(mobj)}` — {summary(mobj)}")
        lines.append("")

    if functions:
        lines.append("### Functions")
        lines.append("")
        for name, obj in functions:
            lines.append(f"- **`{name}{signature_of(obj)}`** — {summary(obj)}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    """Write ``docs/api.md`` from the live ``democreate`` package."""
    header = [
        "# API reference",
        "",
        "> **Generated** by `scripts/generate_api_docs.py` from the live "
        f"`democreate` package (version `{democreate.__version__}`). "
        "Do not edit by hand — regenerate with "
        "`.venv/bin/python scripts/generate_api_docs.py`.",
        "",
        "This reference lists the public classes and functions of each documented "
        "module with the one-line summary of their docstring. For prose and "
        "examples, see the topic docs linked from [README.md](README.md); for the "
        "full contracts, read the source and its tests.",
        "",
        "## Modules",
        "",
    ]
    for mod_name in MODULES:
        header.append(f"- [`{mod_name}`](#{module_anchor(mod_name)})")
    header.append("")

    sections = [render_module(mod_name) for mod_name in MODULES]
    text = "\n".join(header) + "\n" + "\n".join(sections)
    if not text.endswith("\n"):
        text += "\n"
    OUT.write_text(text, encoding="utf-8")
    print(f"wrote {OUT} ({len(MODULES)} modules)")


if __name__ == "__main__":
    main()
