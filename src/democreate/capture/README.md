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

### `browser.py` — website driving
- `BrowserDriver` — abstract: `navigate`, `click`, `fill`, `screenshot`, `close`.
- `NullBrowserDriver` — **default**. Records every call into `.manifest`;
  `screenshot()` renders a synthetic browser frame via `SyntheticRenderer`.
- `PlaywrightBrowserDriver` — real automation (extra `browser`).
- `drive_website_scene(scene, driver=None)` — maps a scene's
  NAVIGATE/CLICK/SCROLL/FILL actions to driver calls; returns the manifest.

### `replay.py` — input record/replay (pure event model)
- `InputEvent(t_ms, kind, payload)` and `EventLog(events)` with `to_json` /
  `from_json` and `to_actions()` (move→MOVE_MOUSE, click→CLICK, key→TYPE_CODE).
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
`tests/test_capture_screen.py`, `tests/test_capture_terminal.py`,
`tests/test_capture_browser.py`, `tests/test_capture_replay.py` — 50 tests, no
mocks, real temp files. Run:

```
.venv/bin/python -m pytest tests/test_capture_*.py -q
```
