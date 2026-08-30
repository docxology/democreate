# AGENTS.md — docs/_videoframes/

- Frames derive from rendered demo videos (`output/video/…`), which are
  gitignored and regeneratable. These PNGs are the doc-facing pinned stills.
- If the declarative demo sources under `examples/` change, these frames can
  go stale — re-extract or flag staleness rather than silently leaving them.
- Referenced by `docs/videos.md` / `docs/gallery.md` (verify exact references
  before moving or renaming anything).
