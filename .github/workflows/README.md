# workflows/

| File | Purpose |
|------|---------|
| `ci.yml` | CI on push/PR to `main`: pytest matrix over Python 3.10–3.13 (fail-fast off), with ffmpeg/poppler system binaries installed so render/paper backend tests run for real; Kokoro tests skip because the `tts` extra is not installed in CI. |
