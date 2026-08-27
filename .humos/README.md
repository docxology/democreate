# .humos/ — HumOS sidecar contract for DemoCreate

This directory declares DemoCreate's relationship to the HumOS ecosystem
without introducing any `humos.*` import dependency (standalone coupling).

## Files

| File | Purpose |
|------|---------|
| `sidecar.toml` | Project identity, archetype, coupling posture, tags |
| `bridges.toml` | Cross-project edges (`feeds` → hum-dashboard, `informs` ← hum-docxology) |
| `conformance.toml` | Coverage floor, gate command, required surfaces, runtime |

## Bridge to hum-dashboard

The `feeds` edge to `hum-dashboard` declares that DemoCreate produces versioned
demo artifacts (MP4 videos, HTML players, transcripts, provenance posters) that
the dashboard can surface on per-repo detail pages. The dashboard discovers
rendered demos by scanning a shared output directory structure.

## Bridge to hum-docxology

The `informs` edge from `hum-docxology` records that DemoCreate is managed and
cloned via the hum-docxology repo manager under `repos/public/DemoCreate/`.
