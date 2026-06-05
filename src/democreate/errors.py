"""Exception hierarchy for DemoCreate.

All recoverable failures raise a subclass of :class:`DemoCreateError`, so callers
can ``except DemoCreateError`` to catch anything the package raises on purpose.
Optional-backend gaps raise :class:`BackendUnavailableError`, which carries the
name of the missing extra so the message can tell the user exactly what to
``uv add`` / ``pip install``.
"""

from __future__ import annotations

__all__ = [
    "DemoCreateError",
    "SchemaValidationError",
    "BackendUnavailableError",
    "RenderError",
    "SyncError",
    "CaptureError",
]


class DemoCreateError(Exception):
    """Base class for every error DemoCreate raises deliberately."""


class SchemaValidationError(DemoCreateError):
    """A :class:`~democreate.schema.Demo` failed structural validation.

    Attributes:
        problems: The list of human-readable problems returned by ``validate()``.
    """

    def __init__(self, problems: list[str]) -> None:
        self.problems = list(problems)
        joined = "; ".join(self.problems) if self.problems else "unknown problem"
        super().__init__(f"demo failed validation: {joined}")


class BackendUnavailableError(DemoCreateError):
    """A requested optional backend is not installed.

    Attributes:
        backend: Human name of the backend (e.g. ``"kokoro"``).
        extra: The pyproject optional-dependency extra that provides it
            (e.g. ``"tts"``), used to build an actionable install hint.
    """

    def __init__(self, backend: str, extra: str | None = None) -> None:
        self.backend = backend
        self.extra = extra
        hint = (
            f" — install it with `uv sync --extra {extra}`"
            if extra
            else ""
        )
        super().__init__(f"backend {backend!r} is unavailable{hint}")


class RenderError(DemoCreateError):
    """A frame, video, or export render step failed."""


class SyncError(DemoCreateError):
    """Audio/action synchronization failed (e.g. transcription mismatch)."""


class CaptureError(DemoCreateError):
    """A screen, browser, or terminal capture step failed."""
