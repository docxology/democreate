# Examples

Worked DemoCreate artifacts you can render and inspect.

## `make_showcase.py` → `democreate_showcase.json` (the definitive demo)

The **canonical package demo**: DemoCreate's definitive showcase, authored as a
DemoCreate `Demo` and exercising *every* renderable surface. **Fourteen scenes** —
(1) hero title card, (2) the one-glance graphical abstract, (3) a **bullet slide**
*"A demo is a value, not a recording"*, (4–6) three **code scenes** typing in
(`schema.py` spine, `tts.py` deterministic backends, `sync.py`
audio-as-ground-truth), (7) a meta **bullet slide** *"What you are seeing"*,
(8) the themes strip, (9) a real research-paper **figure** (fit-contained, whole),
(10) the architecture diagram, (11) a **stat-card slide** *"by the numbers"*
(671 collected tests · 7 subsystems · 5 themes · 4K · 0 binary deps), (12) a provenance **bullet
slide**, (13) a **terminal** render+verify, (14) the outro. 3840×2160, no-crop
(figures fit whole, code autosizes, Ken Burns off), a moving waveform + bottom
metadata bar throughout.

The **bullet slides** and **stat-card slides** are new in `v0.6.1`
(`FrameState.bullets` / `FrameState.stats`, set via `scene.context["bullets"]` /
`scene.context["stats"]`).

```bash
# 1. build the declarative artifact
uv run python examples/make_showcase.py      # writes examples/democreate_showcase.json

# 2. render the definitive showcase to a verified 4K MP4
uv run democreate render examples/democreate_showcase.json -o output \
  --voice Samantha --resolution 2160p --author "Daniel Ari Friedman" \
  --watermark "github.com/docxology/democreate"
uv run democreate verify output/video/demo.mp4 --width 3840 --height 2160
```

`render` produces `output/video/demo.mp4` — a 129.7-second 4K H.264/AAC video
with **14 chapters**, container tags (`title="DemoCreate — The Showcase"` /
`artist="Daniel Ari Friedman"`), and a signed steganographic provenance poster.
The build self-verifies it (real streams, non-silent audio, non-black frames).
Full write-up: [`../docs/videos.md`](../docs/videos.md).

## `make_intro_demo.py` → `democreate_intro.json` (the earlier intro)

The earlier **dogfood**: DemoCreate's own introduction, authored as a DemoCreate
`Demo`. Six scenes (title → spine → backends → sync → terminal → outro), nine
narration chunks, trigger-word-anchored actions, 1920×1080 @ 30fps. The showcase
above **supersedes** it as the canonical package demo; the intro still renders.

```bash
# 1. build the declarative artifact
python examples/make_intro_demo.py            # writes examples/democreate_intro.json

# 2a. deterministic build (no heavy deps): silent audio, frames, captions, player
democreate build examples/democreate_intro.json -o output
open output/web/player.html

# 2b. real HD video with a real spoken voiceover (needs `say`/`espeak` + ffmpeg)
democreate render examples/democreate_intro.json -o output --voice Samantha
democreate verify output/video/demo.mp4 --width 1920 --height 1080
```

`render` produces `output/video/demo.mp4` — a ~67-second 1080p H.264/AAC video.
The build self-verifies it (real streams, audio covers video, non-silent audio,
non-black frames); `verify` re-checks any video file independently.

### Voices

`--voice` is the system voice name. On macOS list them with `say -v '?'`
(e.g. `Samantha`, `Daniel`, `Karen`, `Alex`); on Linux `espeak` voices apply.

### Why this matters

The intro is not a screen recording — it is a **value**. Edit
`make_intro_demo.py` (or the JSON), re-run `render`, and the video updates. You
never re-record. That is the whole thesis, demonstrated on the tool itself.
