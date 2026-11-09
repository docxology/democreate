# `democreate.export`: preview bundles, encoded media and unsigned metadata

Turns a Demo and rendered media into captions/transcripts, JSON, chapters,
posters/GIFs and a timed HTML image preview. HTML embeds its controls/cue data,
not PNG bytes or synthesized audio; keep sibling frame files when sharing it.
Real MP4 encode/verify/container operations need native ffmpeg/ffprobe; PDF
generation needs WeasyPrint. Import safety is not backend readiness. See
[backends](../../../docs/backends.md) and [provenance](../../../docs/provenance.md).

## Modules

### `video.py`
| Function | Kind | Notes |
|----------|------|-------|
| `build_ffmpeg_command(frames_glob, audio_path, out_path, *, fps=30)` | pure | Builds (never runs) the `ffmpeg` argv: `image2` input, optional audio mux, `libx264` / `yuv420p`. Returns `list[str]`. |
| `frames_to_gif(frame_paths, out_path, *, fps=10)` | core Pillow I/O | Loads frames and writes an animated looping GIF; no ffmpeg required. |
| `export_video(frame_paths, audio_path, out_path, *, fps=30)` | **guarded** | Runs the encode. Requires the native `ffmpeg` binary on `PATH`; otherwise raises `BackendUnavailableError("ffmpeg")`. Inputs must be contiguous ascending numbered paths in one directory; sparse, reordered, mixed-pattern, missing, and percent-containing paths are rejected. Output is bounded to the supplied frame count, never stale neighbors. |
| `encode_frame_sequence(frame_paths, audio_path, out_path, *, fps=15, captions=None, crf=18, preset="medium")` | **guarded** | Same exact numbered-input contract. `captions: Path \| None` burns the requested subtitle file at encoded frame times; `None` disables burn. Missing native subtitles/libass capability raises `RenderError`, never silently skips requested captions. |

Native encoders and tag/chapter remuxers stage each attempt in a unique temporary
directory beside the requested destination, then replace that destination only
on native success. Failure preserves its previous bytes and removes only that
attempt's scratch (including concat scripts). This is not a pipeline transaction:
`verify=False` remains supported, and a completed encode rejected by later content
verification remains available at the requested path for diagnosis.

### `interactive.py`
| Function | Kind | Notes |
|----------|------|-------|
| `build_timeline(demo)` | pure | Caption/chapter timeline from chunk `start_ms` and `playback_duration_ms()` (measured duration, estimate only before synthesis). Returns `{captions, chapters, total_ms}`. |
| `export_html_player(demo, timeline, out_path, *, frames_dir=None)` | Jinja2 output | Offline navigation/cue HTML with optional sibling PNG references; timed image preview, not synthesized-audio playback or a single embedded-media file. |

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
| `to_json(demo, *, indent=2, relative_to=None)` | pure | Serializes a Demo; optional workspace-relative path normalization for a resolved bundle. |
| `to_chapters(demo)` | pure | `[{title, scene_id, start_ms}]` for players / YouTube descriptions. |
| `export_pdf(demo, out_path)` | **guarded** | Styled transcript PDF via WeasyPrint; absent engine raises `BackendUnavailableError("pdf", extra="docs")`. Markdown remains core. |

### `verify.py` — content verification
Content-asserts a rendered video so existence is never mistaken for content.
`VideoReport` (dataclass) + `verify_video(path, *, expected_width, expected_height,
min_duration_s)` parse `ffprobe`/`volumedetect` to assert a real video stream of
the expected size, non-silent audio, and a nonblank frame sampled inside the
measured video interval (including subsecond videos). The volume pass strictly
decodes all video/audio streams once: decode failures or missing measurements
fail closed. `check_content=False` remains structural-only. `parse_ffprobe` is
the pure parser.

### `chapters.py` — chapter markers
`write_chapters`, `to_youtube_chapters`, `to_ffmetadata`, `embed_chapters`, and
`measured_chapters` (chapter starts from the *measured* audio timeline) — emit a
YouTube chapter file and embed one chapter marker per scene into the MP4.

### `metadata.py` — container tags
`build_tags`/`embed_tags` write MP4 container metadata (`title`/`artist`/`comment`,
readable by players and `ffprobe`); `ffmpeg_metadata_args`/`to_ffmetadata` are the
pure helpers.

Both remuxers explicitly copy every source video, audio and subtitle stream,
preserving language tags and encoded packet payloads. Chapter embedding replaces
chapters from the supplied metadata document and retains source global tags;
tag embedding retains source chapters. Data tracks are not copied: MP4 chapter
carriers are regenerated from the selected chapters, so chapters-then-tags and
replacement of existing chapters do not copy stale unsupported chapter tracks.

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
| `export_pdf` | WeasyPrint and its native dependencies | `uv sync --extra docs` |

All other functions need nothing beyond the core install.

## Tests

`tests/export/test_*.py` — one per module (`video`, `interactive`, `formats`,
`chapters`, `metadata`, `overlay`, `poster`, `stego`, `verify`) — real computation
on real temp files, no mocks. Guarded backends are covered by asserting the
`BackendUnavailableError` path.
