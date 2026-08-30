"""Shared CLI helpers: console, validation, demo loading, config resolution.

Split out of :mod:`democreate.cli` (agent refactoring lane); every name remains
importable from :mod:`democreate.cli`.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from .schema import Demo

console = Console()

__all__ = [
    "console",
    "_validate_theme",
    "_validate_aspect",
    "_validate_resolution",
    "_load_demo",
    "_resolve_config",
]


def _validate_theme(value: str) -> str:
    """Return ``value`` when it is a known theme, else exit with a usage error."""
    from .config import THEMES

    if value in THEMES:
        return value
    valid = ", ".join(sorted(THEMES))
    typer.echo(f"unknown theme {value!r}; choose one of: {valid}")
    raise typer.Exit(code=2)


def _validate_aspect(value: str) -> str:
    """Return ``value`` when it is a known aspect ratio or empty."""
    from .config import ASPECTS

    if not value or value in ASPECTS:
        return value
    valid = ", ".join(sorted(ASPECTS))
    typer.echo(f"unknown aspect {value!r}; choose one of: {valid}")
    raise typer.Exit(code=2)


def _validate_resolution(value: str) -> str:
    """Return ``value`` when it is a known resolution tier or empty."""
    from .config import RESOLUTIONS

    if not value or value in RESOLUTIONS:
        return value
    valid = ", ".join(sorted(RESOLUTIONS))
    typer.echo(f"unknown resolution {value!r}; choose one of: {valid}")
    raise typer.Exit(code=2)


def _load_demo(path: Path) -> Demo:
    """Load a :class:`Demo` from a ``.json`` or ``.yaml`` file."""
    return Demo.from_file(path)


def _resolve_config(config_path: Path | None, theme: str, voice: str, tts: str):
    """Build a RenderConfig from a --config file or a --theme preset, with overrides."""
    from .config import RenderConfig

    cfg = RenderConfig.from_file(config_path) if config_path else RenderConfig.preset(theme)
    if voice:
        cfg.audio.voice = voice
    elif not config_path:
        cfg.audio.voice = ""
    if tts:
        cfg.audio.backend = tts
    return cfg
