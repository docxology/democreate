"""Animation subsystem — syntax-highlight frames, cursor-zoom math, manim specs.

This package turns code and cursor data into the visual primitives a demo needs:

* :mod:`democreate.animation.highlights` — render syntax-highlighted code to SVG,
  plain text, or a Pillow still frame, using ``rich`` (a core dependency). Pure
  and deterministic.
* :mod:`democreate.animation.zoom` — cursor-following zoom/pan math (easing
  curves, keyframe computation, interpolation) plus a Pillow crop-and-resize
  applicator. Pure math + PIL.
* :mod:`democreate.animation.manim_scenes` — a pure, JSON-serializable description
  of a manim code-walkthrough scene, plus a guarded real-render entry point that
  requires the optional ``animation`` extra (manim).

Everything except :func:`~democreate.animation.manim_scenes.render_manim_scene`
runs with only the core dependencies (rich, pillow) and is fully testable.
"""

from __future__ import annotations

from .diagram import (
    DiagramNode,
    democreate_architecture_image,
    render_architecture_diagram,
)
from .fonts import load_font, resolve_font_path, scaled_font
from .highlights import highlight_to_svg, highlight_to_text, render_code_image
from .manim_scenes import build_code_scene_spec, render_manim_scene
from .waveform import compute_envelope, draw_waveform, render_waveform_strip
from .zoom import (
    ZoomKeyframe,
    apply_zoom,
    compute_zoom_path,
    ease_in_out_cubic,
    ease_in_out_quad,
    interpolate,
    linear,
)

__all__ = [
    # fonts
    "load_font",
    "scaled_font",
    "resolve_font_path",
    # highlights
    "highlight_to_svg",
    "highlight_to_text",
    "render_code_image",
    # waveform
    "compute_envelope",
    "draw_waveform",
    "render_waveform_strip",
    # diagram
    "DiagramNode",
    "render_architecture_diagram",
    "democreate_architecture_image",
    # zoom
    "ZoomKeyframe",
    "apply_zoom",
    "compute_zoom_path",
    "ease_in_out_cubic",
    "ease_in_out_quad",
    "interpolate",
    "linear",
    # manim
    "build_code_scene_spec",
    "render_manim_scene",
]
