# Manuscript figures

`make_figures.py` uses committed repository inputs, including local
`paper_fig.png`, and writes here plus root `output/figures/`. No sibling project
is searched or written. `graphical_abstract.py` generates the cover separately.

`frame_*.png` are rendered synthetic illustrations, not extracted video evidence.
The regenerated cover and unsigned-provenance diagram describe the candidate,
not authentication or release readiness. `latency.png` uses the distinct
source-bound `data/benchmarks-0.8.0.json` observation with separate units.
`video_stills.png` verifies six decoded PNG hashes against
`data/release-0.8.0.json`; labels are requested seek offsets, not annotated
event onsets. This is a package-only montage, not a paper-demo result.

Newly generated code illustrations retrieve current source with
`inspect.getsource`: the typing filmstrip shows
`democreate.assembly.compositor.Timeline.entry_at_ms`, and the editor frame shows
`democreate.schema.Action.to_dict`. Captions identify those exact symbols.
The filmstrip is a synthetic character-count illustration, not a playback
capture; theme-grid code is explicitly schematic, not a verbatim source claim.
Regenerate from the repository root with
`.venv/bin/python docs/manuscript/figures/make_figures.py`.
