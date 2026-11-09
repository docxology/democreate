# Video: scheduled animation, static holds and bounded media checks

`democreate render` uses measured narration clip windows and a scheduled action
stream. A spoken MP4 requires a usable real TTS plus ffmpeg/ffprobe; the default
silent backend is not spoken narration. Animated export uses a fixed
`animation_fps`, waveform/progress overlays and optional transitions. Word/action
positions remain heuristic estimates, not detected acoustic onsets. Contain
fitting does not prevent explicit camera zoom or overlays from hiding content.

The default theme is **noir**: near-black surfaces, bright-white text, and a
single refined red as the only chroma (the played waveform, the cursor, code
keywords, the section pill / heading rule, the line-highlight bar, and the
top-edge progress line). Type is **larger across every theme** for legibility on
video (title `0.094`, caption `0.038`, code autosize cap `0.034` of the frame
height). See [config.md](config.md#theme-presets) for all five presets.

The pipeline stage is `render_video()` in `pipeline.py`; the animation itself is
`render_animation_frames()` in `assembly/animator.py`; the encode is
`encode_frame_sequence()` in `export/video.py`.

## Shared clip timebase and frame rounding

The compositor emits one representative still per narration chunk.
`render_video` requires a one-to-one frame/clip count. Default animated rendering
replays action states on the measured clip timebase; explicitly selected custom
compositors retain their supplied raster content rather than being replaced by
the synthetic renderer. State metadata may still drive cursor overlays.

Clip windows and voiceover use the same configured lead/gap/trailing silence.
Encoded video is quantized to output frames; container/video/audio durations can
differ by a frame or codec padding. A shared planned timebase is not a measured
acoustic-alignment guarantee.

Padding is bound at build time; changing lead/gap/trail during export raises
`RenderError` before output writes. Rebuild rather than retiming only the audio.

The playback horizon remains narration-bounded. `WAIT`, explicit timestamps and
long action durations do not extend narration or guarantee their effects occur
inside an encoded scene. Keep intended effects inside that scene's playback
window; static representative stills are not evidence of animated reachability.
Terminal prompt/start and output/completion effects replay chronologically;
late output appends without rewriting earlier visible lines or switching away
from the currently active editor/browser surface.

## What the animator draws on each frame

For each instant, on top of the active chunk's base content frame:

- **Typing reveal** — for flagged editor chunks, the code is *re-rendered* with
  more characters revealed as the chunk plays, so it types itself in (see
  [Typing animation](#typing-animation) below).
- **Animated cursor** — an arrow cursor with a click ripple, where a chunk
  supplies a position (see [Animated cursor](#animated-cursor) below).
- **Speech waveform** — a waveform of the *whole* voiceover, drawn into the
  reserved bottom band (`WAVEFORM_BAND_FRAC` = 12% of frame height). The portion
  up to the current time is lit (`wave_played`) and a playhead sweeps across.
  The envelope is computed once from the voiceover WAV
  (`animation/waveform.py::compute_envelope`).
- **Progress bar** — a top-edge overlay (`y=0`), which can cover source pixels.
- **Ken Burns** (off by default) — optional zoom on flagged slide/background
  frames. Explicit camera actions are separate and can also crop editor content.
- **Scene crossfade** — at a scene boundary (the chunk's `scene_id` differs from
  the previous chunk's), the new frame fades in from the previous scene's frame
  over `transition_ms` (default 450 ms).

`pipeline._scene_meta()` computes the per-chunk `scene_ids` and `kenburns_flags`
the animator needs; `pipeline._typing_flags()` computes the per-chunk typing
flags, and `result.timeline` supplies the per-chunk `FrameState`s.

## Typing animation

Normal pipeline typing follows each `create_file` / `type_code` action's trigger
and `duration_ms`, not a fraction of the narration chunk. With `video.typing:
false`, complete code appears at its trigger while unrelated event durations
remain unchanged. A trigger is estimated from known text, not recognized speech.

For example, put this action in a chunk whose narration includes “example”:

```json
{"type": "type_code", "params": {"code": "print('hello')"},
 "trigger_word": "example", "duration_ms": 1200}
```

The high-level `video.typing_fraction` setting has been removed; old YAML is
rejected. The low-level `AnimationConfig.typing_fraction` remains applicable only
to snapshot-based calls without scheduled timeline entries. Explicit compositor
rasters are preserved and are not synthetically retyped.

## Animated cursor

When scheduled playback has a cursor position, the animator draws a scaled
arrow at that position. A scheduled CLICK starts a roughly 600 ms ripple;
snapshot-only calls use their chunk-start ripple convention. A starter without
cursor coordinates does not invent a visible pointer. `VideoConfig.cursor`
enables/disables the overlay; explicit compositor state can still supply it.
See [configuration](config.md).

## Ken Burns, off by default

The Ken Burns slow-zoom is **disabled by default** (`VideoConfig.ken_burns =
False`). It can push figure/diagram/page edges out of view. Base contain fitting
reduces that loss before motion, while typing, waveform, cursor and crossfades
provide other motion. Overlays and explicit camera actions may still hide pixels.
Enable Ken Burns explicitly (config
`video.ken_burns: true`) only when you accept the edge crop; the peak zoom is then
`ken_burns_zoom` (default `1.06`).

## Base layout and slide surfaces

Base fitting and bounded autosizing aid layout, not arbitrary-input guarantees;
see [layout limits](config.md#layout-limits-contain-fitting-and-bounded-code-autosizing).

- **Fit-contain backgrounds.** Base images are scaled proportionally into the
  content rectangle. Camera motion and overlays can still hide pixels.
- **Autosize code.** Font size is reduced within implementation limits; very long
  lines, dense code and unsupported glyphs can still overflow or lose detail.
  Inspect representative encoded frames instead of assuming universal no-crop
  or font-coverage guarantees.

The animator also renders two packed slide surfaces carried on the
[`FrameState`](schema.md#related-media-types): **bullet lists**
(`FrameState.bullets`, up to 6 distributed items) and **stat cards**
(`FrameState.stats`, up to 5 big-number `(value, label)` cards), both set from a
slide scene's `context["bullets"]` / `context["stats"]`. The showcase demo uses
both ([videos.md](videos.md)).

## Resolution and encode quality

The pipeline renders at the Demo's width/height. Explicit `render --resolution`
sets a named 16:9 tier on both config and Demo before composition; `--aspect`
then overrides geometry if also supplied. YAML dimensions alone do not resize
the authored Demo. Higher geometry re-renders scalable content but cannot recover
detail absent from a raster background. See [configuration](config.md).

| Tier | Size | Notes |
|------|------|-------|
| `720p` | `1280×720` | Smaller/faster. |
| `1080p` | `1920×1080` | The default. |
| `1440p` | `2560×1440` | QHD geometry. |
| `2160p` / `4k` | `3840×2160` | UHD / 4K. |

`--resolution` sets `cfg.video.width`/`height` (via `RenderConfig.set_resolution`)
and pushes the new geometry onto the demo so the whole pipeline renders at that
size. `--aspect` is the non-16:9 sibling (see [config.md](config.md)).

Encode quality is two `VideoConfig` knobs passed straight to ffmpeg by
`encode_frame_sequence` (animated path) and `assemble_video` (static path):

- **`crf`** (default `18`) — H.264 compression control. Lower values generally
  trade larger output for less compression; no perceptual-quality guarantee.
- **`preset`** (default `"medium"`) — the x264 speed/size tradeoff
  (`ultrafast` … `veryslow`); slower presets compress better at the same `crf`.

```bash
democreate render demo.json --resolution 2160p          # true 4K
# crf/preset are config-only (no CLI flag):
democreate config c.yaml && democreate render demo.json --config c.yaml
```

## On-screen metadata

When `MetadataConfig.header`/`footer` are enabled, the animator burns two slim,
translucent broadcast-style bars onto each frame (`_draw_overlays`, drawing via
`export/overlay.py`):

- **Header** (`draw_header`, off by default) — a thin ribbon just under the window
  chrome + progress bar (~6–10.5% of the frame height) with the demo **title** on
  the left and the current **section** on the right (in accent).
- **Footer** (`draw_footer`, **on by default**) — a strap at the very bottom edge
  (above the waveform band) carrying `author · source` (left), the URL, and — far
  right, in accent — a running **clock** (`format_clock`, e.g. `1:23 / 4:56`) and a
  persistent **watermark**.

Because these are burned into the pixels, they **survive the H.264 encode** — they
are the visible carrier of provenance, complementing the MP4 container tags and the
steganographic poster. Each bar is a no-op when its fields are empty. Set them with
`render --author/--watermark` or a `metadata:` config block; the full story is in
[provenance.md](provenance.md).

## Settings

All motion is governed by [`VideoConfig`](config.md) and surfaced as CLI flags
on `render`:

| Setting | Default | CLI flag | Effect |
|---------|---------|----------|--------|
| `animate` | `True` | `--animate / --no-animate` | Animated render vs static slideshow. |
| `animation_fps` | `15` | `--animation-fps` | Frame rate of the animated render. |
| `fps` | demo's `fps` | `--fps` | Static-render frame rate (`0` = demo default). |
| `waveform` | `True` | (config) | Draw the moving waveform band. |
| `progress_bar` | `True` | (config) | Draw the progress line at the absolute top edge (`y=0`). |
| `transitions` | `True` | (config) | Crossfade scene boundaries. |
| `transition_ms` | `450` | (config) | Crossfade duration. |
| `ken_burns` | `False` | (config) | Slow zoom on background/slide frames (off by default — zoom crops the edges). |
| `ken_burns_zoom` | `1.06` | (config) | Peak Ken Burns zoom factor (when enabled). |
| `typing` | `True` | (config) | Type editor code in character-by-character. |
| `cursor` | `True` | (config) | Draw the animated cursor + click ripple. |
| `width`/`height` | `1920`/`1080` | `--resolution` (16:9 tier) | Output size; everything scales to height. |
| `crf` | `18` | (config) | H.264 compression control; inspect the encoded result. |
| `preset` | `"medium"` | (config) | x264 speed/size tradeoff (`ultrafast`…`veryslow`). |

`AnimationConfig.from_video()` builds the animator's settings from a
`VideoConfig` plus the `Theme` (waveform/accent colors) and `AudioConfig`
(lead/gap/trail timing).

## The two render paths

- **Animated (default).** `render_animation_frames()` writes `anim_%05d.png`
  frames, then `encode_frame_sequence()` encodes them with the voiceover at
  `animation_fps`.
- **Static (`--no-animate`).** `assemble_video()` holds each still frame for its
  measured clip duration plus lead/gap/trail holds via the ffmpeg concat demuxer.
  It retains the previous still through a gap until the next spoken start;
  animated playback can show the upcoming chunk during that gap. Both paths
  burn SRT only when requested with `--captions` (requires libass); default base
  images contain no baked narration, so silence windows have no subtitle text.

Both paths require **`ffmpeg` on `PATH`** (no pip install needed); absence raises
`BackendUnavailableError` naming ffmpeg, with no fictitious pip extra.

## Verification

Every render is content-verified by default (`verify_video()` in
`export/verify.py`) — see [the `verify` command](cli.md#verify). It asserts a
real video stream of the expected size, an audio stream, **non-silent** audio
(ffmpeg `volumedetect` mean volume above a floor), and a **nonblank** sampled
frame (grayscale pixel variance above a floor). `render` exits non-zero if
verification fails. These checks do not establish intelligibility, scientific
accuracy, scene fidelity or acoustic synchronization. [Media identities](videos.md)
and the immutable [engineering receipt](release-0.8.0.md) separate identified
historical observations from future renders; no old duration proves this tree.

The existing volume pass strictly decodes every selected video/audio stream;
native decode errors or unavailable measurements fail closed without a duplicate
full decode. Frame sampling uses the video's midpoint timestamp, including short
and nonzero-start streams. Missing stream duration can fall back to container
duration; a failed sample is not a pass. Structural-only verification does not
decode content, but still requires a known positive duration even with minimum 0.

Each encode/remux stages beside its destination and replaces it only on native
success; a native failure preserves prior bytes. This is not a whole-pipeline
transaction: a completed MP4 rejected by subsequent verification remains at the
requested path for diagnosis, with a failed report/nonzero CLI status.

## See also

- [config.md](config.md) — `VideoConfig` (resolution + crf/preset) and `Theme` reference.
- [audio.md](audio.md) — the voiceover that drives the waveform + timing.
- [cli.md](cli.md) — `render` (`--resolution`/`--author`/`--watermark`) / `verify` options.
- [provenance.md](provenance.md) — the on-screen bars, container tags, and steganography.
- [architecture.md](architecture.md) — the full render-to-verify flow.
