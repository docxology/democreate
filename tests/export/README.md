# tests/export/

Tests for the export subsystem: video assembly, chapters, interactive player, metadata, overlay, provenance poster, steganography, content verification, and output formats.

Mirrors `src/democreate/export/` — run scoped:
`.venv/bin/python -m pytest -q tests/export/`.

## Native FFmpeg regression recipes

The integration owner runs these after all source writers finish; they are not
mocked encodes. Native tests skip when the required binary/filter is absent.

- `.venv/bin/python -m pytest -q tests/export/test_video.py -k native_numbered`
  creates red `frame_0005`, green `frame_0006`, and stale neighbors on both
  sides; each exporter receives one or two frames without audio. A real FFmpeg
  RGB decode must contain exactly the supplied count and colors in order.
- `.venv/bin/python -m pytest -q tests/export/test_video.py -k caption`
  burns a real SRT onto a black frame and checks decoded pixels; the unavailable
  subtitles-filter fixture must raise `RenderError`. Requires libass and a
  usable native font for the positive burn.
- `.venv/bin/python -m pytest -q tests/export/`
  additionally exercises rejected sparse/reordered/mixed inputs, authored digest
  coverage, unsigned carrier/author boundaries, measured player/chapter timing,
  and missing native-binary errors without misleading Python-extra remedies.
- `.venv/bin/python -m pytest -q tests/export/test_interactive.py -k native_browser`
  uses a real Playwright Chromium page (skips if unavailable), seeking across
  measured cue starts/ends, lead/gaps/trail, and script-like narration. It checks
  visible caption text and that narration never executes as script.
