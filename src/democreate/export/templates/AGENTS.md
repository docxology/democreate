# AGENTS.md — export/templates/

- `player.html.j2` is loaded by `src/democreate/export/interactive.py`
  (verify the exact loader name before renaming the file).
- Template changes must keep the player self-contained (single HTML file, no
  external fetches) and stay covered by `tests/export/test_interactive.py`.
