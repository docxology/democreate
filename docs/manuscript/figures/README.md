# Figure Sources: Schematics, Synthetic States, and Recorded Samples

`make_figures.py` uses committed repository inputs, including local
`paper_fig.png`, and writes here plus root `output/figures/`. No sibling project
is searched or written. `graphical_abstract.py` generates the cover separately.

## Conceptual and synthetic illustrations

The cover, architecture, paper-flow and attribution diagrams explain construction
boundaries; none is an empirical validation result. The attribution schematic
distinguishes selected overlapping field sets and unsigned consistency checks,
not signatures or authenticated identities.

`frame_*.png` are synthetic `render_frame` illustrations, not video extractions.
`frame_paper.png` composes the retained `paper_fig.png` input; its generation does
not establish the background's extraction date or publication status. The waveform
is generated from an amplitude-modulated tone, not speech.

Code illustrations retrieve source with `inspect.getsource`: the editor uses
`democreate.schema.Action.to_dict`; the typing reading panel uses
`democreate.assembly.compositor.Timeline.entry_at_ms`. The latter accompanies three
contain-fit synthetic `cursor_typed` previews and character-count bars at
25/55/100%, not captured animation or measured speech alignment. The five-theme
grid has a sixth comparison-key tile; its compact code is schematic.

## Source-bound observations, not measurements of later edits

`latency.png` uses `data/benchmarks-0.8.0.json` with separate units for build
wall clock and whole-render throughput. It retains one silent starter/host/source
observation, not neural-TTS performance or a controlled historical speedup.
`video_stills.png` is a package-only 3×2 montage of six decoded PNGs whose hashes
are checked against `data/release-0.8.0.json`. Labels are requested seeks at cue
midpoints, not independent event/acoustic annotations. Preserve the original raw
stills and source record; recomposing them does not validate a new MP4.

## Generator dimensions and repository-root commands

`make_figures.py` owns `CANVAS = (1600, 900)` and
`WAVE_CANVAS = (1600, 300)`; `graphical_abstract.py` owns
`W, H = 2400, 1350`. `figure_layout.py` supplies shared bounded text/card
layout. These are source-defined targets, not a fresh inspection of PNG bytes.

Regenerate from the repository root with
`.venv/bin/python docs/manuscript/figures/make_figures.py` and
`.venv/bin/python docs/manuscript/figures/graphical_abstract.py`.
Regeneration and manuscript gates must run before asserting that generated files
match source; source edits alone do not establish that correspondence.
