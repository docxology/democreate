# Offline preview and manuscript reproduction

Use a clean checkout with the locked development dependencies. The package
works with Python 3.11.5 and later. The checkout defaults to Python 3.15, and
the local Template verification uses Python 3.14.

## Build a silent preview

From the project root, use an unused path under `output/`.

```bash
uv sync --locked
mkdir -p output/offline-smoke
uv run --locked democreate init output/offline-smoke/demo.json
uv run --locked democreate inspect output/offline-smoke/demo.json
uv run --locked democreate build output/offline-smoke/demo.json --tts silent -o output/offline-smoke/run-a
uv run --locked democreate build output/offline-smoke/demo.json --tts silent -o output/offline-smoke/run-b
cmp output/offline-smoke/run-a/manifests/render_manifest.json output/offline-smoke/run-b/manifests/render_manifest.json
```

The run writes silent WAVs, synthetic PNGs, captions, and a timed preview at
`web/player.html` within each run. This comparison binds the input, assets,
settings, and runtime used by both runs. See the [quickstart](quickstart.md)
for output navigation and [engineering gates](engineering-gates.yaml) for
receipt requirements. The independent voiced synchronization study remains open.

## Render the canonical manuscript

The authored paper and figures live under [`docs/manuscript/`](manuscript/README.md).
Set up a separate Template checkout using the
[pinned runtime guide](https://github.com/docxology/template/blob/87704feae0a4490ef7dad9c931d268e8c30273c2/docs/RUN_GUIDE.md).
Use matching Pandoc and pandoc-crossref versions. A XeLaTeX-class installation
needs the packages declared in [the preamble](manuscript/preamble.md),
including `siunitx`.

From the DemoCreate root, check citation keys and figure insertion with the
native builder, then stage byte-identical copies of its retained figures and
rebase the render copies under `output/`.

```bash
uv run --locked python scripts/build_manuscript.py --stage-template
```

From the separate Template root:

```bash
git switch --detach 87704feae0a4490ef7dad9c931d268e8c30273c2
mkdir -p projects/working
ln -s /absolute/path/to/democreate projects/working/democreate
uv run --locked python scripts/pipeline/stage_03_render.py --project working/democreate --skip-manuscript-hydration
uv run --locked python scripts/pipeline/stage_04_validate.py --project working/democreate
```

A detached worktree at that slot also works. Inspect
`output/pdf/democreate_combined.pdf`, `output/web/index.html`, the figure
registry and the reports inside the DemoCreate worktree. The native
`scripts/build_manuscript.py` command separately builds
`output/pdf/democreate_manuscript.pdf` from the authored tree.
