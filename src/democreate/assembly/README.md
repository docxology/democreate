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
  (representative final `FrameState` for a per-chunk still), `audio_path`,
  `chunk_id`, `initial_state` (scene-opening state), and `actions` (the shared
  absolute-time scene event stream). `state_at_ms(t_ms, *, typing=True)` returns
  an independent scheduled snapshot, including partial code/camera/pointer motion
  over action durations; command output appears on completion. With `typing=False`,
  complete code appears at its trigger, never before it, while camera/pointer
  motion and command completion retain their durations. Replay never mutates
  shared actions or stored snapshots. `duration_ms` and `to_dict()` expose the
  narration window and its playback data.
- `Timeline` (dataclass): `entries`, `total_ms`, `fps`. Methods: `to_dict()`,
  `frame_count()` (= `round(total_ms/1000*fps)`), `entry_at_ms(t)` (returns the
  entry whose half-open `[start, end)` window contains `t`, else `None`).
- `build_timeline(demo, *, fps=None, wpm=150, trail_ms=0) -> Timeline` — **pure**.
  Walks scenes then chunks in order, producing one non-overlapping narration window
  per chunk. Uses `chunk.start_ms` when set (including lead/inter-chunk silence),
  otherwise cumulative timing. `chunk.playback_duration_ms(wpm)` uses measured
  audio duration when available, with word-count estimates only before synthesis.
  `total_ms` includes configured trailing silence without extending subtitle windows.
  Scene state persists across chunks; final still snapshots are distinct from
  scheduled animated playback. File contents survive close/reopen. Actions include:
  - `open_file` / `create_file` → editor frame with `file_path` + `code_lines`
  - `type_code` → string payloads continue literal text (including spaces,
    newlines and tabs); list payloads append complete `code_lines`
  - `highlight_lines` → `state.highlight_lines`
  - `run_command` / `print_output` → terminal frame with `terminal_lines`
  - `navigate` → browser frame with `url`
  - `zoom` / `pan` → `state.scale`; `move_mouse` → `state.cursor_xy`
  - chunk text is always carried as `state.caption`.
- `Compositor(abc.ABC)` — `compose(timeline, workspace) -> Path`.
- `ManifestCompositor` — **the default**. Writes
  `workspace.manifests/render_manifest.json` (= `Timeline.to_dict()`) and one
  captionless PNG per entry to `workspace.frames/frame_XXXX.png`. The required
  core synthetic renderer supplies those images; broken imports/decoding fail,
  rather than silently substituting placeholders. HTML cue text remains separate.
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

Cue timing uses each chunk's synced `start_ms` and measured playback duration when
present, otherwise cumulative word-count estimates. Synced silence remains intact.

### `effects.py` — pure Pillow transforms

All size-preserving, deterministic, Pillow-only:

- `fade(image, alpha)` — toward black over `alpha` 0..1.
- `crossfade(a, b, t)` — `Image.blend` (resizes `b` to `a` if needed).
- `highlight_box(image, box, *, color=(255,214,0), width=4)`.
- `lower_third(image, text, *, height=120)` — translucent caption band.

### `animator.py` — animated frame synthesis

Re-samples scene events onto a fixed frame rate: absolute action timestamps gate
visibility and action durations control typing/camera/pointer progress. Optional
waveform, cursor, scene transitions and Ken Burns overlays use pure Pillow. Input
frames and scheduled renders retain only active/previous images, not typing history.

- `AnimationConfig` (dataclass): the per-render animation parameters
  (`from_video(video, theme, audio)` builds it from a `RenderConfig`).
- `chunk_timing(...)`, `active_index_at(...)` — pure timeline math.
- `frame_hold_durations(clips, *, lead_ms=0, gap_ms=0, trail_ms=0)` — static
  frame holds aligned to spoken starts, preserving every configured pause and
  the complete voiceover duration. First hold includes lead; gaps precede the
  next frame, and the last hold includes trail.
- `render_animation_frames(frame_paths, clips, voiceover, out_dir, *, …,
  timeline_entries=None)` — emit the animated frame sequence (the input to
  `encode_frame_sequence`). Pass `timeline.entries` for scheduled playback.
  `AnimationConfig.typing` (from `video.typing`) controls character interpolation
  in scheduled playback: disabling it shows complete code at the action timestamp,
  preserving trigger visibility and all non-code action durations.
  Direct `frame_states`-only callers retain chunk-wide typing as a separate mode.
  `draw_captions` controls text drawn from re-rendered states; the pipeline passes
  false and burns only an explicitly requested SRT. Pre-baked caller raster
  input cannot have its caption pixels removed by this switch.
  Positive integer fps and nonnegative integer lead/gap/trail are validated both
  at config construction and render time.

### `audio.py` — voiceover assembly

Pure WAV concatenation plus guarded ffmpeg post-processing:

- `write_silence`, `concat_with_gaps` (lead/gap/trail silence), `measure_duration_ms`
  — stdlib `wave` only.
- `normalize_audio`, `apply_fade`, `ffmpeg_audio_available` — ffmpeg loudnorm/fade.
  An absent binary raises `BackendUnavailableError`; unsuccessful processing
  raises `RenderError` so callers can retain their valid raw/unfaded WAV.

## Optional extras

| Backend | Extra | Install |
|---|---|---|
| `MoviePyCompositor` | `video` | `uv sync --extra video` |

Everything else (timeline, `ManifestCompositor`, captions, effects) needs no
extras.

## Tests

- `tests/assembly/test_compositor.py` (+ `test_compositor_extra.py`)
- `tests/assembly/test_captions.py`
- `tests/assembly/test_effects.py`
- `tests/assembly/test_audio.py`

Run them:

```sh
.venv/bin/python -m pytest tests/assembly/ -q
```
