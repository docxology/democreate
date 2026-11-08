# Scope and Related Work {#sec:related}

## Documented Construction Models

CodeVideo documents typed actions for narration, editor, file explorer, terminal, mouse, external views and slides [@codevideo2024]. Its virtual-IDE model is a relevant precedent for DemoCreate's action stream. Event sourcing [@fowler2005event] supplies the broader replayable-log pattern; neither citation proves DemoCreate's timing accuracy or implementation correctness.

Capture-first tools such as Screen Studio describe screen recording, automatic zoom and editing [@screenstudio2026]. asciinema records timed terminal events, and termtosvg turns terminal recordings into SVG animations [@asciinema; @termtosvg]. These are different construction choices, not evidence that their output is inherently unreproducible or that they lack every feature not discussed here.

Code Video Generator's documentation describes a Manim-based library for code walkthroughs, diagrams and synchronized sound [@codevideogenerator2023; @manim2024]. Its current repository is `sleuth-io/code-video-generator`; the previously cited `sleepylemur` URL did not resolve during this review. It is therefore incorrect to characterize that library as having no synchronization support solely because its model differs from narration chunks.

The earlier bibliography's VSpeak attribution lacked an authoritative project URL. Searches did not establish its cited project provenance. This manuscript consequently describes chunk/trigger narration as DemoCreate's organizing model without asserting that unverified external attribution; this is not a claim that no such project exists.

## Agentic Educational and Paper Video

Code2Video uses Planner, Coder and Critic agents to construct educational videos through executable Python [@code2video2025]. Paper2Video introduces a paper/presentation benchmark and the PaperTalker generation framework [@paper2video2025]. The latter coordinates slides, speech, subtitles and a presenter. These primary papers establish their own systems and reported results, not a measured comparison against DemoCreate.

| System | Documented organizing artifact | Evidence boundary here |
|---|---|---|
| DemoCreate | Scenes, narration chunks and typed actions | Core implementation and engineering gates; no completed acoustic study. |
| CodeVideo | Typed JSON actions over a virtual IDE | Official action documentation, not a reproduced performance evaluation. |
| asciinema / termtosvg | Timed terminal recordings / SVG animation | Capture and replay model, not an exhaustive capability audit. |
| Code Video Generator | Manim code walkthrough and diagram scenes with synchronized sound | Official documentation, not a narration-accuracy measurement. |
| Code2Video | Agent-generated executable Python | Primary paper; its results are not transferred to DemoCreate. |
| Paper2Video / PaperTalker | Benchmark and generated scientific presentations | Primary paper; no common corpus or controlled comparison was run here. |

: Construction models and provenance, not a superiority or feature-absence matrix. {#tbl:related}

## Positioning and Limits

DemoCreate integrates a Python schema, lightweight synthetic defaults, duration-based narration estimates and optional native media paths. Paper ingestion uses poppler [@poppler2024]. The browser representation is synthetic by default, not proof that a live website executed the described interactions. Manim, Whisper and Chatterbox interfaces remain unwired slots.

No novelty ranking, acoustic advantage, dependency-cost advantage or human-quality advantage is inferred from this architectural comparison. Such claims require version-pinned peer implementations, common inputs and independently assessed outputs. The planned study and current release blockers remain explicit in [@sec:evaluation].
