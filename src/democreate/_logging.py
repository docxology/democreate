"""Self-contained structured logging for DemoCreate.

The package depends on no external logging infrastructure; this thin wrapper over
the standard library gives every module a consistently-formatted logger via
``get_logger(__name__)``. Verbosity is controlled by the ``DEMOCREATE_LOG_LEVEL``
environment variable (default ``INFO``). A :func:`log_stage` context manager
times pipeline stages for the observability story.
"""

from __future__ import annotations

import logging
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager

__all__ = ["get_logger", "log_stage"]

_CONFIGURED = False
_DEFAULT_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"


def _configure_root() -> None:
    """Attach a single stream handler to the package root logger, once."""
    global _CONFIGURED
    if _CONFIGURED:
        return
    level_name = os.environ.get("DEMOCREATE_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger("democreate")
    root.setLevel(level)
    if not root.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
        root.addHandler(handler)
    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a logger namespaced under ``democreate``.

    Args:
        name: Usually ``__name__`` of the calling module.

    Returns:
        A configured :class:`logging.Logger`.
    """
    _configure_root()
    if name == "democreate" or name.startswith("democreate."):
        return logging.getLogger(name)
    return logging.getLogger(f"democreate.{name}")


@contextmanager
def log_stage(stage: str, logger: logging.Logger | None = None) -> Iterator[None]:
    """Time a named stage, logging start, success, and elapsed milliseconds.

    Args:
        stage: Human-readable stage label.
        logger: Logger to use; defaults to the package logger.

    Yields:
        Control to the wrapped block.
    """
    log = logger or get_logger("democreate")
    log.info("▶ %s", stage)
    start = time.perf_counter()
    try:
        yield
    except Exception:
        elapsed = (time.perf_counter() - start) * 1000
        log.error("✗ %s failed after %.0f ms", stage, elapsed)
        raise
    else:
        elapsed = (time.perf_counter() - start) * 1000
        log.info("✓ %s (%.0f ms)", stage, elapsed)
