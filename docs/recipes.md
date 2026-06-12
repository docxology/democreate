# Recipes

A cookbook of runnable `democreate` commands for the common jobs. Each recipe is
a short intro plus a copy-paste command block. Every flag here is real — see
[cli.md](cli.md) for the full reference, and run any command with `--help`.

Real voice and real video need only **OS binaries** (no pip install): a usable
system TTS (`say` on macOS, `espeak`/`espeak-ng` on Linux) and `ffmpeg` on
`PATH`. The paper recipes additionally need **poppler**
(`pdfinfo`/`pdftotext`/`pdftoppm`). Run `democreate backends` to see what's
available.

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

Turn a paper PDF into a narrated walkthrough: a title card, the **real abstract**
(the table of contents is skipped), a **structure** scene listing the paper's
sections, figure scenes narrating the **real figure captions** (`"Figure N: ..."`),
selected PDF pages, and — with `--repo` — a codebase architecture diagram. The
`paper` theme gives slides a warm academic look. See [paper.md](paper.md).

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
democreate paper  paper.pdf --no-render             # then render a vertical cut:
democreate render output/demos/paper.json --aspect 9:16 --theme paper
```

## 4. Themed render

Pick a preset theme with `--theme` (`noir` — the default — `dark`, `light`,
`midnight`, `paper`), or take full control with a `--config` YAML that pins
colors, fonts, audio pacing, and motion. `--config` overrides `--theme`;
`--voice`/`--tts` still apply on top.

```bash
democreate render demo.json --theme midnight --animation-fps 24
democreate render demo.json --config my_theme.yaml --voice Daniel
```

Generate a starting YAML from the defaults, then edit it:

```bash
.venv/bin/python -c "from democreate.config import RenderConfig; \
print(RenderConfig.preset('midnight').to_yaml())" > my_theme.yaml
```

## 5. GIF preview + poster thumbnail

`gif` builds the demo and exports an animated GIF preview (evenly sampled frames);
`thumbnail` renders a designed poster/title still — both great for a README or a
social card.

```bash
democreate gif demo.json --gif demo.gif --fps 8 --theme dark
democreate thumbnail demo.json --out poster.png --theme midnight \
  --subtitle "narrated HD demo"
```

## 6. YouTube chapters

Chapters are written **automatically** on every `render`/`paper`: a YouTube
chapter file (`output/chapters/youtube_chapters.txt`) plus chapter markers
embedded directly into the MP4 (via ffmpeg `ffmetadata`, one per scene). Just
render, then copy the chapter text into your video description:

```bash
democreate render demo.json --output output --tts system
cat output/chapters/youtube_chapters.txt          # 0:00 Intro · 0:12 …
```

The embedded markers are verifiable with `ffprobe -show_chapters output/video/demo.mp4`.

## 7. Typing-animation demo

The character-by-character typing animation is **on by default** for editor
scenes whose chunks carry a `type_code` or `create_file` action — exactly what
`init` scaffolds. So a plain render already types the code in, with the animated
cursor and click ripple:

```bash
democreate init demo.json
democreate render demo.json --tts system          # types the code in, animated cursor
```

Tune or disable it via `--config` (`video.typing`, `video.typing_fraction`,
`video.cursor`) — see [config.md](config.md#videoconfig-geometry-motion) and
[video.md](video.md#typing-animation).

## 8. Optional LLM narration (env-gated)

The deterministic template narrator is always the default. To *optionally* polish
or generate narration with an OpenAI-compatible endpoint, set an API key in the
environment; with no key configured the library falls back to the template, so
this never breaks a render. Configuration is purely via environment variables
([`narration/llm.py`](api.md#democreatenarrationllm)):

```bash
export OPENAI_API_KEY="sk-…"                       # or DEMOCREATE_LLM_API_KEY
export DEMOCREATE_LLM_BASE_URL="https://api.openai.com/v1"   # optional override
```

It uses only the standard library (`urllib`) — **zero pip dependencies** — and the
network calls are guarded by the key's presence. See [backends.md](backends.md#optional-llm-narration).

## 9. Verify a rendered video

`render`/`paper` content-verify by default. To independently assert any MP4 is a
real, non-silent, non-black video of the expected size:

```bash
democreate verify output/video/demo.mp4 --width 1920 --height 1080 --min-duration 5
```

## 10. Branded, signed 4K render

Render at a true **4K** tier (`--resolution 2160p` — everything scales to the
frame height, so it's genuinely higher resolution), brand it with an on-screen
**author** + **watermark** (footer bar + MP4 `artist` tag + signed provenance),
then verify the steganographic payload against the source demo. The signed poster
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

# verify the signed provenance matches the resolved rendered demo (exit 0 = match)
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
- [gallery.md](gallery.md) — real frames these commands produce.
- [config.md](config.md) — themes, resolution tiers, aspect presets, typing/cursor settings.
- [provenance.md](provenance.md) — on-screen bars, container tags, signed steganography.
- [paper.md](paper.md) · [video.md](video.md) · [audio.md](audio.md) · [backends.md](backends.md)
