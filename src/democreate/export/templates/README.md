# HTML template: timed frame and caption preview

`player.html.j2` is loaded by `export.interactive` to generate
`output/web/player.html`. It embeds chapter/cue data and controls; frame PNGs
remain sibling files and synthesized narration is **not played**. Preserve the
script-safe JSON encoder and body autoescaping. See
[export source guide](../README.md), [architecture](../../../../docs/architecture.md)
and [CLI bundle instructions](../../../../docs/cli.md#image-authority-and-resolved-bundles).
