# CLI reference: commands, defaults, output paths and input authority

`democreate` is the native Typer entry point over the library. No arguments
prints help; each command accepts `--help`. This page owns command/default
reference; [quickstart](quickstart.md) and [recipes](recipes.md) own workflows,
[configuration](config.md) owns override precedence and [backends](backends.md)
distinguishes implemented paths from dependency-present unwired slots.

```
democreate init      [PATH]   [--format json|yaml]   write a starter demo artifact
democreate inspect   DEMO                             validate + summarize a demo
democreate build     DEMO     [--output] [--tts] [--strict/--no-strict]
                                                      run the full pipeline → player
democreate tour      REPO     [--output] [--title] [--build/--no-build]
                              [--render/--no-render] [--tts] [--voice] [--theme]
                                                      generate a codebase tour (--render → MP4)
democreate portfolio DIR      [--output] [--tts] [--voice] [--theme] [--resolution]
                              [--max-projects] [--max-modules] [--skip]
                                                      a timestamped summary video per project
democreate localize  DEMO     [--audio-lang] [--subtitle-lang] [--source-lang]
                              [--pairs] [--translator] [--model] [--host]
                              [--tts] [--voice] [--theme] [--resolution] [--burn]
                                                      audio in one language, subtitles in another
democreate captions  DEMO     [--format srt|vtt|ass]  emit subtitles to stdout
democreate render    DEMO     [--output] [--tts] [--voice] [--fps] [--captions]
                              [--animate/--no-animate] [--animation-fps] [--theme]
                              [--aspect] [--resolution] [--author] [--watermark]
                              [--header/--no-header] [--config]
                                                      animated HD MP4 + voiceover, then verify
democreate verify    VIDEO    [--width] [--height] [--min-duration]
                                                      content-assert a video file
democreate score-sync ANNOTATIONS                    score supplied onset annotations as JSON
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
democreate fetch-voice                                download Kokoro neural-TTS model (~340 MB)
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
demo is invalid, listing each problem. Pass `--json` for machine-readable output
(the same summary as a JSON object).

```bash
democreate inspect demo.json
democreate inspect demo.json --json
```

## `build`

Run TTS → duration-based sync → timeline → frames/manifest → captions → timed
HTML image preview, transcript and resolved JSON. The preview has navigation
and caption cues but does not play synthesized audio. Prints a JSON summary.

```bash
democreate build demo.json --output output --tts auto
```

| Option | Default | Meaning |
|--------|---------|---------|
| `DEMO` (arg) | required | Path to a `.json`/`.yaml` demo. |
| `--output`, `-o` | `output` | Output workspace directory. |
| `--tts` | `auto` | `auto`/`silent` → silent core; implemented `system`, `kokoro`, `elevenlabs`; `chatterbox` is unwired. |
| `--strict / --no-strict` | `--strict` | Fail (`SchemaValidationError`) on an invalid demo vs. warn and continue. |
| `--asset-root` | Demo file directory | Relative background base and allowed input root; see [resolved bundles](#image-authority-and-resolved-bundles). |

## `tour`

Generate a codebase-tour demo from a repository (via the `codebase` AST walker and
the narration script generator) and write it to `<output>/demos/tour.json`. By
default it also **builds** the HTML player; pass `--render` to instead produce a
**verified MP4** with a real voiceover.

```bash
democreate tour /path/to/repo --title "My Project Tour" --output output
democreate tour /path/to/repo --no-build           # generate only
democreate tour /path/to/repo --render --voice Samantha   # → output/video/demo.mp4
```

| Option | Default | Meaning |
|--------|---------|---------|
| `REPO` (arg) | required | Repository/directory to tour. |
| `--output`, `-o` | `output` | Output workspace. |
| `--title`, `-t` | `Codebase Tour` | Demo title. |
| `--build / --no-build` | `--build` | Build the HTML player. |
| `--render / --no-render` | `--no-render` | Render a verified MP4 with voiceover. |
| `--tts` | `system` | TTS backend when `--render` (`system`/`silent`/`kokoro`/`elevenlabs`). |
| `--voice`, `-v` | (none) | Voice id when `--render`. |
| `--theme` | `noir` | Theme preset when `--render`. |

## `portfolio`

Render a **timestamped summary video for every project** under a directory. Each
project gets its own `output/<name>/` subfolder containing a content-verified MP4
named `<name>-summary-<UTC>.mp4`; a project that fails to render is recorded and
the batch continues. A `portfolio_index.json` and `portfolio_index.html` gallery
are written at the output root.

Project names matching `portfolio_index.json` or `portfolio_index.html`
case-insensitively are reserved for the aggregate files. They fail before any
per-project workspace writes and remain explicit failed entries; they are not
silently filtered out of discovery.

The summary is *describing*, not enumerating: a title card, a what-it-is bullet
slide drawn from the real README, an architecture diagram of the real packages, a
by-the-numbers stat card, two or three load-bearing modules shown as real source
narrated from their **real docstrings**, a how-to-run terminal scene, and an outro.
Discovery is Python-AST + README based (a non-Python project still gets a
README/stat summary, without code scenes).

```bash
# one video per project under a folder of repositories
democreate portfolio path/to/repositories -o output --voice Samantha

# a quick, bounded subset at 720p
democreate portfolio ~/code -o output --resolution 720p --max-projects 3
```

| Option | Default | Meaning |
|--------|---------|---------|
| `PROJECTS_DIR` (arg) | required | Directory of project subdirectories. |
| `--output`, `-o` | `output` | Output root (one `<name>/` folder per project). |
| `--tts` | `system` | TTS backend (`system`/`silent`/`kokoro`/`elevenlabs`). |
| `--voice`, `-v` | (none) | Voice id (e.g. `Samantha`). |
| `--theme` | `noir` | Theme preset. |
| `--resolution` | `1080p` | `720p`/`1080p`/`1440p`/`2160p`/`4k`. |
| `--max-projects` | `0` (all) | Cap the number of projects rendered. |
| `--max-modules` | `6` | Key-module code scenes per project. |
| `--skip` | (none) | Comma-separated project names to skip. |

## `localize`

Render a demo with **audio in one language and subtitles in another**, using a
local, configurable translator (an `ollama` server). The narration is translated
to the audio language and synthesized (driving the timing); the subtitle track is
translated against that same timing. Each output filename encodes both languages
(`<title-slug>-audio_<a>-subs_<s>.mp4`), with full-tag `.srt`/`.vtt` sidecars in `captions/`.

```bash
democreate localize demo.json --audio-lang en --subtitle-lang ru --model lfm2.5
democreate localize demo.json --pairs "en:ru,ru:en,en:es" --model lfm2.5   # batch
democreate localize demo.json --translator identity     # no-op (source language)
```

| Option | Default | Meaning |
|--------|---------|---------|
| `DEMO` (arg) | required | Demo `.json`/`.yaml`. |
| `--output`, `-o` | `output` | Workspace directory. |
| `--asset-root` | Demo file directory | Background base/allowed root. |
| `--audio-lang` | `en` | Spoken (TTS) language code. |
| `--subtitle-lang` | `ru` | Subtitle-track language code. |
| `--source-lang` | `en` | Language the demo is authored in. |
| `--pairs` | (none) | Batch: `audio:subs,audio:subs` (overrides the two above). |
| `--translator` | `ollama` | `identity` (no-op) or `ollama`. |
| `--model` | `smollm2` | ollama model tag (e.g. `lfm2.5`). |
| `--host` | `http://localhost:11434` | ollama host. |
| `--tts` | `kokoro` | Implemented TTS for the audio language; prerequisites must be usable. |
| `--voice` | `""` | Preserve configured/authored defaults; Kokoro alone has language-specific fallback voices. |
| `--theme` | `noir` | Theme preset. |
| `--resolution` | `""` | Preserve authored Demo geometry; an explicit preset changes the loaded Demo's output size. |
| `--burn / --no-burn` | `--no-burn` | Additionally burn the subtitle track into the picture; sidecars are retained. |

> Subtitles are text and work for any language; *audio* in a language needs a TTS
> voice for it (Kokoro langs or an installed system voice).

## `score-sync`: supplied annotation diagnostics

Read annotation-format-1 JSON, not a Demo artifact. Print unrounded event/demo
error summaries, fixed-mode corpus counts, missing data and eligibility as JSON.
Exit 0 means only the supplied-data checks pass; exit 1 retains diagnostic JSON
for unmet criteria; malformed/unreadable input exits 2 with error JSON on stderr.
No media/provenance reference is opened. See [the scoring contract](evaluation.md)
for the complete format and executable missing-data example. This command cannot
certify independence, establish the absent study or authorize publication.

## `captions`

Emit one cue per chunk to stdout. Uses resolved measured starts/durations when
supplied; an authored unsynthesized input only yields text-duration estimates.
This command does not run synthesis or acoustic recognition.

```bash
democreate captions demo.json --format srt > demo.srt
democreate captions demo.json -f vtt
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--format`, `-f` | `srt` | `srt`, `vtt`, or `ass`. |

## `render`

Build with the selected voice, assemble WAV clips with configured pauses,
animate scheduled actions by default, encode MP4 and run basic content checks.
Writes `<output>/video/demo.mp4`. The shared measured clip timebase does not
establish acoustic word-onset accuracy or identical encoded endpoints.

[Video](video.md) owns typing/cursor/transitions and animated/static behavior;
[audio](audio.md) owns WAV assembly, optional normalization and fades. Ken Burns
is off by default; explicit camera motion and overlays can still hide content.
`--resolution` picks a named 16:9 tier (`720p`/`1080p`/`1440p`/`2160p`/`4k`) and
`--aspect` reshapes the output to a named aspect-ratio preset before rendering.
`--author`/`--watermark` add on-screen provenance (footer bar + container tag +
unsigned payload — see [provenance.md](provenance.md)), and `--header` turns on the
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
| `--tts` | `system` | `system` (real OS voice), `silent`, `kokoro`, `elevenlabs`, `chatterbox`. |
| `--voice`, `-v` | `""` (OS default) | Optional system voice name (macOS: see `say -v '?'`). |
| `--fps` | `0` | Static-render frame rate (`0` = the demo's fps). |
| `--captions / --no-captions` | `--no-captions` | Burn SRT in either render path; requires subtitles/libass. |
| `--animate / --no-animate` | `--animate` | Moving waveform + progress bar + transitions + typing/cursor vs static slideshow. |
| `--animation-fps` | `15` | Frame rate of the animated render. |
| `--theme` | `noir` | Theme preset: `noir`, `dark`, `light`, `midnight`, `paper`. |
| `--aspect` | `""` (demo's size) | Aspect preset: `16:9`, `9:16`, `1:1`, `4:3`, `4:5` (see [config.md](config.md#aspect-presets)). |
| `--resolution` | `""` (demo's size) | 16:9 tier: `720p`, `1080p`, `1440p`, `2160p`, `4k` (see [config.md](config.md#resolution-tiers)). |
| `--author` | `""` | Creator name → footer bar + MP4 `artist` tag + provenance record. |
| `--watermark` | `""` | Persistent watermark text (footer far-right). |
| `--header / --no-header` | `--no-header` | Show the top metadata bar (title · section). Off by default. |
| `--config` | `None` | RenderConfig YAML replaces theme preset; CLI TTS and other defaults still apply. See [precedence](config.md#using-a-config). |
| `--asset-root` | Demo file directory | Background base/allowed root. |

The selected implemented TTS must be usable; encoding/checks need ffmpeg/ffprobe.
Silent TTS can encode a video but correctly fails voiced-content verification,
causing nonzero exit. Chapter embedding, container tags and unsigned poster
outputs are attempted as configured and can log best-effort failures; a completed
MP4 alone is not proof that every companion output exists. See [provenance](provenance.md).

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

Abstract/caption/section extraction is heuristic and best-effort. A structure
failure may be logged without discarding the summary; missing poppler cannot
support PDF ingestion and is not a successful fallback. Review text against PDF.

By default the video is attributed to the **PDF's own author** (the container
`artist` tag and the unsigned provenance) and its `source` is set to the paper
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
| `--voice`, `-v` | `""` (OS default) | Optional system voice name. |
| `--tts` | `system` | TTS backend. |
| `--aspect` | `""` (demo's size) | Aspect preset: `16:9`, `9:16`, `1:1`, `4:3`, `4:5` (see [config.md](config.md#aspect-presets)). |
| `--resolution` | `""` (demo's size) | 16:9 tier: `720p`, `1080p`, `1440p`, `2160p`, `4k` (see [config.md](config.md#resolution-tiers)). |
| `--author` | `""` (the PDF's author) | Override the creator name; defaults to the PDF metadata's author → footer + MP4 `artist` tag + provenance. |
| `--watermark` | `""` | Persistent watermark text (footer far-right). |
| `--max-figures` | `6` | How many figures to feature in the demo. |
| `--config` | `None` | `RenderConfig` YAML (overrides `--theme`). |
| `--render / --no-render` | `--render` | Render the video, or only emit `paper.json`. |

Requires poppler on `PATH` (`pdfinfo`/`pdftotext`/`pdftoppm`); rendering also
needs a usable system TTS and `ffmpeg`. Missing poppler raises
`BackendUnavailableError("poppler")`.

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
| `--theme` | `noir` | Theme preset: `noir`, `dark`, `light`, `midnight`, `paper`. |
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
| `--theme` | `noir` | Theme preset (`noir`, `dark`, `light`, `midnight`, `paper`). |

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
| `--theme` | `noir` | Base theme preset to seed defaults from (`noir`, `dark`, `light`, `midnight`, `paper`). |

## `stego`

Extract — and optionally **verify** — the steganographic provenance hidden in a
payload-bearing PNG (e.g. `output/provenance/poster_signed.png`, written by every
`render`/`paper` when enabled and successful). Prints the embedded JSON record;
with `--demo`, compares a recomputed content digest and exits nonzero on mismatch.
Use the resolved emitted Demo; see [provenance](provenance.md).

```bash
democreate stego output/provenance/poster_signed.png
democreate stego output/provenance/poster_signed.png --demo output/demos/demo.json
```

| Option | Default | Meaning |
|--------|---------|---------|
| `IMAGE` (arg) | required | A payload-bearing PNG carrying an LSB provenance payload. |
| `--demo` | `None` | A demo to verify the payload against (`✓`/`✗`, exits non-zero on mismatch). |

Remember the honesty note: the payload lives in the **lossless PNG sidecars**, not
the H.264 video pixels — an MP4 re-encode destroys LSB steganography, so the video
carries container tags instead ([provenance.md](provenance.md)).

## `fetch-voice`

Explicitly download Kokoro model/voices (roughly 340 MB) into the selected cache.
This is not performed by ordinary core builds and is not package installation.
Use a compatible voice runtime and provision the `tts` packages separately;
[backends](backends.md) owns paths and readiness limits.

```bash
democreate fetch-voice
```

## `backends`

Print native `found`/`absent` probe state and optional `module installed`/
`module absent` state. These are not `ready` declarations; unwired slots remain
unwired. See [backend reference](backends.md#inspecting-backend-state).

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
at a timed HTML frame/caption preview, transcript, resolved Demo and captions.
`render` and default `paper` continue through video encode and basic verification.
Use [video](video.md), [audio](audio.md), [architecture](architecture.md) and
[backends](backends.md) for behavior rather than treating command names as readiness.
Unsigned digest semantics are defined in [provenance](provenance.md).

## Image authority and resolved bundles

`build`, `render`, `gif`, and `localize` accept `--asset-root DIR`. It is both
the base for relative backgrounds and the allowed input root; by default it is
the input Demo's directory. Generated `demos/demo.json` paths remain relative to
the original workspace. Rebuild that bundle with its explicit asset root:

```bash
democreate build output/demos/demo.json --asset-root output -o output/rerender
```

Outside-root, missing or pixel-undecodable required backgrounds fail before
narration synthesis or rendering; container verification alone is insufficient.
This does not make direct low-level Pillow/capture APIs a sandbox.

The HTML surface is a timed caption/frame preview, not synthesized-audio
playback. Its narration cues are separate from the PNGs. For audible playback
render an MP4 with an implemented voice backend; `--captions` explicitly burns
the SRT in animated and static video.
