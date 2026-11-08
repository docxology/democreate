# Troubleshooting: distinguish input, dependency and media failures

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

**Cause.** You asked for a guarded backend (e.g. `--tts kokoro`) but its optional
extra is not installed, or the adapter slot is present but not wired to a concrete
engine yet. The error names the relevant extra when a dependency is missing.

**Fix.** Install the named extra when the dependency is missing, use a wired
system backend, or fall back to the deterministic default:

```bash
democreate backends                  # module presence and native probes, not readiness
uv pip install -e ".[tts]"           # install the named extra
democreate build demo.json --tts silent   # or force the deterministic default
```

`BackendUnavailableError` carries `.backend` and `.extra` (which can be `None`).
Guards run at construction or call time depending on the backend. Installing a
dependency does not repair an unwired adapter: Whisper, Chatterbox, Manim and
the legacy MoviePy compositor still have no concrete implementation. Kokoro is
implemented but its locked ONNX distribution requires a compatible runtime such
as the recorded Python 3.14 voice environment; core Python remains pinned 3.15.

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
- **Manim slot.** Real Manim rendering is unwired even with its dependency
  installed. JSON `build_code_scene_spec` and Pillow pipeline animation remain
  separate core surfaces; installing Cairo does not implement that slot.

## `ffmpeg` not on `PATH`

**Symptom.** MP4 encoding, verification or audio filtering fails because ffmpeg
or ffprobe is missing. Pillow GIF export does not require either binary.

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
`BackendUnavailableError: backend 'poppler' is unavailable`.

**Cause.** The `paper/` subsystem reads PDFs by shelling out to the poppler
utilities `pdfinfo` / `pdftotext` / `pdftoppm`. These are **OS binaries**, not a
pip package — you install poppler through your system package manager.

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

**Fix.** Run `democreate inspect demo.json` and repair the authored artifact.
`--no-strict` only downgrades structural problems at the pipeline boundary; it
cannot make invalid media, unsafe/missing asset paths or unsupported schema
versions usable. Schema 1.0 is intentionally rejected; author schema 1.1.

## Missing images or a resolved bundle fails to rebuild

CLI backgrounds default to the input Demo directory; library Pipeline defaults
to the current directory. Emitted `demos/demo.json` uses workspace-relative
staged references, so rebuild with the original workspace as `--asset-root`.
Do not widen a root to hide missing required images. See
[image authority](cli.md#image-authority-and-resolved-bundles).

## Preview is silent or voiced verification rejects output

HTML is a timed image/caption preview with no synthesized-audio playback.
`auto` TTS deliberately chooses silence, regardless of installed voices.
Use a working implemented voice and render MP4 for speech. A silent MP4 failing
the non-silence check is expected; do not weaken verification. Non-silent audio
and sampled non-black pixels still do not prove intelligibility or onset accuracy.

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
