# Visual gallery: synthetic renderer and diagram examples

These images are **authored synthetic illustrations**, not extracted paper
results or decoded-video evidence. The gallery generator calls the package's
frame renderer and diagram APIs. Regenerate from the repository root with:

```bash
.venv/bin/python docs/_gallery/make_gallery.py
```

Reproduction requires fixed source, assets and Pillow/FreeType environment.
Committed PNGs are not proof that the current edited generator has been run.

## Typing animation (editor frame, mid-type)

A `codebase` (editor) frame caught partway through DemoCreate's
character-by-character typing animation: the code is revealed up to the current
`cursor_typed`, pygments highlights it as it appears, the active line is
band-highlighted, and the animated caret marks the cursor. In a render this is
re-rendered per output frame at an increasing `cursor_typed` so the code types
itself in. See [video.md](video.md#typing-animation).

![An editor frame mid-typing: code revealed up to the cursor, syntax-highlighted, with a caret and a highlighted active line.](_gallery/typing.png)

## Research-paper figure scene (paper theme)

A synthetic architecture diagram is used as a figure background on the `paper`
theme, fit whole into the frame. Its caption is authored illustration text, not
extracted PDF evidence. Historical committed PNGs may retain superseded labels;
the generator source, not an old image caption, defines the next regeneration.

![Synthetic paper-theme illustration; neither the diagram nor its caption was extracted from a PDF.](_gallery/paper_figure.png)

## Title slide (midnight theme)

A title slide on the high-contrast `midnight` theme: a word-wrapped headline, a
dimmed subtitle, and a section label in the top chrome — the opening card of a
paper or codebase demo.

![A midnight-theme title slide with a headline and subtitle.](_gallery/title_slide.png)

## Architecture diagram

The left-to-right codebase architecture diagram
([`animation/diagram.py`](api.md#democreateanimationdiagram)) that a paper demo
embeds when given a `--repo`: columns grouped by top-level package, each a stack
of labeled module boxes with connectors. Carried as a full-frame
`background_image`, fit whole (contain) into the frame.

![A codebase architecture diagram: columns of module boxes connected left to right.](_gallery/architecture.png)

## Theme strip — four of the five presets

The same slide rendered across four preset themes — `dark`, `light`, `midnight`,
`paper` — selectable with `--theme` (or pinned in a `--config` YAML). The fifth
preset, **noir** (the package-wide *default*: near-black surfaces, white text, a
single red accent), is not in this strip; see it in [videos.md](videos.md) and
[config.md](config.md#theme-presets), which lists all five.

![The same slide across the dark, light, midnight, and paper theme presets.](_gallery/themes_strip.png)

## See also

- [recipes.md](recipes.md) — media workflows; [videos.md](videos.md) separates identified observations.
- [video.md](video.md) — scheduled typing, cursor, waveform and base-layout limits.
- [config.md](config.md) — themes and aspect ratios.
- [paper.md](paper.md) — how a paper becomes narrated figure/section scenes.
