# DemoCreate — `data/`

This directory holds the reproducibility and benchmarking data contract for
**DemoCreate** (import name `democreate`), the declarative, deterministic
audio-visual demo generator for software (codebase tours, website walkthroughs,
terminal/CLI demos).

It is **inputs + registered claims**, not committed render output. Generated
demos (HTML player, transcript, poster/GIF, optional MP4, captions, and audio)
are written to `output/` and are reproducible from the declarative Demo specs
and available backends — they are not stored here.

## Contents

| File | Purpose |
|------|---------|
| `claim_ledger.yaml` | Every numeric/falsifiable claim (coverage gate, sync-error budget, latency, default wpm, corpus size) with its backing gate or experiment and an honest status. |
| `AGENTS.md` | Operating rules for agents editing or consuming files in this directory. |

## How this directory fits the pipeline

```
schema.py (declarative Demo)  ──┐
                                ├─▶ pipeline.py ──▶ media.py ──▶ output/{mp4,gif,html,...}
backends (capture/narration/    │
  animation/assembly/export) ───┘
                                │
domain_profile.yaml ───────────▶ validation_gates  ◀── referenced by claim_ledger.yaml
experiment_plan.yaml ──────────▶ metrics (sync_error_ms ↓)  ◀── referenced by claim_ledger.yaml
```

The primary metric is **`sync_error_ms`** (minimize): the time gap between an
on-screen action and its anchored spoken trigger word after the TTS→STT
alignment pass. Conditions compared in `experiment_plan.yaml` are `default`
(pure-Python deterministic backends) vs `high_fidelity` (adapter-backed media
paths, only where system binaries or guarded adapters are actually wired).

## Claim discipline

A registered claim is **not** a fact. Each entry in `claim_ledger.yaml` carries
a `status` (`asserted` / `verified` / `estimate`) and a `backed_by` pointer to
the gate or experiment that can confirm it. Do not promote a claim to
`verified` without a passing check, and do not cite a ledger value in the
manuscript without referencing its claim id.

## Consistency

Title, version (`0.7.0`), keywords, author, and license are kept identical
across `CITATION.cff`, `codemeta.json`, and `.zenodo.json` at the project root.
If you bump the version or retitle, update all three plus `claim_ledger.yaml`
and `experiment_plan.yaml` together.
