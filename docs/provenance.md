# Provenance, metadata, and steganography

DemoCreate v0.6 attaches provenance to a render through **three carriers**, all
driven by one `MetadataConfig` ([config.md](config.md#metadataconfig-on-screen-container-hidden-provenance)):

1. **On-screen metadata bars** — visible top/bottom overlays burned into every
   frame (author, source, URL, a running clock, a watermark).
2. **MP4 container tags** — standard `title`/`artist`/`comment`/`date` metadata
   muxed into the video container and read by players and `ffprobe`.
3. **Steganographic signed provenance** — a content-hashed JSON record LSB-hidden
   inside **lossless PNG sidecars** (a poster + transmission bookends).

These are complementary, not redundant: the bars are visible, the container tags
survive copying/re-muxing but are trivially editable, and the steganographic
payload is tamper-evident but only lives in the lossless PNGs (not the H.264
pixels — see the honesty note below).

All three are wired into the render by `pipeline._embed_provenance()` and are on
by default; each can be disabled in `MetadataConfig`.

---

## 1. On-screen metadata bars

`export/overlay.py` draws two slim, translucent broadcast-style bars onto each
frame — like a station bug + lower-third strap pinned onto live video. They are
pure Pillow (no ffmpeg) and scale proportionally at any resolution. Each function
is a silent no-op when its fields are empty, so it is always safe to call.

| Bar | Function | Position | Content |
|-----|----------|----------|---------|
| **Header** | `draw_header` | Top ~6.2–10.5% of frame (just below the chrome + progress bar) | Demo **title** (left), current **section** (right, in accent). |
| **Footer** | `draw_footer` | Lowest ~4.5% (above the waveform band) | `author · source` (left), URL (center/right), running **clock** + **watermark** (far right, in accent). |

The footer is **on by default** and shows a running clock; the header is off by
default. Both are toggled by `MetadataConfig.header` / `.footer`, and the clock by
`.show_clock`. The animator resolves the per-frame text via
`overlay.from_metadata_config(...)` (with the live `format_clock(t_ms, total_ms)`
readout such as `"1:23 / 4:56"`) and composites the bars per frame in
`_draw_overlays`.

Because the bars are burned into the pixels, **they survive the H.264 encode** —
they are the visible half of the provenance story. To enable the header and a
watermark in YAML:

```yaml
metadata:
  author: "Daniel Ari Friedman"
  source: "github.com/you/project"
  url: "https://your-domain.example.com"
  watermark: "© 2026"
  header: true       # top title · section bar (off by default)
  footer: true       # bottom provenance bar (on by default)
  show_clock: true   # running M:SS / M:SS readout in the footer
```

`--author` and `--watermark` on `render` set those two fields without a config
file (see [cli.md](cli.md#render)).

---

## 2. MP4 container tags

`export/metadata.py` turns a `Demo` + `MetadataConfig` into standard container
metadata and muxes it into the MP4 **without re-encoding** (stream copy):

- `build_tags(demo, meta, version=...)` — pure. Maps `title` (`meta.title` →
  `demo.title`), `artist` (`meta.author`), `date` (`meta.date`), `comment` and
  `description` (a `"made with DemoCreate <version>"` credit plus any `source` /
  `url`). Empty values are dropped, so blank tags are never written.
- `to_ffmetadata(tags)` / `ffmpeg_metadata_args(tags)` — pure helpers that render
  the tags as a round-trippable `;FFMETADATA1` document or a flat
  `-metadata k=v` argv fragment.
- `embed_tags(mp4_in, mp4_out, tags)` — guarded. Runs
  `ffmpeg -i in <-metadata …> -codec copy out`, copying the streams verbatim and
  replacing the global metadata. Raises `BackendUnavailableError` if `ffmpeg` is
  absent and `RenderError` on a non-zero exit.

`_embed_provenance` calls this when `MetadataConfig.container_tags` is true and
ffmpeg is present, writing into a temp `*_meta.mp4` and atomically replacing the
output.

**Read the tags back** with `ffprobe`:

```bash
ffprobe -v error -show_entries format_tags=title,artist,comment,date \
  -of default=noprint_wrappers=1 output/video/demo.mp4
```

Container tags survive copying and re-muxing, but anyone with ffmpeg can rewrite
them — they are a credit line, not a tamper-evident seal. For that, use the
steganographic payload below.

---

## 3. Steganographic signed provenance

`export/stego.py` hides a JSON provenance record in the **least-significant bits**
of an image's R, G, B channels — one bit per channel per pixel, prefixed by a
4-byte big-endian length header. The payload is plain JSON (this is provenance,
not encryption: anyone with the module can read it).

### Payload contents

`build_provenance(demo, author=, version=, extra=)` returns a flat record. As
embedded by the pipeline, it carries:

| Key | Value |
|-----|-------|
| `tool` | `"democreate"` |
| `version` | DemoCreate version (`0.6.2`) — sourced from `democreate.__version__` |
| `title` | Demo title |
| `author` | `MetadataConfig.author` |
| `scenes` | Scene count |
| `chunks` | Chunk count |
| `content_sha256` | SHA-256 over the demo's **stable content** (the tamper seal) |
| `created_hint` | The `date`, if supplied |
| `date` / `source` / `url` | Passed through `extra` from `MetadataConfig` |

The record is JSON-encoded (`sort_keys=True`) and embedded with `embed()`.

### Where it lives — and the honesty note

LSB pixel steganography survives **only in a lossless container (PNG)**. An H.264
(or any lossy) re-encode re-quantizes every pixel and **destroys the hidden bits
completely**. So DemoCreate does **not** put this payload in the video pixels — the
MP4 carries container tags instead. The signed payload is written to **lossless
PNG sidecars**:

```
output/provenance/poster.png          # the rendered poster (clean)
output/provenance/poster_signed.png   # the poster with the LSB payload embedded
output/provenance/provenance.json     # the same record, in the clear
```

(`poster_signed.png` is the poster; the same payload is also embedded in the
first/last "transmission bookend" frames.) Do not expect a provenance payload to
round-trip through a rendered `.mp4` — that's a property of LSB steganography, not
a DemoCreate limitation, and the module says so plainly.

### Why the content digest is tamper-evident

`content_sha256` is **not** a hash of the full demo JSON. Rendering mutates the
demo (audio paths, synced timestamps), so hashing the whole serialization would
make a freshly-authored demo fail to verify. Instead `_content_digest(demo)`
hashes only the **stable content and geometry** — title, width, height, and the
scene/chunk/action structure with narration text and action params — explicitly
excluding `audio_path`, `start_ms`, `timestamp_ms`, and `duration_ms`.

This makes the pairing tamper-evident in a useful way:

- `verify_provenance(image, demo)` is **`True`** when checked against the same
  resolved demo that the render signed (for normal renders this is the source
  demo; when flags or config override geometry, use `output/demos/demo.json`).
- It is **`False`** if the demo's content was edited (different title, scene text,
  actions, or geometry…), because the recomputed digest no longer matches the embedded one.
- A missing or corrupt payload also yields **`False`**.

So the signed poster proves *"this poster was generated from exactly this demo
content"* and detects edits to the content.

### Verify it — `democreate stego`

Extract (and optionally verify) the payload in a signed PNG:

```bash
# Just dump the embedded provenance JSON
democreate stego output/provenance/poster_signed.png

# Verify the payload matches the resolved rendered demo (exit 0 = match, exit 1 = mismatch)
democreate stego output/provenance/poster_signed.png --demo output/demos/demo.json
```

`stego` prints the decoded record; with `--demo` it recomputes the content digest
and reports `✓ provenance matches the demo` or `✗ provenance does NOT match the
demo`, exiting non-zero on a mismatch. Editing the demo's content and re-running
with `--demo` flips the result to a mismatch — that's the tamper-evidence in
action. See [cli.md](cli.md#stego).

To prove the round-trip and the tamper-detection from the API:

```python
from PIL import Image
from democreate.export.stego import extract_provenance, verify_provenance
from democreate.schema import Demo

img = Image.open("output/provenance/poster_signed.png").convert("RGB")
demo = Demo.from_json(open("demo.json").read())

print(extract_provenance(img))        # the embedded record
print(verify_provenance(img, demo))   # True for the original demo
```

---

## End-to-end: a signed render

```bash
# Render with on-screen author + watermark, container tags, and a signed poster
democreate render demo.json \
  --resolution 1080p \
  --author "Daniel Ari Friedman" \
  --watermark "© 2026" \
  --tts system

# 1. read the container tags
ffprobe -v error -show_entries format_tags=title,artist,comment \
  -of default=noprint_wrappers=1 output/video/demo.mp4

# 2. verify the steganographic provenance against the source demo
democreate stego output/provenance/poster_signed.png --demo demo.json
```

For a branded 4K variant of this, see the
[branded, signed 4K render recipe](recipes.md#branded-signed-4k-render).

## See also

- [config.md](config.md#metadataconfig-on-screen-container-hidden-provenance) — the full `MetadataConfig` table.
- [cli.md](cli.md#render) — `render --author/--watermark`; [`stego`](cli.md#stego).
- [video.md](video.md#on-screen-metadata) — the header/footer bars in the render.
- [backends.md](backends.md) — ffmpeg carries the tags; overlay/stego are pure Pillow.
