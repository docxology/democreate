# democreate (package root)

The `democreate` package. Layout:

- **Spine (load-bearing):** `schema.py` (declarative `Demo` value),
  `media.py`, `errors.py`, `project_paths.py`, `_logging.py`, `config.py`.
- **Orchestration (thin):** `cli.py` (command front door), `pipeline.py`
  (stage spine), `portfolio.py` (batch per-project demos).
- **Subsystems (each with its own `AGENTS.md` + `README.md`):**
  `animation/` (diagram, highlights, waveform, zoom, Manim slot, fonts),
  `assembly/` (compositor, animator, audio, captions, effects),
  `capture/` (browser, screen, terminal, replay),
  `codebase/` (walker, ast_viz, dependency),
  `export/` (video, chapters, interactive player, metadata, overlay, poster,
  stego, verify, formats + `templates/player.html.j2`),
  `narration/` (tts, script, sync, llm, project_summary),
  `paper/` (pdf, extract, structure, script),
  `translation/` (translator, localize).

Entry points: `democreate` console script (`cli.py`); see `docs/cli.md` and the
project-root `README.md`.
