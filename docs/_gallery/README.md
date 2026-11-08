# Gallery assets: authored synthetic illustrations

Generated gallery images for the docs (`architecture.png`, `themes_strip.png`,
`title_slide.png`, `typing.png`, `paper_figure.png`, `_figure_bg.png), built by
[`make_gallery.py`](make_gallery.py). Regenerate with
`.venv/bin/python docs/_gallery/make_gallery.py` rather than hand-editing the
PNGs.
The paper-theme diagram and caption are **synthetic illustrations**, not PDF
extractions or measured paper results. Source/layout and Pillow/FreeType runtime
must be fixed for byte comparisons; committed PNGs do not prove the latest
generator has been run. Public captions live in [the gallery guide](../gallery.md);
[video evidence](../videos.md) is deliberately separate.
