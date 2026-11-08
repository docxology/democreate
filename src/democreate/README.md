# Source map: spine, orchestration and eight subsystems

The standalone `democreate` package builds silent synthetic previews on core
Python dependencies; optional voiced video/PDF/capture paths have explicit
prerequisites. Supported floor: Python **3.11.5**, Pillow **13**; core checkout
pin: **3.15**. Kokoro is implemented but needs a compatible voice runtime/models.

## Locate the contract before changing code

| Surface | Source responsibility | Authoritative user contract |
|---|---|---|
| `schema.py`, `media.py` | Demo/Scene/Chunk/Action and exchanged media values | [Schema 1.1](../../docs/schema.md) |
| `errors.py`, `_logging.py`, `project_paths.py` | Typed errors, stage logging, workspace and asset staging | [Architecture](../../docs/architecture.md), [image authority](../../docs/cli.md#image-authority-and-resolved-bundles) |
| `config.py` | Theme/audio/video/metadata data and YAML | [Configuration and precedence](../../docs/config.md) |
| `pipeline.py` | Clone/stage input; TTS → sync → timeline → compose → captions/preview; optional video | [Architecture](../../docs/architecture.md) |
| `cli.py`, `_cli_common.py`, `_cli_media.py` | Native Typer entry point, shared resolution and media commands | [CLI](../../docs/cli.md) |
| `portfolio.py`, `_portfolio_facts.py`, `_portfolio_render.py` | README/Python facts, project summaries and timestamped batch output | [CLI portfolio](../../docs/cli.md#portfolio) |

`Pipeline.run` leaves authored input unchanged; use `PipelineResult.demo` for
resolved timing and staged assets. CLI image roots default to the Demo directory;
library roots default to the current directory. Deterministic core comparisons
require fixed input **and assets/config/runtime**, including Pillow/FreeType.
The HTML is a timed image/caption preview, not synthesized speech playback.

## Open the subsystem guide and local instructions together

| Subsystem | Implementation guide | Editing guidance |
|---|---|---|
| Animation: fonts, highlights, diagrams, waveform, zoom, Manim slot | [README](animation/README.md) | [AGENTS](animation/AGENTS.md) |
| Assembly: scheduled timeline, compositor, animator, WAVs, captions, effects | [README](assembly/README.md) | [AGENTS](assembly/AGENTS.md) |
| Capture: synthetic/live pixels, terminal/browser/input events | [README](capture/README.md) | [AGENTS](capture/AGENTS.md) |
| Codebase: Python AST, import graphs and text/DOT | [README](codebase/README.md) | [AGENTS](codebase/AGENTS.md) |
| Export: HTML, video, metadata, posters and digest associations | [README](export/README.md) | [AGENTS](export/AGENTS.md) |
| Narration: script/facts, TTS, measured clip windows and word estimates | [README](narration/README.md) | [AGENTS](narration/AGENTS.md) |
| Paper: poppler, heuristics and paper Demo construction | [README](paper/README.md) | [AGENTS](paper/AGENTS.md) |
| Translation: no-op/Ollama translators and localization orchestration | [README](translation/README.md) | [AGENTS](translation/AGENTS.md) |

Private implementation siblings support public facades; they are not alternate
user import conventions. Read [package AGENTS](AGENTS.md), [root AGENTS](../../AGENTS.md)
and [testing policy](../../docs/testing_philosophy.md) before changes. The
[generated API](../../docs/api.md) is generated, not hand-edited; a symbol's
signature is not proof that an optional adapter is implemented or ready.
