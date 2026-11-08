# Composition and Configurability {#sec:composition}

A demo's content is authored in its `Demo` value, while its look, audio assembly and motion are governed by serializable `RenderConfig` data ([@sec:architecture]). A config selects settings; it is not sufficient alone to reproduce external asset bytes, voices, model files or encoder builds. For example, `democreate render demo.json --config my_theme.yaml --asset-root ./assets` explicitly selects the input image root as well as configuration; a named theme can instead be selected with `--theme paper`. `RenderConfig` bundles `Theme`, `AudioConfig`, `VideoConfig` and `MetadataConfig` ([@sec:provenance]). `democreate config out.yaml` writes commented defaults for commonly tuned fields. Existing illustrations in this chapter are historical assets, reviewed 2026-11-07, with extraction dates unrecorded; they are not current render or legibility-study receipts.

## Themes, Fonts, and Syntax Highlighting

The `Theme` dataclass holds RGB surface, text, accent and syntax colors, plus six font ratios expressed as fractions of frame height (title, subtitle, code, terminal, caption and section). `scaled_font` in `animation/fonts.py` multiplies a ratio by height and loads Pillow's bundled scalable face, avoiding host-font discovery. For example, `0.094` corresponds to about 101 pixels at 1080 lines. Proportional sizing is not a guarantee that arbitrary content will fit or remain legible at every geometry. Pygments [@pygments2024] supplies syntax tokens mapped to the theme's `syn_*` palette when available; otherwise the renderer draws plain text coloring.

**Five** presets ship in `THEMES`. The default is **noir**: near-black `(12,12,14)` surfaces, bright-white `(242,242,244)` text, and a *single* refined red `(224,49,57)` as the only chroma — spent sparingly on the played waveform, the cursor, code keywords, the section pill / heading rule, the line-highlight bar, and the top-edge progress line. Its code syntax is monochrome-with-red (keywords red, names white, strings gray, comments dim), so the eye reads structure rather than a rainbow. Alongside noir ship the classic `dark` (slate editor, blue accent), a high-contrast `light`, a deep-blue `midnight`, and an academic `paper` look with warm paper-white slides intended for research-paper demos ([@sec:paper]). [@fig:themes] renders the *same* editor frame under all five, making the point that a theme change is a data change, not a code change — the layout, fonts, and highlighting are identical; only the palette differs. Partial themes are supported: `RenderConfig.from_dict` merges a user's overrides onto a named base, so a config can recolor a single accent while inheriting everything else.

![One synthetic editor frame rendered under all five preset themes — `noir` (the default), `dark`, `light`, `midnight`, and `paper`. Layout, fonts, pygments highlighting, the section pill, and the caption are identical across cells; only the `Theme` palette changes, illustrating that the look is configurable data rather than code. Noir carries the design in black and white with a single red accent.](figures/themes.png){#fig:themes}

Beyond code frames, a `SLIDE` frame draws a centered title, accent underline and optional subtitle, as in [@fig:frame_title]. A `background_image` is initially fit whole into the content area by contain, with section and caption bands outside it. This fit applies before any explicit camera scale or optional Ken Burns transformation; neither a configured zoom nor an arbitrary final composition has an unconditional no-crop guarantee ([@sec:paper]).

![A `SLIDE` title card rendered by `SyntheticRenderer`: a large TrueType title sized by the theme's `title_ratio`, an accent underline, a subtitle in the dim color, and a section pill in the top chrome. The same slide renderer composes intro, outro, and section-divider frames.](figures/frame_title.png){#fig:frame_title}

## Presentation Slides: Bullets and Stat Cards

The `SLIDE` frame supports two additional presentation layouts driven by `FrameState` data: a **bullet slide** (`bullets`) with accent markers and a **stat-card slide** (`stats`) with number/label pairs. Both use the theme palette and core Pillow rendering. Their claims and numbers are authored content, not measurements performed by rendering them. A displayed coverage threshold is a gate, not achieved coverage, and a displayed resolution is not evidence that a video was freshly encoded at that size. The showcase uses both layouts ([@sec:evaluation]).

## Contain Layout and Its Limits

The default composition aims to retain image context: paper figures and pages are initially fit by contain rather than cover, and captions and waveform have reserved bands. This design is useful for information-dense material but does not ensure that every possible input is shown in full.

**Ken Burns is off by default** (`ken_burns=False`); its configured `ken_burns_zoom` defaults to `1.06`, not a universal maximum. When enabled it enlarges and center-crops flagged frames. Independently, authored camera scale above 1 zooms content before the renderer redraws the fixed section, caption and waveform bands. Background contain fitting therefore does not prevent an intentional camera crop. Code autosizing chooses a font within a legibility floor and ceiling, then wraps long lines into continuation rows; the editor stops drawing when available vertical space is exhausted. Dense code, long captions and narrow geometries still require content selection and inspection. Splitting a long example into scenes is preferable to claiming that wrapping guarantees complete visibility.

## Motion: Waveform, Progress, Transitions, and Ken Burns

`VideoConfig` controls geometry and motion. The animator draws a waveform and progress line keyed to the assembled clip timeline, not measured word onsets ([@sec:implementation]). The progress line is placed at the top edge, while captions and waveform occupy lower bands. Explicit camera scale applies before the synthetic renderer redraws its fixed bands; Ken Burns is a later transformation of the rendered base and can also transform those base-frame elements. Crossfades blend adjacent scenes during `transition_ms`; overlays drawn afterward include the current progress/waveform and optional metadata. These ordering rules do not establish a general no-overlap law for every user configuration. `AnimationConfig.from_video` derives settings from `VideoConfig`, theme colors and audio padding; each motion feature is independently configurable.

## Typing Reveal and the Animated Cursor

In the pipeline's scheduled playback, code appears only after its action trigger and is progressively revealed over that action's duration. The animator requests `TimelineEntry.state_at_ms` and sends changing snapshots through the same synthetic renderer, including syntax coloring. This is distinct from the lower-level frame-state fallback: there `cursor_typed` grows across the first `typing_fraction` (default `0.7`) of a chunk window. [@fig:typing_filmstrip] illustrates partial text snapshots, not a freshly observed action/acoustic alignment. Neither path proves that a visible keystroke coincides with a spoken word.

![One `FrameState` re-rendered at `cursor_typed` of 25%, 55%, and 100% (left to right). The animator emits the intermediate frames between these snapshots, so code types in character-by-character with pygments re-highlighting the partial source and a caret at the typing head. Layout, theme, and gutter are identical across panels; what changes is how much of the source has been "typed", the caret position, and — once typing reaches it — the highlighted line.](figures/typing_filmstrip.png){#fig:typing_filmstrip}

The **animated cursor** draws a pointer from the scheduled state. Pointer actions can interpolate over their durations; a triggered `click` can produce an expanding, fading ripple for 600 ms. In the lower-level frame-state fallback the ripple uses chunk start instead. These are synthetic indications of authored actions, not proof that a real GUI was clicked where the narration says it was. The `cursor` flag controls the overlay.

## Aspect-Ratio Presets and Resolution Tiers

Named aspect presets in `ASPECTS` include `16:9` (1920×1080), `9:16` (1080×1920), `1:1` (1080×1080), `4:3` (1440×1080) and `4:5` (1080×1350). `RenderConfig.set_aspect` sets video dimensions, and both `render` and `paper` accept `--aspect`. Height-relative sizing permits retargeting without changing the schema, but a square or vertical layout can wrap differently or exhaust vertical space; inspect and, when necessary, re-author the content for the chosen geometry.

Named 16:9 tiers in `RESOLUTIONS` are `720p` (1280×720), `1080p` (1920×1080), `1440p` (2560×1440) and `2160p`/`4k` (3840×2160), selectable through `RenderConfig.set_resolution` or `render --resolution`. Text and chrome are re-rasterized at the requested size rather than upscaled, but low-resolution background assets do not gain source detail. `VideoConfig.crf` (default `18`) and `preset` are forwarded to ffmpeg's encode path. Those are quality/compression settings, not a measured perceptual-quality result or a guarantee of identical encoded bytes across machines.

## On-Screen Metadata Bars

`export/overlay.py` draws optional metadata bars: a header with title/current section and a footer with selected author/source/URL, clock and watermark fields. The footer is enabled by default; the header is opt-in. These visible labels share some `MetadataConfig` inputs with MP4 tags and the PNG payload, but the three outputs have different field sets and encodings; they are not identical authenticated carriers. Empty fields are omitted, while enabled clocks or supplied labels can still be drawn. The unsigned association model and its limits are developed in [@sec:provenance].

## Export: Chapters, Posters, and GIFs

Chapter exports include YouTube text and ffmetadata muxed into an MP4 when ffmpeg is available. Boundaries derive from the clip timeline and its configured gaps; current output must be inspected rather than inferred from historical chapter totals. The showcase has 15 authored scenes, not the earlier claimed 14.

## Audio: Pacing, Normalization, and Fades

`AudioConfig` controls lead, inter-chunk and trail silences and the normalization/fade passes. The ffmpeg `loudnorm` filter targets integrated −16 LUFS and −1.5 dBTP; that configured target is not a measured result. Historical mean volume of −15.5 dB is a different statistic and cannot verify integrated loudness. Integrated LUFS requires its own measurement.
