# `democreate.capture`

The visual-capture subsystem. It turns the declarative demo schema into
rendered frames and records terminal / browser / input sessions. Every heavy
capability has a **pure-Python deterministic default** that runs with only the
core dependencies (Pillow + stdlib); real backends sit behind optional extras
and raise `BackendUnavailableError` when their dependency is missing.

## Modules

### `screen.py` — frame rendering (the heart)
- `FrameSource` — abstract base: `render(state, size) -> PIL.Image.Image`.
- `SyntheticRenderer` — **default**. Pure Pillow. Draws a clean, deterministic
  frame per `FrameState.scene_kind`:
  - editor: title bar with `file_path`, line-numbered `code_lines`, emphasized
    `highlight_lines`, and a typing cursor honoring `cursor_typed`;
  - terminal: dark background, `terminal_lines`, trailing prompt;
  - browser: address bar with `url` + placeholder body;
  - slide: centered `title`.
  Any non-empty `caption` is overlaid as a lower-third subtitle. Uses
  `ImageFont.load_default()` (no external fonts). Byte-for-byte deterministic.
  Camera scales greater than one apply a centered content crop/resize before
  drawing the fixed waveform band, section and caption overlays.
- `MssScreenCapture` — real pixel capture (extra `capture`, via `mss`).
- `render_frame(state, size=(1920,1080))` — convenience wrapper for the default.
- `render_demo_thumbnail(demo, size=(1280,720))` — renders the first scene's
  opening frame (blank titled slide for an empty demo).

### `terminal.py` — asciinema asciicast v2 (pure)
- `AsciicastEvent(time, kind, data)` and `AsciicastRecording(version, width,
  height, events)` with `to_json` / `from_json` (header line + one `[time, kind,
  data]` array per line) and `duration()`.
- `record_commands(commands, *, prompt="$ ")` — deterministic input+output
  events at increasing timestamps.
- `recording_to_frame_states(rec)` — terminal `FrameState`s for the renderer.
- Headers require version 2 plus positive integer `width` and `height`. Parsing
  rejects missing/nonobject headers, invalid geometry/versions, malformed event
  triples, nonnumeric/nonfinite/negative times, and nonstring event channels/data
  with `CaptureError` (including semantic errors).

### `browser.py` — website driving
- `BrowserDriver` — abstract: `navigate`, `click(selector)`,
  `click_xy(x, y, *, button="left")`, `fill(selector, value)`,
  `scroll(direction, amount)`, `screenshot`, `close`.
- `NullBrowserDriver` — **default**. Records every call into `.manifest`;
  `screenshot()` renders a synthetic browser frame via `SyntheticRenderer`.
- `PlaywrightBrowserDriver` — real automation (extra `browser`). Missing browser
  executables raise `BackendUnavailableError` with `playwright install chromium`
  guidance; failed launches release their started Playwright context.
- `drive_website_scene(scene, driver=None)` consumes canonical action params:
  NAVIGATE `url`; CLICK either `selector` or `xy` with optional `button`; FILL
  `selector` and `value` (not `text`); SCROLL `direction` and optional `amount`
  (default 100 pixels, not the removed `by` alias). All drivers receive scrolls;
  up/down/left/right produce signed vertical/horizontal wheel movement. Invalid
  directions or negative amounts fail explicitly. Null manifests retain canonical
  `value`, `xy`/`button`, and `direction`/`amount` fields.

### `replay.py` — input record/replay (pure event model)
- `InputEvent(t_ms, kind, payload)` and `EventLog(events)` with `to_json` /
  `from_json` and `to_actions()`. Event timestamps are preserved and discrete
  recorded inputs have zero duration, so a key is visible at its recorded instant.
  Moves become
  MOVE_MOUSE `{"xy": (x, y)}`; clicks become CLICK `{"xy": (x, y), "button": ...}`
  with pynput's `Button.` prefix removed, never a fabricated selector. Printable
  keys become TYPE_CODE `{"code": ...}` after unwrapping pynput's quoted
  characters. `Key.space`, `Key.enter`, and `Key.tab` map to actual whitespace;
  unsupported controls (including shift/backspace) are explicitly skipped, not
  inserted as literal `Key.*` text. Live replay uses the same supported key mapping
  and honors the recorded mouse button.
- `record_session(...)` / `replay_session(...)` — real OS hooks (extra
  `replay`, via `pynput` / `pyautogui`).

## Optional extras

| Backend | Class / function | Extra | Dependency |
|---------|------------------|-------|------------|
| Real screen pixels | `MssScreenCapture` | `capture` | `mss` |
| Real browser | `PlaywrightBrowserDriver` | `browser` | `playwright` |
| Record input | `record_session` | `replay` | `pynput` |
| Replay input | `replay_session` | `replay` | `pyautogui` |

Install with e.g. `uv sync --extra capture`. The default backends need none of
these and produce identical output on every machine.

## Tests
`tests/capture/test_screen.py`, `tests/capture/test_terminal.py`,
`tests/capture/test_browser.py`, `tests/capture/test_replay.py` use real temp files,
schema validation, visible-state/render consumers, and deterministic backends,
without mocked computation. Real-browser tests use a local HTML file when the
optional package/binary is available; absence is skipped. Run:

```
.venv/bin/python -m pytest tests/capture/test_*.py -q
```
