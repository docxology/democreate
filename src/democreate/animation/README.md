# democreate.animation

Visual primitives for demo frames: syntax-highlighted code rendering,
cursor-following zoom/pan math, and manim scene specs.

Everything except the real manim render runs on **core dependencies only**
(`rich`, `pillow`) and is fully deterministic — no I/O, no randomness, no
network — so it is import-safe and unit-testable without any heavy backend.

## Modules

### `highlights.py` — code → SVG / text / image
Pure syntax highlighting built on `rich` (a core dep).

| Function | Returns | Notes |
| --- | --- | --- |
| `highlight_to_svg(code, *, language="python", theme="monokai", line_numbers=True)` | `str` | Vector highlight via `rich` record console + `export_svg`. Always contains `<svg`. |
| `highlight_to_text(code, *, language="python")` | `str` | Flattened plain-text rendering (line numbers included). |
| `render_code_image(code, *, language="python", size=(1280,720), highlight_lines=())` | `PIL.Image.Image` | Raster code frame on a fixed character grid with a line-number gutter and highlighted-line background bands. Byte-stable across machines (fixed cell size, not host-font metrics). |

### `zoom.py` — cursor-following zoom/pan
Pure math plus one Pillow op.

| Symbol | Purpose |
| --- | --- |
| `linear(t)`, `ease_in_out_quad(t)`, `ease_in_out_cubic(t)` | Easing curves mapping `t∈[0,1] → [0,1]` (inputs clamped). |
| `ZoomKeyframe(t_ms, center_x, center_y, scale)` | Camera state at one instant. |
| `compute_zoom_path(cursor_points, frame_size, *, zoom=1.6, hold_ms=400)` | Build a time-sorted keyframe track that zooms toward each `(t_ms, x, y)` cursor point and eases back out. Every `scale >= 1`. |
| `interpolate(keyframes, t_ms, *, easing=ease_in_out_cubic)` | Sample camera state at an arbitrary time; clamps outside the track. |
| `apply_zoom(image, kf)` | Crop a `1/scale` region around the keyframe center and resize back to the original size (`scale<=1` is identity). |

### `manim_scenes.py` — manim scene specs
| Function | Returns | Notes |
| --- | --- | --- |
| `build_code_scene_spec(code, *, title="", language="python")` | `dict` | **Pure**, JSON-serializable line-by-line reveal description (title, code, language, ordered `steps` with `start_ms`/`duration_ms`, `total_duration_ms`). No manim required. |
| `render_manim_scene(spec, out_path)` | `Path` | **Guarded** real render. Raises `BackendUnavailableError("manim", extra="animation")` when manim is absent. Marked `# pragma: no cover`. |

### `fonts.py` — scaled TrueType font resolution
Pure font loading/scaling on Pillow (a core dep). Resolves a usable TrueType face
and scales it to the frame height so type stays crisp at any resolution
(`load_font` / `scaled_font` / font-path resolution helpers), falling back to
`ImageFont.load_default()` when no system face is found.

### `waveform.py` — speech-waveform scrubber
Pure envelope computation + drawing for the moving speech waveform overlaid on
animated renders: compute a normalized amplitude envelope from a WAV and draw the
waveform strip with a sweeping playhead locked to audio progress
(`compute_envelope` / `draw_waveform` / `render_waveform_strip`).

### `diagram.py` — architecture diagram image
Pure Pillow rendering of a labelled, columned architecture diagram used as a
full-frame scene background. `DiagramNode(label, sublabels=[])` is one box;
`render_architecture_diagram(size, *, title, columns, …) -> Image` lays out
columns of nodes; a helper renders DemoCreate's own architecture image.

## Optional extras

| Backend | Function | Upgrade extra | Install |
| --- | --- | --- | --- |
| manim | `render_manim_scene` | `animation` | `uv sync --extra animation` |

`highlights.py` and `zoom.py` need no extras.

## Determinism

`render_code_image` uses a fixed character cell (`_CELL_W`/`_CELL_H`) and fixed
colors rather than the host font's metrics or a theme, so byte output is stable
across machines. All zoom math is closed-form; `apply_zoom` is the only Pillow
resample and preserves the input image size exactly.
