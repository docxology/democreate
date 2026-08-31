# AGENTS.md — docs/manuscript/figures/

- All figures are **registry-backed generated artifacts**: rebuild with
  `make_figures.py` / `graphical_abstract.py`; do not retouch PNGs.
- The manuscript references figures by path from chapter markdown
  (`00_abstract.md` opens with the graphical abstract); renaming breaks
  cross-references and the Pandoc build.
- `frame_*` stills depend on rendered demo output — re-extract when the demo
  changes or mark them stale.
