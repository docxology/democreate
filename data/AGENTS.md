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
   `status` (`asserted` / `verified` / `estimate`). Never invent a value to fill
   a row.

2. **Status discipline.** Do not set `status: verified` unless the referenced
   gate (`domain_profile.yaml:validation_gates`) or experiment
   (`experiment_plan.yaml`) has actually passed and you can point to the run.
   When in doubt, use `estimate`.

3. **Keep the metadata trio in sync.** `CITATION.cff`, `codemeta.json`, and
   `.zenodo.json` at the project root must share the same title, version
   (`0.7.0`), keywords, author (Daniel Ari Friedman, ORCID
   0000-0001-6232-9096, Active Inference Institute), and license (MIT). A change
   to one requires changing all three, plus this ledger and the experiment plan
   if a numeric claim or version is affected.

4. **Primary metric is fixed.** The headline benchmark metric is
   `sync_error_ms` (direction: minimize). Do not silently swap or re-scale it;
   add secondary metrics instead and document them in `experiment_plan.yaml`.

5. **Deterministic-default invariant.** Any claim about producing "a real demo"
   must hold with **only the light/default dependencies** installed
   (pyyaml, typer, rich, jinja2, pillow). The required core outputs are
   inspectable frames/manifests plus web, transcript, poster, and GIF artifacts;
   MP4 assembly and verification require the `ffmpeg`/`ffprobe` system binaries.
   Neural TTS, Whisper, Manim, and MoviePy surfaces are guarded adapter slots
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
| `README.md` | Maintainers documenting the data contract. |
| `AGENTS.md` | Maintainers (this file). |
