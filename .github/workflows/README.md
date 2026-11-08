# CI: core compatibility, installed-package smoke, and inspectable visual evidence

`ci.yml` runs on branch pushes and main pull requests. Each job has a bounded
timeout; no task-specific branch pattern is required to obtain pre-main proof.

| Job | Contract |
|---|---|
| Python 3.11–3.15 matrix | Core import preflight, built-wheel installation/build smoke, Ruff, mypy and the ≥90% core coverage gate. Real ffmpeg/poppler and a SHA-256-checked matched Pandoc/crossref pair are installed. |
| Docs / figures / manuscript | Regenerate source-owned PNGs and API reference, exercise the localization media API with an explicitly silent control, build the complete PDF, and rasterize every page for inspection. |

Regenerated API/figure files, the showcase Demo and its three staged figure
assets must match their committed versions; drift fails the job. Inspect the
retained artifact before refreshing those files, not the gate.

The `visual-proof-<commit>` artifact retains PNGs, the generated API reference,
PDF/pages and the control's media/captions for 14 days. Its manifest records the
source SHA, Python/Pillow/FreeType versions, per-stage outcomes and retained file
hashes. **Inspect stage outcomes:** a failed run can retain old committed inputs;
an inventory hash alone is not evidence that every file was regenerated.

Optional model/browser and external-paper fixtures may skip. Silent-control
rendering is not the canonical Kokoro showcase, speech-quality validation or
acoustic-corpus evidence. Passing CI does not waive the
[blocking publication criterion](../../docs/manuscript/07_evaluation.md).
