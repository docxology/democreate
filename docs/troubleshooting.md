# Troubleshooting

Most issues come from one of a few sources: a real backend invoked without its
extra, headless/display problems, or a system binary (`ffmpeg`, poppler) not
being on `PATH`. The deterministic default `build` path needs none of the heavy
dependencies, so when in doubt, fall back to it and confirm the demo builds
before debugging an extra. (`render`, `verify`, and `paper` do need their system
binaries — see the relevant sections below.)

## `BackendUnavailableError`

**Symptom.** A build or command raises
`BackendUnavailableError: backend 'kokoro' is unavailable — install it with
\`uv sync --extra tts\`` (or similar for `whisper`, `mss`, `playwright`, `manim`,
`moviepy`, …).

**Cause.** You asked for a real backend (e.g. `--tts kokoro`) but its optional
extra is not installed. The error always names the exact extra to install.

**Fix.** Install the named extra, or fall back to the default:

```bash
democreate backends                  # see which extras are installed vs default
uv pip install -e ".[tts]"           # install the named extra
democreate build demo.json --tts silent   # or force the deterministic default
```

The error is raised early (in the backend constructor) and carries `.backend` and
`.extra` attributes if you are catching it programmatically.

## Headless rendering / no display

**Symptom.** Frame rendering, browser, or animation steps fail referencing an X
display, a window server, or a missing browser.

**Cause and fix by subsystem:**

- **Default frames (`SyntheticRenderer`, Pillow).** These never need a display —
  they draw straight to an image with `ImageFont.load_default()`. If a *frame*
  render fails headlessly, it is not the default path; check you are not forcing a
  real capture backend.
- **`browser` extra (Playwright).** After `uv pip install -e ".[browser]"` you
  must also fetch the browser binaries: `playwright install`. On headless Linux,
  run under `xvfb-run` or use Playwright's headless mode. The `NullBrowserDriver`
  default needs no browser at all.
- **`capture` extra (mss).** Real screen capture needs an actual display/session;
  it will not work in a headless CI runner. Use the `SyntheticRenderer` default
  there.
- **`animation` extra (Manim).** Manim renders need a working Cairo/ffmpeg stack;
  on headless machines prefer the JSON scene-spec default
  (`build_code_scene_spec`) and render elsewhere.

## `ffmpeg` not on `PATH`

**Symptom.** Video/GIF export fails with a "ffmpeg not found" style error even
though the `video` extra is installed.

**Cause.** The `video` extra installs the Python wrappers (`moviepy`,
`ffmpeg-python`) but **not** the `ffmpeg` binary. DemoCreate builds the ffmpeg
argv purely; actually encoding shells out to `ffmpeg`, which must be on `PATH`.

**Fix.** Install ffmpeg with your OS package manager and verify:

```bash
# macOS:        brew install ffmpeg
# Debian/Ubuntu: sudo apt-get install ffmpeg
ffmpeg -version
```

The default export path (`ManifestCompositor` manifest + HTML player) does not
require `ffmpeg`, so a `build` (as opposed to `render`) without it still yields
an inspectable result.

## `paper` fails: poppler not on `PATH`

**Symptom.** `democreate paper paper.pdf` raises
`BackendUnavailableError: backend 'poppler' is unavailable — install it with
\`uv sync --extra pdf\``.

**Cause.** The `paper/` subsystem reads PDFs by shelling out to the poppler
utilities `pdfinfo` / `pdftotext` / `pdftoppm`. These are **OS binaries**, not a
pip package — the `pdf` extra carries no Python dependency; you install poppler
through your system package manager.

**Fix.**

```bash
# macOS:         brew install poppler
# Debian/Ubuntu: sudo apt-get install poppler-utils
pdfinfo -v && pdftoppm -v
```

All three of `pdfinfo`, `pdftotext`, `pdftoppm` must be present
(`poppler_available()` checks all three). See [paper.md](paper.md).

## A demo fails to build with validation errors

**Symptom.** `build --strict` raises `SchemaValidationError`, or `inspect` reports
problems and exits non-zero.

**Cause.** The demo failed structural validation: empty title, non-positive
geometry/fps, duplicate scene or chunk ids, or an invalid action type.

**Fix.** Run `democreate inspect demo.json` to see the exact problem list. Fix the
artifact, or build with `--no-strict` to downgrade problems to warnings and still
produce output.

## Tests pass locally but the gate fails

- Use `.venv/bin/python -m pytest` — a bare `python` may be a different
  interpreter (e.g. a pyenv shim) and silently run a stale or empty suite.
- Run subsystem-scoped tests *without* `--cov` when working in parallel; multiple
  `--cov` runs race on the shared `.coverage` file.
- The coverage gate is `fail_under = 90` on the pure core. If it dips, you likely
  added pure logic without a test or removed a `# pragma: no cover` from a heavy
  adapter. See [testing_philosophy.md](testing_philosophy.md).

## Import errors on a clean install

**Symptom.** `import democreate` fails referencing `numpy`, `torch`, `mss`, or
another heavy package.

**Cause.** A heavy dependency leaked into a module top-level import — a violation
of the deterministic-default rule. The package must import cleanly on core deps
alone.

**Fix.** The import should be lazy (inside the function that needs it), gated by
`importlib.util.find_spec`. See [AGENTS.md](AGENTS.md) rule 5. Confirm a clean
core install with `python -c "import democreate"`.
