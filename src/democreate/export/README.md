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
| `export_video(frame_paths, audio_path, out_path, *, fps=30)` | **guarded** | Runs the encode. Requires the native `ffmpeg` binary on `PATH`; otherwise raises `BackendUnavailableError("ffmpeg")`. Inputs must be contiguous ascending numbered paths in one directory; sparse, reordered, mixed-pattern, missing, and percent-containing paths are rejected. Output is bounded to the supplied frame count, never stale neighbors. |
| `encode_frame_sequence(frame_paths, audio_path, out_path, *, fps=15, captions=None, crf=18, preset="medium")` | **guarded** | Same exact numbered-input contract. `captions: Path \| None` burns the requested subtitle file at encoded frame times; `None` disables burn. Missing native subtitles/libass capability raises `RenderError`, never silently skips requested captions. |

### `interactive.py`
| Function | Kind | Notes |
|----------|------|-------|
| `build_timeline(demo)` | pure | Caption/chapter timeline from chunk `start_ms` and `playback_duration_ms()` (measured duration, estimate only before synthesis). Returns `{captions, chapters, total_ms}`. |
| `export_html_player(demo, timeline, out_path, *, frames_dir=None)` | pure (Jinja2) | Renders `templates/player.html.j2` into one self-contained, offline HTML file: title, click-to-seek chapter sidebar, caption track, vanilla-JS player. Optionally shows per-chunk frames. |

The player template embeds the captions/chapters as JSON inside a `<script>`
block. That JSON is emitted with a script-safe encoder (`<`, `>`, `&`, and the
U+2028/U+2029 line separators are escaped to `\uXXXX`) so it can never break out
of the script element or be mangled by HTML autoescaping.

Caption cues carry explicit `start_ms`/`end_ms` measured windows. The player
clears caption text during leading silence, inter-chunk gaps, and after each
cue's end, while a still frame may remain visible. Pipeline-supplied `total_ms`
may include trailing silence beyond the last caption.

### `formats.py`
| Function | Kind | Notes |
|----------|------|-------|
| `to_markdown(demo)` | pure | Readable transcript: H1 title, H2 per scene, narration + bulleted action list per chunk. |
| `to_json(demo, *, indent=2)` | pure | Passthrough to `Demo.to_json` (round-trips via `Demo.from_json`). |
| `to_chapters(demo)` | pure | `[{title, scene_id, start_ms}]` for players / YouTube descriptions. |
| `export_pdf(demo, out_path)` | **guarded** | Renders the transcript to PDF. Requires a Markdown→PDF engine (`weasyprint` / `markdown-pdf` / `reportlab`); otherwise raises `BackendUnavailableError("pdf", extra="docs")`. `to_markdown` is the always-available fallback. |

### `verify.py` — content verification
Content-asserts a rendered video so existence is never mistaken for content.
`VideoReport` (dataclass) + `verify_video(path, *, expected_width, expected_height,
min_duration_s)` parse `ffprobe`/`volumedetect` to assert a real video stream of
the expected size, an audio stream that is **not silent**, and a sampled frame that
is **not black**. `parse_ffprobe` is the pure parser.

### `chapters.py` — chapter markers
`write_chapters`, `to_youtube_chapters`, `to_ffmetadata`, `embed_chapters`, and
`measured_chapters` (chapter starts from the *measured* audio timeline) — emit a
YouTube chapter file and embed one chapter marker per scene into the MP4.

### `metadata.py` — container tags
`build_tags`/`embed_tags` write MP4 container metadata (`title`/`artist`/`comment`,
readable by players and `ffprobe`); `ffmpeg_metadata_args`/`to_ffmetadata` are the
pure helpers.

### `overlay.py` — on-screen provenance bars
Pure Pillow drawing of the top/bottom metadata bars (author · source · running
clock · watermark): `OverlayInfo`, `draw_header`, `draw_footer`, `format_clock`,
`from_metadata_config`.

### `poster.py` — poster + GIF
`render_poster(demo, out, …)` renders a title/thumbnail frame; `demo_to_gif`
exports an animated GIF preview of a demo's frames.

### `stego.py` — steganographic provenance
LSB steganography in lossless PNG sidecars: `build_provenance`/`embed_provenance`
write an **unsigned, self-asserted content association**, not author or image
authentication. `verify_provenance` compares stable authored content (including
scene context, fps, and demo/chunk voices), excluding transient audio paths and
timing. Copied payloads and carrier-pixel edits preserving hidden bits can still
match. Operational `poster_signed` filenames are not cryptographic guarantees.
`capacity_bytes`/`embed`/`extract` are the low-level primitives.

## Optional extras

| Capability | Upgraded by extra | Install |
|------------|-------------------|---------|
| `export_video` MP4 encode | system `ffmpeg` binary; the `video` extra supplies Python-side helpers, not the binary | install `ffmpeg` (`brew install ffmpeg`, `apt-get install ffmpeg`) |
| `export_pdf` | a Markdown→PDF engine (`weasyprint` etc.) | `uv sync --extra docs` |

All other functions need nothing beyond the core install.

## Tests

`tests/export/test_*.py` — one per module (`video`, `interactive`, `formats`,
`chapters`, `metadata`, `overlay`, `poster`, `stego`, `verify`) — real computation
on real temp files, no mocks. Guarded backends are covered by asserting the
`BackendUnavailableError` path.
