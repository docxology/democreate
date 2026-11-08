# Quickstart: offline preview first, spoken MP4 when provisioned

Requires [uv](https://github.com/astral-sh/uv). Supported package floor:
**Python ≥3.11.5**, **Pillow ≥13**; this checkout pins core Python **3.15**.
The core preview requires no ffmpeg, voice model, browser binary or display.

## 1. Install the standalone package

From the repository root:

```bash
uv venv --python 3.15
source .venv/bin/activate           # Windows: .venv\Scripts\activate
uv pip install -e .
democreate version
```

Contributors can install `.[dev]` instead; see [testing policy](testing_philosophy.md).
Optional model packages may require another compatible interpreter; see
[backends](backends.md), rather than installing every extra into the core runtime.

## 2. Author and inspect a starter

```bash
democreate init demo.json
democreate inspect demo.json
democreate build demo.json --tts silent --output output
```

Edit the declarative artifact and rebuild. `inspect` validates structure, not the
scientific accuracy of narration or the quality of a future video. Its duration
is a text estimate until generated audio supplies measured durations.

## 3. Open the timed image preview

Open `output/web/player.html` in a browser. It supports frame/chapter navigation
and caption timing, **not synthesized speech playback**. Its PNGs remain sibling
files: copy the workspace, not only the HTML.

```text
output/
  demos/       demo.json (resolved) · transcript.md
  audio/       chunk_0000.wav … (silent with this recipe)
  frames/      frame_0000.png …
  captions/    captions.srt · captions.vtt
  manifests/   render_manifest.json
  web/         player.html
```

The pipeline leaves the authored Demo unchanged. Resolved JSON uses staged
workspace-relative assets. See [image authority and rebuilding bundles](cli.md#image-authority-and-resolved-bundles)
before rendering that emitted JSON in a new workspace.

## 4. Generate a repository tour

Replace the path with an existing repository:

```bash
democreate tour /path/to/repo --title "My Project Tour" -o output/tour
```

This generates `demos/tour.json` and builds a preview by default; it does not
produce MP4 unless `--render` is passed. Python AST summaries and docstrings
supply content, not an independent assessment of the project.

## 5. Render audible MP4 after provisioning

With usable `say` or `espeak`/`espeak-ng` and ffmpeg/ffprobe on `PATH`:

```bash
democreate render demo.json -o output --tts system
democreate verify output/video/demo.mp4 --width 1920 --height 1080
```

Use an installed voice name only when appropriate to your OS. Real system TTS
must pass synthesis/transcode probing. Content verification checks media presence,
audio energy and sampled picture variance—not intelligibility or acoustic onset
accuracy. `--tts silent` can encode a video but correctly fails voiced-content
verification. See [backend readiness](backends.md), [video](video.md) and
[configuration/precedence](config.md) for themes, animation and geometry.

## 6. Prepare paper inputs or localized output

With a real PDF and poppler installed, inspect a generated paper artifact before
voiced rendering:

```bash
democreate paper /path/to/paper.pdf --no-render -o output/paper
```

[Paper workflow](paper.md) explains supplied figure roots, page staging and
heuristic extraction. [Localization](translation.md) explains independent audio
and subtitle languages, model/server prerequisites and identity translation.

## 7. Use the same core as a library

```python
from pathlib import Path
from democreate import Demo
from democreate.pipeline import build_demo
from democreate.project_paths import Workspace

source = Path("demo.json")
demo = Demo.from_file(source)
result = build_demo(demo, Workspace("output"), asset_root=source.resolve().parent)
print(result.summary())
print(result.demo_path)  # resolved timing/assets; authored demo remains reusable
```

Next: [recipes](recipes.md), [CLI reference](cli.md), [schema](schema.md),
[identified media and historical receipts](videos.md).
