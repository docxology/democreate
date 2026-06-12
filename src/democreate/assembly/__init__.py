"""Assembly subsystem — timeline build, compositors, captions, and effects.

This package turns a declarative :class:`~democreate.schema.Demo` into rendered
output. Its pieces are:

* :mod:`~democreate.assembly.compositor` — the pure :class:`Timeline` data
  structure, the :func:`build_timeline` walker, and the compositor backends
  (deterministic :class:`ManifestCompositor` default; guarded legacy
  :class:`MoviePyCompositor` slot behind the ``video`` extra).
* :mod:`~democreate.assembly.captions` — pure SRT / WebVTT / ASS subtitle
  formatting, plus a word-level karaoke SRT helper.
* :mod:`~democreate.assembly.effects` — pure Pillow transforms (fade, crossfade,
  highlight box, lower third).

Everything except :class:`MoviePyCompositor` runs with only the core
dependencies, which keeps the whole subsystem import-safe and fully testable.
"""

from __future__ import annotations

from .captions import to_ass, to_srt, to_vtt, word_timestamps_to_srt
from .compositor import (
    Compositor,
    ManifestCompositor,
    MoviePyCompositor,
    Timeline,
    TimelineEntry,
    build_timeline,
)
from .effects import crossfade, fade, highlight_box, lower_third

__all__ = [
    # compositor
    "TimelineEntry",
    "Timeline",
    "build_timeline",
    "Compositor",
    "ManifestCompositor",
    "MoviePyCompositor",
    # captions
    "to_srt",
    "to_vtt",
    "to_ass",
    "word_timestamps_to_srt",
    # effects
    "fade",
    "crossfade",
    "highlight_box",
    "lower_third",
]
