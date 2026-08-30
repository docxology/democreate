# AGENTS.md — workflows/

Only `ci.yml` exists here (verified). Notes for agents:

- The matrix installs **real media binaries** (ffmpeg/ffprobe, poppler-utils)
  rather than mocking — consistent with the repo-wide no-mocks policy in the
  root `AGENTS.md`.
- Kokoro/TTS-heavy tests self-skip when `kokoro-onnx` is absent; do not "fix"
  that by adding the extra to CI silently — it is a deliberate scope choice.
- Any workflow change must keep `concurrency` cancellation and the Python
  matrix consistent with what `README.md` claims about CI.
