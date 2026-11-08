# Introduction {#sec:introduction}

## From Recordings to Editable Descriptions

Screen recordings preserve the appearance of an interaction, but revising the underlying software can require editing or replacing its footage. A declarative description offers a different tradeoff: retain the intended narration and visual events as data, then render them again. It does not recover undocumented interactions or guarantee that a synthetic interface accurately depicts a live application.

Reproducibility studies such as Pimentel et al.'s examination of Jupyter notebooks [@pimentel2019jupyter] motivate retaining execution inputs and environments. They are not evidence that DemoCreate is reproducible. That property requires controlled builds of this package with the same source, assets, configuration and runtime.

## Four Responsibilities

DemoCreate separates **visual state**, **narration**, **timing** and **export**. Its action stream is related to CodeVideo's virtual IDE [@codevideo2024] and event sourcing [@fowler2005event]. asciinema and termtosvg [@asciinema; @termtosvg] provide related examples of replayable terminal descriptions. Here, scenes group narration chunks and typed editor, terminal, browser or slide events.

The default narration backend writes real, measured silent WAVs. Optional native speech and the implemented Kokoro adapter [@kokoro2025] can supply voiced audio when their prerequisites are available. Silence is useful for engineering checks; it is not speech or evidence of spoken-word alignment. Chatterbox [@chatterbox2025] remains an unimplemented adapter slot.

Timing uses generated clip durations and character-weighted interpolation of the supplied narration text. Word triggers therefore receive estimates, not recognized acoustic onsets. Animated replay resolves visible state at the selected time; static representative frames cannot demonstrate within-chunk event timing. ffmpeg [@ffmpeg2024] is required for MP4 encoding, not for core PNG, caption or HTML output.

## Contribution and Evidence Boundary

The contribution is an inspectable Python artifact and an integrated path from that artifact to frames, captions, transcripts and a local HTML player, with optional MP4 output. Render configuration controls composition and pacing. PDF ingestion uses poppler [@poppler2024], and repository inspection reads source rather than executing it. Neither extraction path guarantees that its generated overview captures every scientifically important detail.

The architecture ([@sec:architecture]) distinguishes core defaults from implemented optional adapters and unwired slots. Synchronization ([@sec:synchronization]) distinguishes measured duration from estimated word timing. Composition and paper ingestion are described in [@sec:composition] and [@sec:paper]. Evaluation and reproducibility ([@sec:evaluation; @sec:reproducibility]) separate engineering receipts, historical artifacts and the still-unmet empirical study. Related work ([@sec:related]) compares documented construction models, not unmeasured superiority.
