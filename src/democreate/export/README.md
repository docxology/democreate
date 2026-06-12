# `democreate.export`

Turns a `Demo` (plus its rendered frames and audio) into shareable deliverables:
video/GIF, a self-contained interactive HTML player, and document formats
(Markdown transcript, JSON, chapter list, PDF).

Everything here runs on the **core dependencies only** (`pyyaml`, `typer`,
`rich`, `jinja2`, `pillow`) except two explicitly guarded paths — actual MP4
encoding and PDF generation — which require an external binary / engine.

## Modules

### `video.py`
| Function | Kind | Notes |
|----------|------|-------|
| `build_ffmpeg_command(frames_glob, audio_path, out_path, *, fps=30)` | pure | Builds (never runs) the `ffmpeg` argv: `image2` input, optional audio mux, `libx264` / `yuv420p`. Returns `list[str]`. |
| `frames_to_gif(frame_paths, out_path, *, fps=10)` | pure (Pillow) | Loads frames and writes an animated, looping GIF. Returns the path. |
| `export_video(frame_paths, audio_path, out_path, *, fps=30)` | **guarded** | Runs the encode. Requires the `ffmpeg` binary on `PATH`; otherwise raises `BackendUnavailableError("ffmpeg", extra="video")`. |

### `interactive.py`
| Function | Kind | Notes |
|----------|------|-------|
| `build_timeline(demo)` | pure | Deterministic caption/chapter timeline from chunk `start_ms` (or estimated durations). Returns `{captions, chapters, total_ms}`. |
| `export_html_player(demo, timeline, out_path, *, frames_dir=None)` | pure (Jinja2) | Renders `templates/player.html.j2` into one self-contained, offline HTML file: title, click-to-seek chapter sidebar, caption track, vanilla-JS player. Optionally shows per-chunk frames. |

The player template embeds the captions/chapters as JSON inside a `<script>`
block. That JSON is emitted with a script-safe encoder (`<`, `>`, `&`, and the
U+2028/U+2029 line separators are escaped to `\uXXXX`) so it can never break out
of the script element or be mangled by HTML autoescaping.

### `formats.py`
| Function | Kind | Notes |
|----------|------|-------|
| `to_markdown(demo)` | pure | Readable transcript: H1 title, H2 per scene, narration + bulleted action list per chunk. |
| `to_json(demo, *, indent=2)` | pure | Passthrough to `Demo.to_json` (round-trips via `Demo.from_json`). |
| `to_chapters(demo)` | pure | `[{title, scene_id, start_ms}]` for players / YouTube descriptions. |
| `export_pdf(demo, out_path)` | **guarded** | Renders the transcript to PDF. Requires a Markdown→PDF engine (`weasyprint` / `markdown-pdf` / `reportlab`); otherwise raises `BackendUnavailableError("pdf", extra="docs")`. `to_markdown` is the always-available fallback. |

## Optional extras

| Capability | Upgraded by extra | Install |
|------------|-------------------|---------|
| `export_video` MP4 encode | system `ffmpeg` binary; the `video` extra supplies Python-side helpers, not the binary | install `ffmpeg` (`brew install ffmpeg`, `apt-get install ffmpeg`) |
| `export_pdf` | a Markdown→PDF engine (`weasyprint` etc.) | install an engine, e.g. `uv pip install weasyprint` |

All other functions need nothing beyond the core install.

## Tests

`tests/test_export_video.py`, `tests/test_export_interactive.py`,
`tests/test_export_formats.py` — real computation on real temp files, no mocks.
Guarded backends are covered by asserting the `BackendUnavailableError` path.
