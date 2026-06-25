# Configuration and theming

A single `RenderConfig` controls the **look** (theme colors + font scale), the
**sound** (voice, pacing, normalization, fades), the **motion** (fps, resolution,
quality, waveform, transitions, Ken Burns, typing animation, animated cursor), and
the **provenance** (on-screen metadata bars, container tags, steganography) of a
render. It is plain data — serializable
to and from YAML — so a render can be reproduced from one file. Everything has a
sensible default that matches the package's out-of-the-box look, so config is
purely additive: omit it and nothing changes.

`RenderConfig` lives in `src/democreate/config.py` and is threaded through the
pipeline, the synthetic renderer, and the animator: `Theme` colors the frames
(`capture/screen.py`), `AudioConfig` shapes the voiceover (`assembly/audio.py`),
`VideoConfig` drives the animated render (`assembly/animator.py`), and
`MetadataConfig` drives provenance (`export/overlay.py`, `export/metadata.py`,
`export/stego.py`).

## The four config objects

`RenderConfig` is a composite of four dataclasses:

```python
@dataclass
class RenderConfig:
    theme: Theme              # colors + font ratios
    audio: AudioConfig        # voice + pacing + normalization
    video: VideoConfig        # geometry + resolution + quality + motion
    metadata: MetadataConfig  # on-screen bars + container tags + steganography
```

### `Theme` — colors + font scale

Colors are `(r, g, b)` 0–255 tuples; font ratios are fractions of the frame
height, so text stays proportional at any resolution. The **noir** theme is the
default. Selected fields:

| Group | Fields |
|-------|--------|
| surfaces | `bg_editor`, `bg_terminal`, `bg_browser`, `bg_slide`, `title_bar`, `gutter`, `band_bg` |
| text | `text`, `dim`, `text_dark` |
| accents | `accent`, `section_fg`, `prompt`, `cursor` |
| code highlight | `highlight`, `highlight_bar` |
| caption | `caption_bg`, `caption_fg` |
| waveform | `wave_played`, `wave_bar` |
| syntax (pygments) | `syn_keyword`, `syn_string`, `syn_comment`, `syn_number`, `syn_name` |
| font ratios | `title_ratio` (0.094), `subtitle_ratio` (0.040), `code_ratio` (0.030), `terminal_ratio` (0.032), `caption_ratio` (0.038), `section_ratio` (0.026) — larger for legibility on video |

`Theme.from_dict()` coerces color *lists* (as they appear in YAML) back to
tuples and ignores unknown keys.

#### Theme presets

**Five** presets ship in the `THEMES` registry and are selectable via `--theme`:

| Preset | Look | Typical use |
|--------|------|-------------|
| `noir` | **The default** — near-black `(12,12,14)` surfaces, bright-white `(242,242,244)` text, and a single refined red `(224,49,57)` as the only chroma, used sparingly (played waveform, cursor, code keywords, the section pill / heading rule, the line-highlight bar, the top progress line). Code syntax is monochrome-with-red (keywords red, names white, strings gray, comments dim). | The default look for software demos. |
| `dark` | Slate editor, blue accent. | Software demos (the classic dark look). |
| `light` | Paper-white editor, blue accent. | Light-background screencasts. |
| `midnight` | Deep navy surfaces, violet accent. | High-contrast / cinematic. |
| `paper` | Warm paper-white slides, serif-ish, amber accent. | **Research-paper demos** (see [paper.md](paper.md)). |

### `AudioConfig` — voice + pacing

| Field | Default | Meaning |
|-------|---------|---------|
| `backend` | `"system"` | TTS backend: `system` / `silent` / `kokoro` / `chatterbox`. |
| `voice` | `""` | Optional voice id for voiced backends; blank uses the OS default. |
| `rate_wpm` | `None` | Optional speaking-rate override (system voices). |
| `lead_silence_ms` | `300` | Silence prepended to the whole voiceover. |
| `trail_silence_ms` | `600` | Silence appended to the whole voiceover. |
| `gap_ms` | `220` | Silence inserted between chunks (breathing room). |
| `normalize` | `True` | Apply ffmpeg `loudnorm` to even out loudness. |
| `fade_ms` | `180` | Fade-in/out applied to the final track. |

See [audio.md](audio.md) for how these shape the assembled voiceover.

### `VideoConfig` — geometry + motion

| Field | Default | Meaning |
|-------|---------|---------|
| `width` / `height` | `1920` / `1080` | Output dimensions in pixels. |
| `fps` | `30` | Nominal demo frame rate. |
| `animation_fps` | `15` | Frame rate of the animated render. |
| `animate` | `True` | Render the moving waveform + progress (vs a slideshow). |
| `waveform` | `True` | Draw the speech-waveform band. |
| `progress_bar` | `True` | Draw the progress line. It now sits at the **absolute top edge** (`y=0`, ~6 px) so it never overlaps content or background images — it previously sat ~58 px down and clipped the top of figures and diagrams. |
| `transitions` | `True` | Crossfade between scenes. |
| `transition_ms` | `450` | Crossfade duration. |
| `ken_burns` | `False` | Slow zoom on background-image scenes. **Off by default**: zooming crops content off the frame edges, losing information — the no-crop fit-contain layout keeps figures and diagrams whole. Enable only if you accept the edge crop. |
| `ken_burns_zoom` | `1.06` | Peak Ken Burns zoom factor (applies only when `ken_burns` is enabled). |
| `typing` | `True` | Type editor code in character-by-character (vs showing it all at once). |
| `typing_fraction` | `0.7` | Fraction of a chunk's window spent typing before the code holds. |
| `cursor` | `True` | Draw the animated cursor (with a click ripple) where a chunk supplies a position. |
| `crf` | `18` | H.264 quality: lower = crisper/larger. `18` ≈ visually lossless; `23` is the x264 default. |
| `preset` | `"medium"` | x264 speed/size tradeoff (`ultrafast` … `veryslow`); passed straight to ffmpeg. |

`crf` and `preset` are passed to ffmpeg by `encode_frame_sequence` /
`assemble_video`, so they apply to both the animated and the static render paths.
The default `crf: 18` is **near-visually-lossless** — noticeably crisper than the
x264 default of `23`. See [video.md](video.md) for how these drive the animator —
including the [typing animation](video.md#typing-animation),
[cursor](video.md#animated-cursor), and
[resolution & quality](video.md#resolution-quality).

### Layout: no-crop fit-contain + autosize code

Two layout invariants in the synthetic renderer (`capture/screen.py`) keep
content whole at every resolution and aspect ratio — there is no config knob for
them because losing information is never the right default:

- **Fit-contain backgrounds (never crop).** A full-frame `background_image`
  (figure, PDF page, architecture diagram, screenshot) is scaled by
  `min(bw/sw, bh/sh)` — the **contain** fit — so the whole image is visible inside
  the content band with a subtle matte frame around it. A cover-crop would push
  the edges of a figure or diagram off-screen; DemoCreate refuses that. This pairs
  with `ken_burns: false` (above): a slow zoom would re-introduce the very edge
  crop the contain fit avoids.
- **Autosize code (no clip).** An editor frame picks the **largest** legible mono
  font that fits the *whole* code block — sized by both the longest line (so it
  fits the width without clipping the right edge) and the line count (so every
  line fits the height), with a hard legibility floor and a cap of `0.034 ×`
  frame height. Code never overflows the frame and never gets silently truncated.

### Slide surfaces: bullet lists and stat cards

A `slide`-kind scene can carry two packed, no-crop slide surfaces, set from the
scene's free-form `context` dict and threaded onto the per-chunk
[`FrameState`](schema.md#related-media-types-media.py) by the compositor:

| Surface | `scene.context` key | `FrameState` field | Renders as |
|---------|---------------------|--------------------|------------|
| Bullet list | `bullets` | `FrameState.bullets: list[str]` | Up to 6 wrapped bullet items, distributed down the slide (not a floating title). |
| Stat cards | `stats` | `FrameState.stats: list[tuple[str, str]]` | Up to 5 big-number `(value, label)` cards drawn in a row. |

```json
{
  "id": "numbers", "title": "By the numbers", "kind": "slide",
  "context": {
    "bullets": ["Declarative spine", "Deterministic defaults", "Audio-anchored sync"],
    "stats": [["664", "tests"], ["7", "subsystems"], ["5", "themes"], ["4K", "max"]]
  },
  "chunks": [{ "id": "n1", "text": "DemoCreate, by the numbers." }]
}
```

`stats` take precedence over `bullets` when both are present on a frame. Both are
honored on any `slide` scene; the package's own showcase demo uses them for its
bullet and stat-card scenes (see [videos.md](videos.md)).

### `MetadataConfig` — on-screen / container / hidden provenance

The same fields drive three carriers: visible top/bottom overlay bars, MP4
container tags, and a steganographic payload in lossless poster/bookend PNGs. It
is now part of `RenderConfig` (`cfg.metadata`). The full provenance story is in
[provenance.md](provenance.md).

| Field | Default | Meaning |
|-------|---------|---------|
| `author` | `""` | Creator name → footer bar + container `artist` tag + provenance record. |
| `title` | `""` | Overrides the demo title in overlays/tags when set. |
| `date` | `""` | Date string → footer + container `date` + provenance `created_hint`. |
| `source` | `""` | Source label (repo / paper / project) → footer + container `comment`. |
| `url` | `""` | A URL shown in the footer (and in the container `comment`). |
| `watermark` | `""` | Small persistent watermark text (footer far-right). |
| `header` | `False` | Draw the top metadata bar (title · section). |
| `footer` | `True` | Draw the bottom metadata bar (author · source · url · clock). |
| `show_clock` | `True` | Show a running `M:SS / M:SS` clock in the footer. |
| `container_tags` | `True` | Write MP4 metadata tags via ffmpeg (`build_tags` → `embed_tags`). |
| `steganography` | `True` | Embed a signed provenance payload in lossless PNG sidecars. |

`--author` and `--watermark` on `render` set those fields without a config file.

## Resolution tiers

`RESOLUTIONS` is a registry of named **16:9 resolution tiers** → `(width, height)`.
Every visual element scales to the frame **height**, so a higher tier is genuinely
higher resolution — not an upscale of a 1080p render:

| Tier | Size |
|------|------|
| `720p` | `1280×720` |
| `1080p` | `1920×1080` |
| `1440p` | `2560×1440` |
| `2160p` | `3840×2160` |
| `4k` | `3840×2160` (alias of `2160p`) |

`RenderConfig.set_resolution(name)` sets `video.width`/`video.height` from the tier
and returns `self` for chaining; unknown names are ignored. The `render` command
also pushes the new geometry onto the demo, so the whole pipeline renders at that
size (verified: `1440p` produces a true `2560×1440` video):

```python
cfg = RenderConfig.preset("dark").set_resolution("1440p")   # 2560×1440
```

```bash
democreate render demo.json --resolution 2160p              # true 4K
```

## Aspect presets

`ASPECTS` is a registry of named aspect-ratio presets → `(width, height)` at
1080-class resolution, surfaced as `democreate render --aspect <name>`:

| Preset | Size | Typical use |
|--------|------|-------------|
| `16:9` | `1920×1080` | Standard landscape (the default). |
| `9:16` | `1080×1920` | Vertical reels / shorts. |
| `1:1` | `1080×1080` | Square social. |
| `4:3` | `1440×1080` | Classic / slides. |
| `4:5` | `1080×1350` | Portrait feed. |

`RenderConfig.set_aspect(name)` sets `video.width`/`video.height` from the preset
and returns `self` for chaining; unknown names are ignored. The `render` command
also pushes the new geometry onto the demo so the whole pipeline renders at that
size:

```python
cfg = RenderConfig.preset("midnight").set_aspect("9:16")   # 1080×1920
```

## Using a config

### `democreate config` — a commented starter YAML

The most accessible control surface is a fully-commented config file.
`democreate config out.yaml [--theme noir]` writes one (via
`RenderConfig.commented_yaml`) with every commonly-tuned knob — resolution/quality,
motion, audio, metadata — annotated inline, ready to edit and pass to `--config`:

```bash
democreate config democreate.yaml --theme noir
democreate render demo.json --config democreate.yaml
```

The first lines look like:

```yaml
# DemoCreate render configuration. Pass with: democreate render --config this.yaml
# Every field is optional; omitted fields fall back to the defaults below.

theme: noir            # preset: dark | light | midnight | paper

video:
  width: 1920              # frame width in pixels
  height: 1080             # frame height (everything scales to this)
  # resolution tiers (16:9): 720p 1280x720 · 1080p 1920x1080 · 1440p 2560x1440 · 2160p/4k 3840x2160
  fps: 30                  # demo frame rate
  animation_fps: 15        # animated render frame rate (motion smoothness)
  crf: 18                  # H.264 quality: 18 ~ visually lossless, 23 = default, lower = crisper
  preset: medium           # x264 speed/size tradeoff: ultrafast..veryslow
```

(It continues with the rest of `video`, then `audio` and `metadata` sections,
each line commented.) See [cli.md](cli.md#config).

### `--theme` preset (quick)

```bash
democreate render demo.json --theme midnight
democreate paper paper.pdf --theme paper
```

`RenderConfig.preset(name)` looks the name up in `THEMES` and returns a config
that uses that preset theme (audio/video at their defaults).

### `--config` YAML (full control)

```bash
democreate render demo.json --config my_theme.yaml
```

`--config` overrides `--theme`. The CLI still applies `--voice`/`--tts` on top
of a loaded config, so you can pin a theme in YAML and pick the voice on the
command line.

## A sample YAML config

`RenderConfig.to_yaml()` emits this shape (colors stay as lists for YAML
cleanliness); any subset is accepted — omitted keys fall back to the preset/base
defaults via `RenderConfig.from_dict()`:

```yaml
theme:
  name: midnight
  accent: [124, 92, 255]
  wave_played: [150, 120, 255]
  title_ratio: 0.085
  caption_ratio: 0.032
audio:
  backend: system
  voice: Daniel
  lead_silence_ms: 300
  trail_silence_ms: 600
  gap_ms: 220
  normalize: true
  fade_ms: 180
video:
  width: 1920
  height: 1080
  fps: 30
  animation_fps: 15
  animate: true
  waveform: true
  progress_bar: true
  transitions: true
  transition_ms: 450
  ken_burns: false
  ken_burns_zoom: 1.06
  typing: true
  typing_fraction: 0.7
  cursor: true
  crf: 18
  preset: medium
metadata:
  author: "Daniel Ari Friedman"
  source: "github.com/you/project"
  url: "https://your-domain.example.com"
  watermark: "© 2026"
  header: false
  footer: true
  show_clock: true
  container_tags: true
  steganography: true
```

`theme` may also be a bare string (`theme: paper`) to select a preset wholesale.

## Loading a config in code

```python
from democreate.config import RenderConfig, Theme, THEMES

cfg = RenderConfig.preset("paper")          # a preset theme
cfg = RenderConfig.from_file("my.yaml")     # full YAML
cfg.audio.voice = "Daniel"                  # override in place
text = cfg.to_yaml()                        # serialize back out
```

## See also

- [cli.md](cli.md) — `render`/`paper`/`config` options including `--theme`, `--config`, `--resolution`.
- [video.md](video.md) — the animated render driven by `VideoConfig` (resolution + quality).
- [audio.md](audio.md) — the voiceover assembly driven by `AudioConfig`.
- [provenance.md](provenance.md) — the full `MetadataConfig` story (bars, tags, steganography).
- [architecture.md](architecture.md) — where config threads through the pipeline.
