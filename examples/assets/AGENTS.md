# AGENTS.md — examples/assets/

- `make_assets.py` owns the architecture diagram and optional browser capture of
  the dashboard. Do not replace a retained dashboard when no browser is available.
- `make_showcase.py` copies graphical abstract, theme and paper-figure inputs from
  `docs/manuscript/figures/`. Regenerate those sources before staging their copies.
- Preserve the curated `paper/` subtree and original input identities; filenames
  are Demo-relative references, so renames require migrating every artifact.
