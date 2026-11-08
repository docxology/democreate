# AGENTS.md — docs/manuscript/figures/

- Figure outputs are **generated artifacts**: rebuild with
  `make_figures.py` / `graphical_abstract.py`; do not retouch PNGs.
- The manuscript references figures by path from chapter markdown
  (`00_abstract.md` opens with the graphical abstract); renaming breaks
  cross-references and the Pandoc build.
- `frame_*` stills are synthetic API illustrations, not decoded-video evidence;
  regenerate them when their source changes or mark them stale. The video
  montage instead uses recorded decoded frames and verifies their hashes;
  preserve the original frames and source record.
- Dimensions, stable source symbols and conceptual-versus-observed evidence
  classes are documented in `README.md` and `../AGENTS.md`; update captions and
  factual orientation when those generator contracts change.
