# AGENTS — `democreate.export`

Guidance for agents editing this subsystem. Read `../schema.py`, `../media.py`,
`../errors.py`, `../project_paths.py`, `../_logging.py` first; do not modify them.

## Boundaries
- This subsystem **consumes** `Demo` and rendered frames/audio; it never defines
  schema or media value types. Import them from `..schema` / `..media`.
- Only the files under `src/democreate/export/` and the matching
  `tests/export/test_*.py` files belong to this subsystem (modules: `video`,
  `interactive`, `formats`, `chapters`, `metadata`, `overlay`, `poster`, `stego`,
  `verify`). Do not touch other subsystems, `__init__.py` of the package root,
  `pyproject.toml`, or `conftest.py`.

## The deterministic-default rule
- Core deps only: `pyyaml`, `typer`, `rich`, `jinja2` (and `markupsafe`, which
  ships with jinja2), `pillow` (imported as `PIL`).
- Never import a heavy/optional dep at module top level. Detect with
  `importlib.util.find_spec(...)` or `shutil.which(...)`.
- Two paths are genuinely heavy and carry `# pragma: no cover`:
  - `video.export_video` → needs the `ffmpeg` binary
    (`BackendUnavailableError("ffmpeg", extra="video")`).
  - `formats.export_pdf` → needs a Markdown→PDF engine
    (`BackendUnavailableError("pdf", extra="docs")`).
  Their backend-detection helpers (`_has_ffmpeg`, `_has_pdf_engine`) stay pure
  and ARE tested (via `monkeypatch` of the helper).

## Security note (do not regress)
The HTML player embeds JSON inside a `<script>` block. Use `interactive._script_json`
(escapes `<`, `>`, `&`, U+2028, U+2029 to `\uXXXX` and returns `markupsafe.Markup`).
Do **not** swap it for a bare `json.dumps` — Jinja2 autoescaping would turn the
quotes into `&#34;`, which is invalid inside `<script>` and breaks the player.
Body-context values (the title) stay autoescaped — that is correct.

WARNING: U+2028 / U+2029 are line separators to Python's `str.splitlines()`.
Never place literal copies of those characters in source; reference them via
`chr(0x2028)` / `chr(0x2029)` as the existing code does.

## Public API
See `__init__.py` `__all__`: `build_ffmpeg_command`, `frames_to_gif`,
`export_video`, `export_html_player`, `to_markdown`, `to_json`, `to_chapters`,
`export_pdf`.

## Verify
```
cd <repo> && .venv/bin/python -m pytest \
  tests/export/test_video.py tests/export/test_interactive.py \
  tests/export/test_formats.py -p no:cacheprovider -q
```
Lint: `ruff check src/democreate/export/ --line-length 88`.
