"""Attempt-local staging for native media publication."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

__all__: list[str] = []


@contextmanager
def _atomic_output(destination: Path) -> Iterator[Path]:
    """Publish a same-filesystem staged file only after the caller succeeds."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=destination.parent, prefix=".democreate-") as directory:
        staged = Path(directory) / destination.name
        yield staged
        staged.replace(destination)
