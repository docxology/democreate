# CLI reference

The `democreate` command is a **thin orchestration layer** over the library
(`pipeline.py` and the subsystems) — it carries no business logic of its own.
Every command resolves to a few library calls. It is a [Typer](https://typer.tiangolo.com/)
app; run any command with `--help` for its options. Running `democreate` with no
arguments prints help.

```
democreate init      [PATH]   [--format json|yaml]   write a starter demo artifact
democreate inspect   DEMO                             validate + summarize a demo
democreate build     DEMO     [--output] [--tts] [--strict/--no-strict]
                                                      run the full pipeline → player
democreate tour      REPO     [--output] [--title] [--build/--no-build]
                                                      generate + build a codebase tour
democreate captions  DEMO     [--format srt|vtt|ass]  emit subtitles to stdout
democreate render    DEMO     [--output] [--tts] [--voice] [--fps] [--captions]
                              [--animate/--no-animate] [--animation-fps] [--theme]
                              [--aspect] [--resolution] [--author] [--watermark]
                              [--header/--no-header] [--config]
                                                      animated HD MP4 + voiceover, then verify
democreate verify    VIDEO    [--width] [--height] [--min-duration]
                                                      content-assert a video file
democreate paper     PDF      [--repo] [--figures] [--output] [--pages] [--theme]
                              [--voice] [--tts] [--aspect] [--resolution] [--author]
                              [--watermark] [--max-figures] [--config] [--render/--no-render]
                                                      narrated demo of a research paper
democreate thumbnail DEMO     [--out] [--theme] [--subtitle]
                                                      render a poster/thumbnail frame
democreate gif       DEMO     [--output] [--gif] [--fps] [--theme]
                                                      build + export an animated GIF preview
democreate config    [OUT]    [--theme]               write a commented render-config YAML
democreate stego     IMAGE    [--demo]                extract/verify steganographic provenance
democreate backends                                   list backends + availability
democreate version                                    print the version
```

## `init`

Write a small, valid starter `Demo` you can edit and then `build`. It doubles as
documentation-by-example.

```bash
democreate init demo.json            # default path is demo.json
democreate init demo.yaml --format yaml
```

| Option | Default | Meaning |
|--------|---------|---------|
| `PATH` (arg) | `demo.json` | Where to write the artifact. |
| `--format`, `-f` | `json` | `json` or `yaml`. |

## `inspect`

Load a `.json`/`.yaml` demo, validate it, and print a structural summary table
(scenes, chunks, actions, estimated duration, validity). Exits non-zero if the
demo is invalid, listing each problem.

```bash
democreate inspect demo.json
```

## `build`

Run the full pipeline — TTS → TTS→STT sync → timeline → frames + manifest →
captions → HTML player + transcript + JSON — into an output workspace. Prints a
JSON summary and the player path.

```bash
democreate build demo.json --output output --tts auto
```

| Option | Default | Meaning |
|--------|---------|---------|
| `DEMO` (arg) | required | Path to a `.json`/`.yaml` demo. |
| `--output`, `-o` | `output` | Output workspace directory. |
| `--tts` | `auto` | TTS backend: `auto`, `silent`, `kokoro`, `chatterbox`. |
| `--strict / --no-strict` | `--strict` | Fail (`SchemaValidationError`) on an invalid demo vs. warn and continue. |

## `tour`

Generate a codebase-tour demo from a repository (via the `codebase` AST walker and
the narration script generator), write it to `<output>/demos/tour.json`, and — by
default — render it.

```bash
democreate tour /path/to/repo --title "My Project Tour" --output output
democreate tour /path/to/repo --no-build      # generate only, do not render
```

| Option | Default | Meaning |
|--------|---------|---------|
| `REPO` (arg) | required | Repository/directory to tour. |
| `--output`, `-o` | `output` | Output workspace. |
| `--title`, `-t` | `Codebase Tour` | Demo title. |
| `--build / --no-build` | `--build` | Also render the generated demo. |

## `captions`

Emit subtitles for a demo to stdout in the chosen format. Useful for piping into
a file or a player.

```bash
democreate captions demo.json --format srt > demo.srt
democreate captions demo.json -f vtt
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--format`, `-f` | `srt` | `srt`, `vtt`, or `ass`. |

## `render`

Render a demo to a real **animated HD MP4 with a spoken voiceover**, then
content-verify it. Builds the demo (using the chosen TTS), assembles the
per-chunk narration into one voiceover track (with lead/gap/trail silence,
`loudnorm`, and fades — see [audio.md](audio.md)), and — by default —
**animates** the still per-chunk frames: re-samples them onto `animation_fps` and
overlays a moving speech waveform, a progress bar, scene crossfades, and Ken
Burns on slide/background frames (see [video.md](video.md)). Each frame is held
for its narration clip's *measured* duration so audio and video share one
timebase (no drift). Writes `<output>/video/demo.mp4`.

By default the animated render also **types editor code in character-by-character**
(with an animated cursor and click ripple) for codebase scenes whose chunks carry
a `type_code`/`create_file` action — see [video.md](video.md#typing-animation).
`--resolution` picks a named 16:9 tier (`720p`/`1080p`/`1440p`/`2160p`/`4k`) and
`--aspect` reshapes the output to a named aspect-ratio preset before rendering.
`--author`/`--watermark` add on-screen provenance (footer bar + container tag +
signed payload — see [provenance.md](provenance.md)), and `--header` turns on the
top metadata bar (title · section), which is off by default.

```bash
democreate render demo.json -o output --voice Samantha
democreate render demo.json --tts system --voice Daniel --captions
democreate render demo.json --theme midnight --animation-fps 24
democreate render demo.json --resolution 2160p      # true 4K (everything scales)
democreate render demo.json --aspect 9:16           # vertical social cut
democreate render demo.json --author "Daniel Ari Friedman" --watermark "© 2026"
democreate render demo.json --config my_theme.yaml
democreate render demo.json --no-animate            # static slideshow, audio-synced
```

| Option | Default | Meaning |
|--------|---------|---------|
| `DEMO` (arg) | required | Path to a `.json`/`.yaml` demo. |
| `--output`, `-o` | `output` | Output workspace. |
| `--tts` | `system` | `system` (real OS voice), `silent`, `kokoro`, `chatterbox`. |
| `--voice`, `-v` | `Samantha` | System voice name (macOS: see `say -v '?'`). |
| `--fps` | `0` | Static-render frame rate (`0` = the demo's fps). |
| `--captions / --no-captions` | `--no-captions` | Burn subtitles in, static path (needs libass). |
| `--animate / --no-animate` | `--animate` | Moving waveform + progress bar + transitions + typing/cursor vs static slideshow. |
| `--animation-fps` | `15` | Frame rate of the animated render. |
| `--theme` | `noir` | Theme preset: `noir`, `dark`, `light`, `midnight`, `paper`. |
| `--aspect` | `""` (demo's size) | Aspect preset: `16:9`, `9:16`, `1:1`, `4:3`, `4:5` (see [config.md](config.md#aspect-presets)). |
| `--resolution` | `""` (demo's size) | 16:9 tier: `720p`, `1080p`, `1440p`, `2160p`, `4k` (see [config.md](config.md#resolution-tiers)). |
| `--author` | `""` | Creator name → footer bar + MP4 `artist` tag + provenance record. |
| `--watermark` | `""` | Persistent watermark text (footer far-right). |
| `--header / --no-header` | `--no-header` | Show the top metadata bar (title · section). Off by default. |
| `--config` | `None` | `RenderConfig` YAML; **overrides `--theme`/`--voice`** (see [config.md](config.md)). |

Requires a system TTS (`say` on macOS, `espeak` on Linux) and `ffmpeg` on `PATH`.
Exits non-zero if verification fails. With `--tts silent` you get a real video
with a (correctly-flagged) silent track. Every render also writes YouTube
chapters and embeds chapter markers into the MP4, **container metadata tags**, and
a **signed steganographic poster** (see [provenance.md](provenance.md) and the
chapters note below).

## `verify`

Independently content-assert any video file via `ffprobe`/`ffmpeg`: a real video
stream of the expected size, an audio stream covering it, audio that is **not
silent** (mean volume above a floor), and a sampled frame that is **not black**
(pixel variance). Prints a JSON report and exits non-zero on any failure.

```bash
democreate verify output/video/demo.mp4 --width 1920 --height 1080
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--width` | `0` | Expected width (`0` = skip the check). |
| `--height` | `0` | Expected height (`0` = skip the check). |
| `--min-duration` | `1.0` | Minimum acceptable duration in seconds. |

## `paper`

Generate a narrated demo of a **research paper** from its PDF — optionally with
the paper's codebase (`--repo`) and a directory of exported figures (`--figures`)
— and (by default) render + verify the video. Reads the PDF with poppler
(`pdfinfo`/`pdftotext`/`pdftoppm`, zero pip deps), extracts a title/abstract/
figure summary, rasterizes the requested pages, renders an architecture diagram
of the codebase, assembles a `Demo`, and renders it. Writes
`<output>/demos/paper.json` and `<output>/video/demo.mp4`. See [paper.md](paper.md)
for the full workflow.

It also reads the paper's **deeper structure**: the real abstract (skipping the
table of contents), the real figure captions (`"Figure N: ..."`, narrated on each
figure scene), and the section list (which adds a **structure** scene mapping the
paper's parts). This is best-effort and degrades gracefully if poppler is absent.

By default the video is attributed to the **PDF's own author** (the container
`artist` tag and the signed provenance) and its `source` is set to the paper
title; pass `--author` to override. `--aspect`/`--resolution` reshape/resize the
render exactly as on `render`, and `--max-figures` caps how many figures are
featured.

```bash
democreate paper paper.pdf --repo ./code --figures ./figs --theme paper
democreate paper paper.pdf --pages 1,2 --voice Daniel
democreate paper paper.pdf --max-figures 8 --resolution 2160p   # 8 figures, true 4K
democreate paper paper.pdf --aspect 9:16 --author "Me" --watermark "© 2026"
democreate paper paper.pdf --no-render          # emit paper.json only
```

| Option | Default | Meaning |
|--------|---------|---------|
| `PDF` (arg) | required | Path to the paper PDF. |
| `--repo`, `-r` | `None` | Associated codebase directory (architecture diagram). |
| `--figures` | `None` | Directory of exported figure images (`.png`/`.jpg`). |
| `--output`, `-o` | `output` | Output workspace. |
| `--pages` | `"1"` | Comma-separated 1-based PDF pages to show. |
| `--theme` | `paper` | `paper`, `noir`, `dark`, `light`, `midnight` (paper is the academic default for paper demos). |
| `--voice`, `-v` | `Samantha` | System voice name. |
| `--tts` | `system` | TTS backend. |
| `--aspect` | `""` (demo's size) | Aspect preset: `16:9`, `9:16`, `1:1`, `4:3`, `4:5` (see [config.md](config.md#aspect-presets)). |
| `--resolution` | `""` (demo's size) | 16:9 tier: `720p`, `1080p`, `1440p`, `2160p`, `4k` (see [config.md](config.md#resolution-tiers)). |
| `--author` | `""` (the PDF's author) | Override the creator name; defaults to the PDF metadata's author → footer + MP4 `artist` tag + provenance. |
| `--watermark` | `""` | Persistent watermark text (footer far-right). |
| `--max-figures` | `6` | How many figures to feature in the demo. |
| `--config` | `None` | `RenderConfig` YAML (overrides `--theme`). |
| `--render / --no-render` | `--render` | Render the video, or only emit `paper.json`. |

Requires poppler on `PATH` (`pdfinfo`/`pdftotext`/`pdftoppm`); rendering also
needs a system TTS and `ffmpeg`. Missing poppler raises
`BackendUnavailableError(extra="pdf")`.

## `thumbnail`

Render a designed **poster / thumbnail** still for a demo — a themed background
with the title word-wrapped and centered over a thin accent rule, plus a subtitle
(a generated `"<N> scenes · <duration>s"` summary by default). Pure Pillow, no
`ffmpeg`. Sized to the demo's own resolution. See
[`render_poster`](api.md#democreateexportposter).

```bash
democreate thumbnail demo.json --out poster.png --theme midnight
democreate thumbnail demo.json --subtitle "narrated HD demo"
```

| Option | Default | Meaning |
|--------|---------|---------|
| `DEMO` (arg) | required | Path to a `.json`/`.yaml` demo. |
| `--out`, `-o` | `poster.png` | Destination `.png`. |
| `--theme` | `dark` | Theme preset: `noir`, `dark`, `light`, `midnight`, `paper`. |
| `--subtitle` | `""` (auto) | Explicit subtitle; empty uses a generated scene/duration summary. |

## `gif`

Build the demo and export an **animated GIF preview** of its frames — evenly
down-sampling the frame sequence (always keeping the first and last) into a short
looping GIF. Great for a README or a social card. See
[`demo_to_gif`](api.md#democreateexportposter).

```bash
democreate gif demo.json --gif demo.gif --fps 8 --theme dark
```

| Option | Default | Meaning |
|--------|---------|---------|
| `DEMO` (arg) | required | Path to a `.json`/`.yaml` demo. |
| `--output`, `-o` | `output` | Output workspace (the demo is built here first). |
| `--gif` | `demo.gif` | Destination `.gif`. |
| `--fps` | `8` | Playback frame rate of the GIF. |
| `--theme` | `dark` | Theme preset (`noir`, `dark`, `light`, `midnight`, `paper`). |

## `config`

Write a **fully-commented render-config YAML** you can edit and pass to `--config`.
This is the most accessible control surface — every commonly-tuned knob
(resolution/quality, motion, audio, metadata) with an inline comment, built by
`RenderConfig.commented_yaml`.

```bash
democreate config democreate.yaml             # default path is democreate.yaml
democreate config theme.yaml --theme midnight # seed from a preset theme
democreate render demo.json --config democreate.yaml
```

| Option | Default | Meaning |
|--------|---------|---------|
| `OUT` (arg) | `democreate.yaml` | Where to write the config. |
| `--theme` | `dark` | Base theme preset to seed defaults from (`noir`, `dark`, `light`, `midnight`, `paper`). |

## `stego`

Extract — and optionally **verify** — the steganographic provenance hidden in a
signed PNG (e.g. `output/provenance/poster_signed.png`, written by every
`render`/`paper`). Prints the embedded JSON record; with `--demo` it recomputes the
content digest and reports whether the payload matches that demo, exiting non-zero
on a mismatch. See [provenance.md](provenance.md).

```bash
democreate stego output/provenance/poster_signed.png
democreate stego output/provenance/poster_signed.png --demo demo.json   # verify
```

| Option | Default | Meaning |
|--------|---------|---------|
| `IMAGE` (arg) | required | A signed PNG carrying an LSB provenance payload. |
| `--demo` | `None` | A demo to verify the payload against (`✓`/`✗`, exits non-zero on mismatch). |

Remember the honesty note: the payload lives in the **lossless PNG sidecars**, not
the H.264 video pixels — an MP4 re-encode destroys LSB steganography, so the video
carries container tags instead ([provenance.md](provenance.md)).

## `backends`

List every subsystem capability and whether its optional extra is installed
(`installed`) or the deterministic default is in use (`default`), with the
`uv sync --extra <extra>` command to upgrade each.

```bash
democreate backends
```

## `version`

Print the installed DemoCreate version.

```bash
democreate version
```

## Command-group naming

The commands group naturally into the lifecycle phases referenced across the docs:
**init** (scaffold), **inspect** (validate), **build** / **tour** / **paper**
(generate + assemble), **render** / **verify** (produce + assert the video),
**thumbnail** / **gif** (still + preview exports), **config** / **stego**
(config authoring + provenance verification), and
**captions** / **backends** / **version** (export + introspection). `build` stops
at the interactive HTML player (player, transcript, demo JSON, captions); `render`
and `paper` continue through the animated render, encode, and content
verification — see [video.md](video.md), [audio.md](audio.md),
[architecture.md](architecture.md), and [backends.md](backends.md).
