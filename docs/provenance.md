# Provenance, metadata, and unsigned digest checks

DemoCreate offers three association carriers controlled by `MetadataConfig`:
visible header/footer text, editable MP4 container tags, and JSON embedded in a
lossless PNG poster. None authenticates authorship.

## Visible and container metadata

`export/overlay.py` renders selected title, section, author, source, URL, clock
and watermark fields. The footer is enabled by default; the header is optional.
`export/metadata.py` maps metadata into `title`, `artist`, `comment` and related
MP4 tags. They can be read or rewritten with ordinary media tools.

```bash
democreate render demo.json -o output --tts system --author "Your Name"
ffprobe -v error -show_entries format_tags=title,artist,comment \
  -of default=noprint_wrappers=1 output/video/demo.mp4
```

The system TTS availability probe and ffmpeg must succeed for this voiced render.

## Unsigned poster payload

`export/stego.py` places a length-prefixed JSON record in image-channel LSBs.
The payload includes tool/version, user-supplied attribution, and
`content_sha256`. `verify_provenance` compares that digest with a recomputed Demo
digest. Canonical digest fields are defined by the implementation. A reference
path does not authenticate external asset bytes.

A match is only a **content-digest consistency check**. There is no cryptographic
signature, trusted author identity, cover-pixel binding, video-byte binding or
adversarial tamper resistance. Attribution may be forged, payloads may be copied
to unrelated covers, and an editor can recompute the hash. LSB recovery requires
a lossless image; H.264 does not preserve this payload.

Actual pipeline outputs:

```text
output/provenance/poster.png
output/provenance/poster_signed.png
output/provenance/provenance.json
```

`poster_signed.png` is a retained filename, **not a digital signature**. No
transmission-bookend PNGs are emitted.

```bash
democreate stego output/provenance/poster_signed.png
democreate stego output/provenance/poster_signed.png --demo output/demos/demo.json
```

Use the emitted resolved Demo when render configuration changes geometry or
stages assets. The latter command returns a mismatch status when the embedded
digest does not match; success does not prove who made the poster, that its pixels
came from that Demo, or that an MP4 matches it.

See [config.md](config.md), [cli.md](cli.md#stego), and
[recipes.md](recipes.md#10-branded-4k-render-with-unsigned-provenance).
