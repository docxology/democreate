# AGENTS — `data/` (DemoCreate)

Operating rules for any agent (human or AI) creating, editing, or consuming
files in this directory.

## Scope

This directory is the **reproducibility/benchmarking data contract** for
DemoCreate. It registers claims and holds benchmark inputs. It is **not** a
dumping ground for rendered demos — generated videos, previews, players, and
adapter-backed artifacts belong in `output/`.

## Rules

1. **Claims are not facts.** Every numeric or falsifiable statement that appears
   in the manuscript, README, or docs must have a matching entry in
   `claim_ledger.yaml` with a `value`, a `backed_by` pointer, and an honest
   `status` (`asserted` / `verified` / `estimate` / `historical` / `planned`). Never invent a value to fill
   a row.

2. **Status discipline.** Do not set `status: verified` unless the referenced
   gate (`domain_profile.yaml:validation_gates`) or experiment
   (`experiment_plan.yaml`) has actually passed and a specific receipt is recorded.
   Historical reports do not establish current artifact identity; planned studies
   are not measured results.
   When in doubt, use `estimate`.

3. **Keep the metadata trio in sync.** `CITATION.cff`, `codemeta.json`, and
   `.zenodo.json` at the project root must share the same title, version
   (`0.8.0`), keywords, author (Daniel Ari Friedman, ORCID
   0000-0001-6232-9096, Active Inference Institute), and license (MIT). A change
   to one requires changing all three, plus this ledger and the experiment plan
   if a numeric claim or version is affected.

4. **Primary metric is fixed.** The headline benchmark metric is
   `sync_error_ms` (direction: minimize). Do not silently swap or re-scale it;
   add secondary metrics instead and document them in `experiment_plan.yaml`.

5. **Deterministic-default invariant.** Core builds require only the light/default
   dependencies (pyyaml, typer, rich, jinja2, pillow). They emit inspectable
   frames/manifests, silent WAV audio, captions, the resolved Demo, transcript and
   HTML preview. Poster and GIF are separate exports, not automatic build outputs.
   MP4 assembly and verification require the `ffmpeg`/`ffprobe` system binaries;
   voiced synthesis requires a usable voice backend and its own prerequisites.
   Kokoro is implemented; Whisper, Chatterbox and Manim remain unwired slots
   unless their implementation and gates prove otherwise.

6. **No silent failure.** A benchmark or gate that cannot run must be recorded
   as such (skip with reason), never masked. Do not report a passing gate you
   did not execute.

7. **Reproducibility.** Benchmark inputs and Demo specs are committed; outputs
   are regenerated. If a result depends on a random process, pin the seed and
   record it alongside the claim.

## File ownership

| File | Edited by |
|------|-----------|
| `claim_ledger.yaml` | Analysis/manuscript pipeline; reviewed before release. |
| `benchmarks.json` | Preserved historical aggregate; never silently relabel as current. |
| `benchmarks-0.8.0.json` | Source-bound `scripts/benchmark.py` observation, integrated by the release owner. |
| `release-0.8.0.json` | Immutable earlier engineering epoch and then-observed publication blockers. |
| `visual-refresh-2026-11-08.json` | Source-bound visual/API/core/media epochs; preserve earlier observations separately. |
| `deep-audit-2026-11-09.json` | Source-bound native timing/input/export/scoring engineering epoch; not the independent acoustic study. |
| `README.md` | Maintainers documenting the data contract. |
| `AGENTS.md` | Maintainers (this file). |
