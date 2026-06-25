# `democreate.assembly`

The assembly subsystem turns a declarative `Demo` into rendered output. It owns
the **timeline** (the pure, central data structure that pairs absolute time
windows with renderable frame states), the **compositor backends** that render a
timeline, the **caption formatters**, and a small set of **image effects**.

Everything here runs on the core dependencies (`pillow`, `pyyaml`, …) except the
guarded legacy `MoviePyCompositor` adapter slot. The default path is fully
deterministic and import-safe.

## Modules

### `compositor.py` — timeline + compositors

The timeline is pure and central; building it never touches disk.

- `TimelineEntry` (dataclass): `index`, `start_ms`, `end_ms`, `state`
  (`FrameState`), `audio_path`, `chunk_id`; plus a `duration_ms` property and
  `to_dict()`.
- `Timeline` (dataclass): `entries`, `total_ms`, `fps`. Methods: `to_dict()`,
  `frame_count()` (= `round(total_ms/1000*fps)`), `entry_at_ms(t)` (returns the
  entry whose half-open `[start, end)` window contains `t`, else `None`).
- `build_timeline(demo, *, fps=None, wpm=150) -> Timeline` — **pure**. Walks
  scenes then chunks in order, producing one gap-free, non-overlapping
  `TimelineEntry` per chunk. Uses `chunk.start_ms` when set (post-sync) else a
  cumulative estimate from `estimated_duration_ms(wpm)`. Each entry's
  `FrameState` reflects the scene kind and the chunk's actions:
  - `open_file` / `create_file` → editor frame with `file_path` + `code_lines`
  - `type_code` → appends `code_lines`
  - `highlight_lines` → `state.highlight_lines`
  - `run_command` / `print_output` → terminal frame with `terminal_lines`
  - `navigate` → browser frame with `url`
  - `zoom` / `pan` → `state.scale`; `move_mouse` → `state.cursor_xy`
  - chunk text is always carried as `state.caption`.
- `Compositor(abc.ABC)` — `compose(timeline, workspace) -> Path`.
- `ManifestCompositor` — **the default**. Writes
  `workspace.manifests/render_manifest.json` (= `Timeline.to_dict()`) and one
  PNG per entry to `workspace.frames/frame_XXXX.png`. Frame rendering delegates
  to `democreate.capture.screen.render_frame` when importable; otherwise a
  built-in Pillow placeholder renderer keeps the default path working with only
  core deps.
- `MoviePyCompositor` — guarded legacy video adapter slot. Raises
  `BackendUnavailableError("moviepy", extra="video")` when MoviePy is absent;
  if MoviePy is present, it still raises `NotImplementedError` until real
  assembly is wired.

### `captions.py` — pure subtitle formatting

- `to_srt(demo, *, wpm=150)` — SubRip, `HH:MM:SS,mmm`, one cue per chunk.
- `to_vtt(demo, *, wpm=150)` — WebVTT with header, `HH:MM:SS.mmm`.
- `to_ass(demo, *, wpm=150)` — minimal valid ASS with `[Script Info]`,
  `[V4+ Styles]`, `[Events]`.
- `word_timestamps_to_srt(words)` — karaoke-granularity SRT, one cue per word.

Cue timing uses each chunk's synced `start_ms` when present, else a gap-free
cumulative estimate.

### `effects.py` — pure Pillow transforms

All size-preserving, deterministic, Pillow-only:

- `fade(image, alpha)` — toward black over `alpha` 0..1.
- `crossfade(a, b, t)` — `Image.blend` (resizes `b` to `a` if needed).
- `highlight_box(image, box, *, color=(255,214,0), width=4)`.
- `lower_third(image, text, *, height=120)` — translucent caption band.

### `animator.py` — animated frame synthesis

Re-samples the still per-chunk frames onto a fixed frame rate with motion: the
moving speech waveform + playhead, the top-edge progress line, character-by-character
code typing, the animated cursor, scene transitions, and Ken Burns. Pure Pillow.

- `AnimationConfig` (dataclass): the per-render animation parameters
  (`from_video(video, theme, audio)` builds it from a `RenderConfig`).
- `chunk_timing(...)`, `active_index_at(...)` — pure timeline math.
- `render_animation_frames(frame_paths, clips, voiceover, out_dir, *, …)` — emit the
  animated frame sequence (the input to `encode_frame_sequence`).

### `audio.py` — voiceover assembly

Pure WAV concatenation plus guarded ffmpeg post-processing:

- `write_silence`, `concat_with_gaps` (lead/gap/trail silence), `measure_duration_ms`
  — stdlib `wave` only.
- `normalize_audio`, `apply_fade`, `ffmpeg_audio_available` — ffmpeg loudnorm/fade,
  applied only when ffmpeg is present (skipped gracefully otherwise).

## Optional extras

| Backend | Extra | Install |
|---|---|---|
| `MoviePyCompositor` | `video` | `uv sync --extra video` |

Everything else (timeline, `ManifestCompositor`, captions, effects) needs no
extras.

## Tests

- `tests/assembly/test_compositor.py`
- `tests/assembly/test_captions.py`
- `tests/assembly/test_effects.py`

Run them:

```sh
.venv/bin/python -m pytest tests/assembly/test_compositor.py \
  tests/assembly/test_captions.py tests/assembly/test_effects.py -q
```
