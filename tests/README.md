# tests/

The pytest suite (≥90% coverage gate on the pure core, no mock framework).

- **Root-level modules** test the spine and cross-cutting behavior:
  `test_schema.py`, `test_pipeline.py`, `test_cli.py`, `test_cli_commands.py`,
  `test_composition.py`, `test_config.py`, `test_foundation.py`,
  `test_media.py`, `test_portfolio.py`, `test_provenance_v06.py`,
  `test_claim_ledger.py`, `test_manuscript_consistency.py`,
  `test_output_public_allowlist.py`, `test_nocrop_layout.py`,
  `test_motion_and_export.py`, `test_video_assembly.py`,
  `test_visual_upgrades.py`, `test_render_integration.py`,
  `test_scene_context_and_player.py`, `test_redteam_fixes.py`,
  `test_scripts_smoke.py`.
- **Subsystem mirrors:** `animation/`, `assembly/`, `capture/`, `codebase/`,
  `export/`, `narration/`, `paper/`, `translation/` mirror
  `src/democreate/<x>/`.
- `conftest.py` provides shared fixtures.

Run: `.venv/bin/python -m pytest -q` (scoped to `tests/<x>/` for fast
subsystem loops; full `--cov` gate as a final step).
