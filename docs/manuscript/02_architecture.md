# Demo Values, Backend Boundaries, and Workspace Custody {#sec:architecture}

The architecture separates plain values, backend adapters and filesystem outputs. A `Demo` describes content; `RenderConfig` controls its presentation; a `Workspace` contains generated files. Reproducibility requires all three inputs plus a fixed toolchain and backend, not just the Demo JSON.

![Construction boundaries: authored Demo values feed narration and duration-based timing, then scheduled synthetic state and exports. Measured clip windows are distinct from estimated words. Core PNG/caption/HTML-preview output needs no model or media executable; voiced MP4 and PDF ingestion require additional tools and inputs.](figures/architecture.png){#fig:architecture}

## Schema 1.1: Content Values and Timing Provenance

`Demo` contains ordered `Scene` objects; a scene contains narration `Chunk`s and each chunk contains typed `Action`s. Scene kinds select editor, terminal, browser or slide representations. The action-stream model is related to event sourcing [@fowler2005event] and CodeVideo [@codevideo2024]. Narration text and optional word triggers organize timing without requiring a live IDE.

Schema 1.1 stores measured `Chunk.duration_ms` separately from word-count estimates. `Action.timestamp_source` distinguishes explicit authored absolute times from sync-derived times: the former survive re-synthesis, while the latter refresh after narration edits. Triggered actions are re-anchored. WAIT advances the untriggered fallback cursor; recorded discrete input events have zero duration and retain their absolute event times.

Valid values round-trip through dict, JSON and YAML. `Demo.validate()` reports structural problems such as duplicate identifiers or nonpositive geometry; it is not a general resource limiter or a sandbox. Schema 1.0 is intentionally rejected. Action parameters describe virtual state: terminal command/output payloads are not permission to execute those commands.

## Core Defaults, Implemented Adapters, and Unwired Slots

| Surface | Core path | Additional prerequisites or limitations |
|---|---|---|
| Narration | `SilentTTSBackend` writes PCM WAV | Native speech needs an available OS engine and conversion tools; Kokoro needs its extra and model files. |
| Word timing | `HeuristicTranscriber` interpolates supplied text over measured duration | No acoustic onset measurement; Whisper is an unimplemented slot. |
| Visual state | `SyntheticRenderer`, scheduled replay and Pillow animation | Browser frames are synthetic unless real captured pixels are supplied; optional screen/browser drivers have their own prerequisites. |
| Core exports | PNGs, manifest, captions, transcript, timed HTML image preview | No narration playback; sibling frame assets must accompany the HTML. |
| MP4 | Animated or static assembly | ffmpeg; content verification also uses ffprobe and ffmpeg. |
| Paper ingestion | poppler wrappers | `pdfinfo`, `pdftotext`, `pdftoppm`; no pure-Python PDF fallback or `pdf` extra. |

Optional dependencies are imported lazily. Missing packages raise `BackendUnavailableError` with the applicable extra; missing native tools identify the tool rather than inventing an install extra. Dependency discovery does not turn an unwired slot into an implementation. Native speech availability is probed, not inferred solely from a binary name.

## Scheduled State Replay and Asset-Root Custody

Timeline entries retain scene-level state across chunk boundaries and resolve partial typing, file restoration and terminal completion at an absolute time. Animated output consumes that scheduled state. Final representative stills are a separate inspection surface. Lead, gap and trail intervals are explicit; caption windows cover narration rather than silence.

Chunk identifiers are opaque, not filenames. Narration uses numbered audio paths, and current frame paths come from the current timeline rather than a directory glob. Workspace-generated namespaces reject symlinks. Background images must exist beneath an explicit asset root or the workspace; they are copied into portable, content-named assets before synthesis. These checks do not protect against a concurrent hostile same-UID filesystem replacement or sandbox direct low-level capture APIs.

## Pipeline Stages and Resolved-Artifact Ownership

The orchestrator validates, stages assets, synthesizes narration, synchronizes durations/events, builds the timeline and writes frames, captions, player, transcript and resolved Demo. MP4 rendering then builds the voiceover, samples animation, encodes and optionally verifies content presence. An HTML build does not prove video encoding or voiced output.

Pipeline execution clones the authored input and changes only the resolved timing and asset references in `PipelineResult.demo`; the original remains reusable in another workspace. The resolved JSON uses workspace-relative paths; replaying it through the CLI requires that workspace as the explicit `--asset-root`. Content digests associate stable selected content with a record; they are not signatures or complete render identities ([@sec:provenance]).
