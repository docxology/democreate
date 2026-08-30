# AGENTS.md — src/democreate/

Authoritative contract: the project-root `AGENTS.md` (non-negotiables, backend
contract, code style). Package-level notes:

- **Spine discipline:** `schema.py`, `media.py`, `errors.py`,
  `project_paths.py`, `_logging.py` are imported by every subsystem; change
  only when the contract must evolve, and bump `SCHEMA_VERSION` when the
  on-disk representation changes. Never copy/redefine spine value types in a
  subsystem — import from `..schema` / `..media`.
- **Thin orchestration:** `cli.py` and `pipeline.py` must stay logic-free. Large
  `cli.py` command groups live in private siblings (`_cli_common.py`,
  `_cli_media.py`); `cli.py` registers them on the shared `app` and re-exports
  the shared helpers so `democreate.cli` remains the only public import path.
  The same facade pattern applies to `portfolio.py` (`_portfolio_facts.py`,
  `_portfolio_render.py`), `narration/tts.py` (`_tts_audio.py`,
  `_tts_kokoro.py`, `_tts_backends.py`), and `capture/screen.py`
  (`_screen_renderer.py`).
- **Subsystem map:** every subdirectory listed in `README.md` here carries its
  own `AGENTS.md` + `README.md`; read the local pair before touching it.
- **Verify:** `.venv/bin/python -m pytest -q` scoped to the subsystem's
  `tests/<x>/`; `ruff check`; `mypy`; `python -c "import democreate"` with core
  deps only.
