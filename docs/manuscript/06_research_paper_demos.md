# From PDF Text and Supplied Figures to Demo Scenes {#sec:paper}

The `paper/` subsystem assembles research-paper overviews from a PDF, supplied figure images and optional Python source summaries. `build_paper_demo` composes those inputs into an ordinary `Demo` value; the narration, synchronization, animation and export pipeline then follows the same contracts as a software tour ([@sec:architecture]). The extraction path supplies content, not a separate scientific-validation stage. [@fig:paper_flow] distinguishes extracted inputs, authored scenes and downstream outputs.

![Paper-input construction path: poppler supplies metadata, text and page rasters; heuristic extraction, supplied figures and optional Python source summaries feed an authored Demo, then core exports or optional voiced MP4. This conceptual diagram is not an observed extraction result, scientific-fidelity check or acoustic-alignment evaluation.](figures/paper_flow.png){#fig:paper_flow}

## Poppler Metadata, Text, and Page Rasters; Supplied Figure Files

The PDF path wraps poppler command-line utilities [@poppler2024], not a Python PDF library, so it adds no PDF-specific pip dependency to an otherwise installed DemoCreate environment. `paper/pdf.py` uses `pdfinfo` for metadata, `pdftotext` for text and `pdftoppm` for page PNGs. These real binaries must be usable on `PATH`; a pip extra does not supply them. Missing tools raise `BackendUnavailableError`. The source PDF is read rather than edited, while page rendering writes output images. Extracted text and rasterization depend on the input PDF and poppler build, so this is not a cross-machine byte-identity guarantee or an OCR guarantee for scanned pages.

`paper/extract.py` turns those calls into a render-ready `PaperSummary`: title and authors from `pdfinfo` metadata, the page count, and a sorted list of figure images collected from a sibling directory. Figures are *collected*, not extracted from the PDF: the subsystem takes a directory of already-exported figure PNGs (the reproducible analysis outputs the project already has), which keeps figure quality high and the implementation simple.

## Heuristic Abstract, Caption, and Heading Extraction

The depth of a paper demo comes from `paper/structure.py`, whose three pure extractors read the paper's *real* prose rather than generic boilerplate, and whose recurring adversary is the table of contents (TOC) that long manuscripts front-load. The extractors operate on already-extracted text, so they are fully testable without poppler; only `summarize_structure` touches the guarded poppler path.

`extract_abstract` searches standalone `Abstract` markers, rejects TOC-like candidates using dotted leaders and trailing page numbers, and prefers substantial prose (at least 200 characters). If that fails it searches for a substantial paragraph after the first third of the extracted text, with a bounded last-resort candidate. Such fallback prose need not be the true abstract. `extract_figure_captions` recognizes figure markers, gathers multiline bodies, bounds captions to a sentence/character budget and deduplicates figure numbers, while rejecting some TOC/cross-reference fragments. `extract_sections` recognizes numbered, `Part N` and fixed named headings and rejects TOC-like lines. Caption cleaning includes NFKC glyph folding; this is text normalization, not semantic or mathematical verification. `summarize_structure` normally scans the first 14 pages for abstract/sections (with a whole-text abstract fallback) and the whole document for captions. These are heuristics, not a guarantee of correct structure on every PDF. Earlier reports of a roughly 1200-character abstract and six sections from *Policy Entanglement in Active Inference* are historical observations, not a fresh extraction or corpus-wide accuracy result.

## Composing Reviewed Inputs into Ordinary Demo Scenes

`paper/script.py`'s `build_paper_demo` assembles a title card, optional rendered title page, sentence-chunked abstract, optional structure scene, selected figures with matched captions or generic fallback narration, supplied PDF-page images, optional codebase architecture and an outro. It produces ordinary scene/chunk/action data; title/author metadata, section detection and figure-caption matching still require review against the source paper. Figure images use contain fitting before any explicit zoom, with the section and narration caption in separate bands ([@sec:composition]). [@fig:frame_paper] illustrates that initial composition using the committed background input, not a current paper-video receipt.

![Generated paper-theme slide using the committed `figures/paper_fig.png` background, historically labeled as a coupling-potential graph from *Policy Entanglement*. Initial contain fitting places the image inside the content area with separate section/caption bands; later camera or Ken Burns zoom can crop it. The background's extraction date and publication status are not established by this illustration.](figures/frame_paper.png){#fig:frame_paper}

Narration templates require no LLM; fixed extracted inputs and overrides determine the authored Demo. Different extraction, synthesis or encoder environments need not yield identical voiced media. The ordinary pipeline supplies themes, scheduled actions, waveform and transitions; its verifier does not assess scientific correctness ([@sec:evaluation]).

The authoritative two-step CLI recipe is in [@sec:reproducibility]: generate and review `paper.json`, then render with an explicit image allow-root. The `paper` command's direct-render path instead derives that root from `--figures` or the PDF directory and has no separate `--asset-root` option. Accepted images are staged into the workspace, and the resolved artifact uses workspace-relative paths; it is distinct from the pre-render authored Demo.

## Historical Template Run Versus Curated External-Input Showcase

Historical documentation reported a template paper run from a 170-page *Policy Entanglement* PDF and associated codebase, producing 12 scenes and a 188.0-second video. This is not a current 0.8.0 receipt. The curated showcase is a distinct hand-authored artifact, with separately supplied external paper inputs; neither workflow substitutes an unrelated paper when inputs are absent.

The historical report describes 1920×1080 H.264 output and −15.5 dB mean volume. Mean dB is not integrated LUFS, not proof of the configured −16 LUFS target, and not proof of intelligible speech. A fresh output needs its own stream, energy, picture and identity evidence.
