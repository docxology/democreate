# Recipes: compose the CLI into bounded media workflows

Start with the [quickstart](quickstart.md) for installation and an authored
`demo.json`. Paths below stand for inputs you must supply. [CLI](cli.md) owns
flags/defaults, [configuration](config.md) owns precedence, and
[backends](backends.md) owns implemented paths and runtime prerequisites.

Spoken MP4 recipes require a usable selected TTS and ffmpeg/ffprobe; paper
ingestion additionally needs poppler. `--voice Samantha` is a macOS example,
not a portable voice name. `democreate backends` reports dependency/probe state,
not complete render readiness.

## 1. Software demo (codebase tour → HD video)

Point `tour` at a repository to auto-generate a narrated codebase walkthrough,
then `render` it to an animated HD MP4 with a real spoken voiceover. `tour`
writes `output/demos/tour.json`; you edit that artifact and re-render as needed.

```bash
democreate tour /path/to/repo --title "My Project Tour" --output output
democreate render output/demos/tour.json --output output --tts system --voice Samantha
```

Or hand-author a demo from the starter artifact and render it directly:

```bash
democreate init demo.json          # scaffold a small, valid demo
democreate inspect demo.json       # validate + summarize before rendering
democreate render demo.json --tts system
```

## 2. Research-paper demo (PDF + figures + codebase)

Extract candidate abstract/captions/sections from a supplied PDF, add figures,
selected pages and an optional Python architecture diagram, then render. These
are heuristic extractions requiring review against the source, not a guaranteed
correct reading. See [paper.md](paper.md).

```bash
democreate paper paper.pdf \
  --repo /path/to/code \
  --figures /path/to/figs \
  --pages 1,2 \
  --theme paper \
  --voice Samantha
```

Emit only the demo artifact (no render) to inspect or tweak it first:

```bash
democreate paper paper.pdf --no-render        # writes output/demos/paper.json
```

## 3. Vertical 9:16 social cut

`--aspect` reshapes the output to a named aspect-ratio preset. Use `9:16` for a
vertical reel/short; the demo is re-sized and rendered at that geometry. Presets:
`16:9`, `9:16`, `1:1`, `4:3`, `4:5` (see [config.md](config.md#aspect-presets)).

```bash
democreate render demo.json --aspect 9:16 --tts system
democreate render demo.json --aspect 1:1            # square
# After an existing complete paper build, reuse its resolved staged bundle:
democreate render output/demos/demo.json --asset-root output \
  -o output/vertical --aspect 9:16 --theme paper
```

## 4. Themed render

Pick a preset with `--theme` or create a config before using it. CLI defaults
still override selected YAML settings; see [precedence](config.md#using-a-config).
Choose an installed voice appropriate to the host (or omit the voice flag).

```bash
democreate render demo.json --theme midnight --animation-fps 24
democreate config my_theme.yaml --theme midnight
# Edit my_theme.yaml, then use it:
democreate render demo.json --config my_theme.yaml --tts system
```

## 5. GIF preview + poster thumbnail

`gif` builds and samples representative per-chunk stills at uniform GIF cadence;
it is not the action-scheduled MP4 animation or a speech player. `thumbnail`
renders a plain title/poster still (not a payload-bearing poster).

```bash
democreate gif demo.json --gif demo.gif --fps 8 --theme dark
democreate thumbnail demo.json --out poster.png --theme midnight \
  --subtitle "narrated HD demo"
```

## 6. YouTube chapters

Rendering attempts chapter text and MP4 chapter embedding as best-effort exports.
Inspect warnings and output rather than treating a completed MP4 as proof that
chapter embedding succeeded. When present, copy the text into your description:

```bash
democreate render demo.json --output output --tts system
cat output/chapters/youtube_chapters.txt          # 0:00 Intro · 0:12 …
```

The embedded markers are verifiable with `ffprobe -show_chapters output/video/demo.mp4`.

## 7. Typing-animation demo

Typing reveal is enabled by default for editor actions. Scheduled playback uses
each action's trigger and `duration_ms`, not a fixed fraction of a chunk.
The starter has no cursor coordinates; a cursor/ripple only appears when supplied.

```bash
democreate init demo.json
democreate render demo.json --tts system          # scheduled typing reveal
```

Disable reveal with `video.typing: false`; tune pace using the action's
`duration_ms`. The removed `video.typing_fraction` YAML field is rejected.
See [the action-duration example](video.md#typing-animation) and
[config.md](config.md).

## 8. Optional LLM narration (env-gated, library-only)

The deterministic template narrator is always the default — the CLI never calls
an LLM. Polishing narration with an OpenAI-compatible endpoint is a deliberate
**library-only** surface; rewritten text may lose trigger words and change
estimated action anchoring. Set the endpoint/key explicitly and review its text
before replacing narration ([narration source guide](../src/democreate/narration/README.md)):

```bash
export OPENAI_API_KEY="sk-…"                       # or DEMOCREATE_LLM_API_KEY
export DEMOCREATE_LLM_BASE_URL="https://api.openai.com/v1"   # optional override
```

```python
from democreate.narration.llm import get_narrator
from democreate import Demo

demo = Demo.from_file("demo.json")

narrator = get_narrator()                      # env-configured, no pip extra
texts = [c.text for c in demo.iter_chunks()]
polished = narrator.rewrite_chunks(texts, context=demo.title)
```

It uses only the standard library (`urllib`) — **zero pip dependencies** — and the
network calls are guarded by the key's presence. See [backends.md](backends.md#optional-llm-narration).

## 9. Verify a rendered video

`render`/`paper` content-verify by default. To independently assert any MP4 is a
real, non-silent, non-black video of the expected size:

```bash
democreate verify output/video/demo.mp4 --width 1920 --height 1080 --min-duration 5
```

## 10. Branded 4K render with unsigned provenance

Render at a true **4K** tier (`--resolution 2160p` — everything scales to the
frame height, so it's genuinely higher resolution), brand it with an on-screen
**author** + **watermark** (footer bar + MP4 `artist` tag + unsigned provenance),
then verify the steganographic payload against the source demo. The payload-bearing poster
lives in `output/provenance/` because LSB steganography survives only in lossless
PNG, not the H.264 pixels — see [provenance.md](provenance.md).

```bash
democreate render demo.json \
  --resolution 2160p \
  --author "Daniel Ari Friedman" \
  --watermark "© 2026" \
  --tts system

# read the container tags ffmpeg muxed in
ffprobe -v error -show_entries format_tags=title,artist,comment \
  -of default=noprint_wrappers=1 output/video/demo.mp4

# verify the unsigned provenance matches the resolved rendered demo (exit 0 = match)
democreate stego output/provenance/poster_signed.png --demo output/demos/demo.json
```

For full control over `crf`/`preset` and the `metadata:` block, write a commented
config first:

```bash
democreate config democreate.yaml --theme dark
democreate render demo.json --config democreate.yaml --resolution 2160p
```

## See also

- [cli.md](cli.md) — every command and flag.
- [gallery.md](gallery.md) — synthetic renderer illustrations, separate from decoded video.
- [config.md](config.md) — themes, resolution tiers, aspect presets, typing/cursor settings.
- [provenance.md](provenance.md) — on-screen bars, container tags, unsigned steganography.
- [paper.md](paper.md) · [video.md](video.md) · [audio.md](audio.md) · [backends.md](backends.md)
