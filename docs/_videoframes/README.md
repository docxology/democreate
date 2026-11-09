# Identified candidate frames and historical stills

`candidate-0.8.0/` contains six decoded PNGs from the real Kokoro `af_heart`
3840×2160 candidate MP4. Source/input/model/video/frame identities, extraction
receipt and requested ffmpeg seek offsets are in `data/release-0.8.0.json`.
Seek offsets are not independently annotated event/onset timestamps.

`visual-refresh-2026-11-08/` retains four changed decoded samples from the refreshed
cover/theme/illustrative-code showcase. Two byte-identical samples reuse their
`candidate-0.8.0/` paths. That earlier six-frame selection, MP4 identity and
bounded extraction receipt are in `data/visual-refresh-2026-11-08.json`.

`deep-audit-2026-11-09/` contains the later six montage samples and an additional
opening-title check. `data/showcase-2026-11-09.json` binds the fresh source,
qualified outro, updated graphic, model/runtime, caption and MP4 identities.
The graphical abstract was also inspected as actually encoded, not just as PNG.

The older top-level stills predate the 2026-11-07 repair. Original extraction
dates and source-video digests are unrecorded; their embedded suite counts and
narration are obsolete, not current gate results. They remain preserved.

Re-extract only from an identified fresh render and retain its source/input/tool
identity and extraction timestamps. The canonical package recipe remains Kokoro
`af_heart` at 2160p; the curated and template paper demos are distinct artifacts.
