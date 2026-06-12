# Animated video render

`democreate render` (and `democreate paper`) turn a built demo into a real HD
MP4 with a spoken voiceover. By default the render is **animated**, not a
slideshow: the still per-chunk frames are re-sampled onto a fixed
`animation_fps` and overlaid with motion — a character-by-character typing
reveal, an animated cursor, a moving speech waveform, a top-edge progress line,
and scene crossfades — that makes the video feel alive while staying perfectly
locked to the audio. (Ken Burns is available but **off by default**: a slow zoom
crops content off the frame edges, which the no-crop fit-contain layout exists to
prevent — see [below](#ken-burns-off-by-default).)

The default theme is **noir**: near-black surfaces, bright-white text, and a
single refined red as the only chroma (the played waveform, the cursor, code
keywords, the section pill / heading rule, the line-highlight bar, and the
top-edge progress line). Type is **larger across every theme** for legibility on
video (title `0.094`, caption `0.038`, code autosize cap `0.034` of the frame
height). See [config.md](config.md#theme-presets) for all five presets.

The pipeline stage is `render_video()` in `pipeline.py`; the animation itself is
`render_animation_frames()` in `assembly/animator.py`; the encode is
`encode_frame_sequence()` in `export/video.py`.

## Why frames stay locked to audio

The compositor emits exactly **one still frame per narration chunk** — correct
but static. `render_video` enforces a one-to-one frame↔clip count (mismatch is a
`RenderError`), then holds each frame for its clip's **measured** duration. The
concatenated voiceover shares the same timebase by construction, so there is no
drift. The animator re-samples this timeline onto `animation_fps`: every output
frame is a `1/fps` slice, which encodes cleanly with ffmpeg's `image2` demuxer.

`chunk_timing()` lays out per-chunk spoken `(start_ms, end_ms)` windows from the
measured clip durations, reserving the same `lead_ms` / `gap_ms` / `trail_ms`
silence that the voiceover uses (from [`AudioConfig`](audio.md)) — so the frame
timeline and the audio timeline match millisecond-for-millisecond.

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
- **Progress bar** — a thin progress line pinned to the **absolute top edge** of
  the frame (`y=0`, ~6 px) showing overall progress. It sits above all content so
  it never overlaps the picture; it previously sat ~58 px down and clipped the top
  of figures and diagrams. In the default **noir** theme it is drawn in the single
  red accent.
- **Ken Burns** (off by default) — when explicitly enabled, a slow center zoom on
  *flagged* frames only: slide scenes and any scene with a full-frame
  `background_image` (diagrams, screenshots, PDF pages). Code/terminal frames are
  never zoomed, where a drift would clip text. Peak zoom is `ken_burns_zoom`
  (default `1.06`). See [Ken Burns, off by default](#ken-burns-off-by-default).
- **Scene crossfade** — at a scene boundary (the chunk's `scene_id` differs from
  the previous chunk's), the new frame fades in from the previous scene's frame
  over `transition_ms` (default 450 ms).

`pipeline._scene_meta()` computes the per-chunk `scene_ids` and `kenburns_flags`
the animator needs; `pipeline._typing_flags()` computes the per-chunk typing
flags, and `result.timeline` supplies the per-chunk `FrameState`s.

## Typing animation

Instead of showing a code block all at once, the animator types it in
character-by-character. A chunk is flagged for typing when its scene is an
**editor** (`codebase`) view, it has **no full-frame background**, and it carries
a `type_code` or `create_file` action (`pipeline._typing_flags()`). For a flagged
chunk, `render_animation_frames()` re-renders that chunk's `FrameState` at a
progressively larger `cursor_typed` — pygments highlights the code as each
character appears — so the editor frame literally types the code in.

The reveal is paced by `typing_fraction` (default `0.7`): the code finishes
typing after the first ~70% of the chunk's spoken window, then holds for the
rest. Re-rendered states are cached by `(chunk index, characters typed)`, so the
same partially-typed frame is rendered once and reused. Typing requires the
per-chunk `FrameState`s (passed as `frame_states`); without them the animator
falls back to the static base frame.

Controlled by `VideoConfig.typing` / `typing_fraction` ([config.md](config.md));
typing is independent of Ken Burns (editor frames are never zoomed).

## Animated cursor

When a chunk's `FrameState` carries a `cursor_xy` position, the animator draws an
arrow cursor there (`_draw_cursor()`), scaled to the frame height. At the start of
the chunk's window a **click ripple** expands and fades out from the cursor over
~600 ms, drawing the eye to where the action happens. Cursor drawing is governed
by `VideoConfig.cursor` ([config.md](config.md)); chunks without a `cursor_xy`
simply draw no cursor.

## Ken Burns, off by default

The Ken Burns slow-zoom is **disabled by default** (`VideoConfig.ken_burns =
False`). Zooming a full-frame figure, diagram, or PDF page pushes its edges off
the frame — losing exactly the content a paper or architecture slide is there to
show. DemoCreate's default instead keeps every background **whole** via the
no-crop fit-contain layout (below) and gets its motion from typing, the moving
waveform, the cursor, and crossfades. Enable Ken Burns explicitly (config
`video.ken_burns: true`) only when you accept the edge crop; the peak zoom is then
`ken_burns_zoom` (default `1.06`).

## No-crop layout and slide surfaces

Two renderer invariants keep content intact at any resolution or aspect ratio
(see [config.md](config.md#layout-no-crop-fit-contain-autosize-code)):

- **Fit-contain backgrounds.** A full-frame `background_image` is scaled by
  `min(bw/sw, bh/sh)` (the *contain* fit) so the whole image sits inside the
  content band with a matte frame — never a cover-crop. The **top-edge** progress
  line (`y=0`) and the matte band mean the picture is never clipped by chrome.
- **Autosize code.** An editor frame picks the largest legible mono font that fits
  the *whole* code block (longest line for width, line count for height; cap
  `0.034 ×` frame height) — code never overflows or gets truncated at the right
  edge.

The animator also renders two packed slide surfaces carried on the
[`FrameState`](schema.md#related-media-types-media.py): **bullet lists**
(`FrameState.bullets`, up to 6 distributed items) and **stat cards**
(`FrameState.stats`, up to 5 big-number `(value, label)` cards), both set from a
slide scene's `context["bullets"]` / `context["stats"]`. The showcase demo uses
both ([videos.md](videos.md)).

## Resolution & quality

The render is sized by `VideoConfig.width`/`height`, and `render --resolution`
picks a named **16:9 tier** that sets both. Every visual element scales to the
frame **height**, so a higher tier is genuinely higher resolution — not a 1080p
render upscaled:

| Tier | Size | Notes |
|------|------|-------|
| `720p` | `1280×720` | Smaller/faster. |
| `1080p` | `1920×1080` | The default. |
| `1440p` | `2560×1440` | QHD (verified: produces a true `2560×1440` video). |
| `2160p` / `4k` | `3840×2160` | UHD / 4K. |

`--resolution` sets `cfg.video.width`/`height` (via `RenderConfig.set_resolution`)
and pushes the new geometry onto the demo so the whole pipeline renders at that
size. `--aspect` is the non-16:9 sibling (see [config.md](config.md)).

Encode quality is two `VideoConfig` knobs passed straight to ffmpeg by
`encode_frame_sequence` (animated path) and `assemble_video` (static path):

- **`crf`** (default `18`) — the H.264 constant-rate-factor. Lower is
  crisper/larger; `18` is **near-visually-lossless** — noticeably sharper than the
  x264 default of `23` (DemoCreate's previous behavior).
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
| `typing_fraction` | `0.7` | (config) | Fraction of a chunk's window spent typing. |
| `cursor` | `True` | (config) | Draw the animated cursor + click ripple. |
| `width`/`height` | `1920`/`1080` | `--resolution` (16:9 tier) | Output size; everything scales to height. |
| `crf` | `18` | (config) | H.264 quality; `18` ≈ visually lossless, lower = crisper. |
| `preset` | `"medium"` | (config) | x264 speed/size tradeoff (`ultrafast`…`veryslow`). |

`AnimationConfig.from_video()` builds the animator's settings from a
`VideoConfig` plus the `Theme` (waveform/accent colors) and `AudioConfig`
(lead/gap/trail timing).

## The two render paths

- **Animated (default).** `render_animation_frames()` writes `anim_%05d.png`
  frames, then `encode_frame_sequence()` encodes them with the voiceover at
  `animation_fps`.
- **Static (`--no-animate`).** `assemble_video()` holds each still frame for its
  measured clip duration via an ffmpeg concat demuxer — a slideshow synced to the
  audio. `--captions` burns the SRT into the picture here (needs libass).

Both paths require **`ffmpeg` on `PATH`** (no pip install needed); absence raises
`BackendUnavailableError(extra="video")`.

## Verification

Every render is content-verified by default (`verify_video()` in
`export/verify.py`) — see [the `verify` command](cli.md#verify). It asserts a
real video stream of the expected size, an audio stream, **non-silent** audio
(ffmpeg `volumedetect` mean volume above a floor), and a **non-black** sampled
frame (grayscale pixel variance above a floor). `render` exits non-zero if
verification fails. This is the harness that proved the end-to-end render real:
the `Policy Entanglement in Active Inference` paper rendered to a 1920×1080 /
~188 s H.264 + AAC video, content-verified ok (and the package showcase to a
3840×2160 / 129.7 s video) — see [videos.md](videos.md).

## See also

- [config.md](config.md) — `VideoConfig` (resolution + crf/preset) and `Theme` reference.
- [audio.md](audio.md) — the voiceover that drives the waveform + timing.
- [cli.md](cli.md) — `render` (`--resolution`/`--author`/`--watermark`) / `verify` options.
- [provenance.md](provenance.md) — the on-screen bars, container tags, and steganography.
- [architecture.md](architecture.md) — the full render-to-verify flow.
