# Implementation {#sec:implementation}

DemoCreate is organized as a single `democreate` package under `src/`: 51 source modules in total, a small set of shared top-level modules plus seven subsystem packages (`capture/`, `narration/`, `animation/`, `codebase/`, `assembly/`, `export/`, `paper/`). This section maps the module structure and describes each subsystem, emphasizing the deterministic default in each case. Two figures in this section show the rendering primitives directly: [@fig:frame_code] is a real synthetic editor frame, and [@fig:waveform] is a real speech-waveform scrubber — both produced by calling the package's own public APIs.

## Module Map

The top-level modules hold the shared, dependency-light primitives that the subsystems exchange:

| Module | Responsibility |
|--------|----------------|
| `schema.py` | The declarative spine: `Demo`, `Scene`, `Chunk`, `Action`, `ActionType`, `SceneKind`, `WordTimestamp` ([@sec:architecture]) |
| `config.py` | `Theme`, `AudioConfig`, `VideoConfig`, `RenderConfig`, and the `THEMES` presets ([@sec:composition]) |
| `media.py` | Shared value types: `AudioClip` (a rendered narration file and its measured properties) and `FrameState` (a renderable snapshot of the virtual environment) |
| `pipeline.py` | The `Pipeline` orchestrator, `PipelineResult`, `build_demo`, and `render_video` |
| `cli.py` | The `democreate` command-line interface (Typer [@typer2024] + Rich [@rich2024]) |
| `project_paths.py` | The `Workspace` path resolver that creates and exposes all output sub-directories |
| `errors.py` | The exception hierarchy rooted at `DemoCreateError` (`SchemaValidationError`, `BackendUnavailableError`, `SyncError`, `RenderError`, …) |
| `_logging.py` | Self-contained structured logging and the `log_stage` context manager |

## `capture/` — The Visual Track

The capture subsystem produces the visual surface of each scene. Its centerpiece is the **synthetic renderer** in `capture/screen.py`: a `FrameSource` whose default `SyntheticRenderer` turns a `FrameState` into a Pillow image by *drawing* a clean, deterministic depiction of the editor, terminal, browser, or slide implied by that state — a virtual desktop in the CodeVideo lineage [@codevideo2024], reproducible across machines and requiring only the core `pillow` dependency [@pillow2024]. Every metric is proportional to the frame height and all text uses real, scalable TrueType fonts resolved by `animation/fonts.py`, so titles and captions stay legible at HD. Code is colored with **pygments** [@pygments2024] when available — its lexer tokens mapped onto the active theme's syntax palette — falling back to a small keyword set otherwise. A frame may instead carry a `background_image` (a real browser screenshot, a generated diagram, or a paper figure), which the renderer fits *whole* into the content area — contain, never cropped ([@sec:composition]) — placing the section pill in the chrome and the word-wrapped caption in its own band below the image, and reserving a bottom band for the animated waveform. [@fig:frame_code] is exactly such a frame: a line-numbered, pygments-highlighted editor showing real `schema.py` source with one highlighted line, a section pill, and a caption.

![A synthetic `CODEBASE` editor frame rendered by `SyntheticRenderer`: scaled TrueType fonts, a line-number gutter, pygments syntax highlighting, an emphasized line, a section label pill, and a word-wrapped caption band — all drawn in pure Pillow with no real-pixel capture.](figures/frame_code.png){#fig:frame_code}

The real-pixel `MssScreenCapture` backend sits behind the `capture` extra [@mss2024] for grabbing genuine screen content, but is never required. `capture/terminal.py` models a terminal session as a stream of timed events serialized to the asciinema asciicast v2 format [@asciinema] — a header object followed by one `[time, kind, data]` array per line — so a list of `(command, output)` pairs becomes a deterministic recording and a sequence of renderable terminal frame states without launching a shell, echoing the durable-capture philosophy of asciinema and termtosvg [@termtosvg]. `capture/browser.py` drives `website` scenes, deterministically by default and via Playwright [@playwright2024] when the `browser` extra is present. `capture/replay.py` provides a pure event model for input record/replay, with guarded real backends over `pynput` [@pynput2024] and `pyautogui` [@pyautogui2024].

## `narration/` — The Audio Track

The narration subsystem owns text-to-speech, script generation, and synchronization. `narration/tts.py` defines the `TTSBackend` interface, the default `SilentTTSBackend`, the zero-pip real-voice `SystemTTSBackend` (macOS `say` / Linux `espeak`), and the guarded `KokoroTTSBackend` [@kokoro2025] and `ChatterboxTTSBackend` [@chatterbox2025] ([@sec:architecture]). `narration/sync.py` defines the `Transcriber` interface, the deterministic `HeuristicTranscriber`, the guarded `WhisperTranscriber` [@radford2023whisper], and the `sync_demo` and `absolute_word_timestamps` functions that close the TTS→STT round-trip ([@sec:synchronization]). `narration/script.py` builds a declarative `Demo` from structured context — its `generate_codebase_demo` converts a list of module summaries (from the codebase subsystem) into scenes, chunks, trigger-bearing actions, and narration — so a demo can be *generated* programmatically rather than hand-authored.

## `assembly/` — Timeline, Audio, and Animation

The assembly subsystem turns the demo into a rendered timeline and a moving video. `assembly/compositor.py` defines the pure `Timeline` data structure and `build_timeline`, which walks scenes and chunks to produce a gap-free, non-overlapping sequence of `TimelineEntry` objects — each pairing an absolute time window with a `FrameState` derived by replaying that chunk's actions (`_state_for_chunk`). It defines the `Compositor` interface and the default `ManifestCompositor` (which writes `render_manifest.json` and one PNG per entry, delegating frame drawing to the synthetic renderer).

`assembly/audio.py` post-processes the voiceover with pure-stdlib primitives plus guarded `ffmpeg` steps. `concat_with_gaps` concatenates the per-chunk WAVs in order, inserting lead, inter-chunk, and trail silences generated at the clips' own `(channels, sampwidth, framerate)` so nothing resamples; `measure_duration_ms` reads true durations from the WAV header. `normalize_audio` applies `ffmpeg`'s `loudnorm` filter — the EBU R128 [@ebu2020r128; @ffmpegloudnorm2024] integrated-loudness, true-peak, and loudness-range standard, defaulting to −16 LUFS — and `apply_fade` adds gentle in/out fades; both are guarded and raise `BackendUnavailableError` when `ffmpeg` is absent.

`assembly/animator.py` re-samples the one-frame-per-chunk output onto a fixed `animation_fps` and, for each instant, composites the active chunk's base frame, a moving **speech waveform** drawn into the reserved bottom band with a sweeping playhead, and a thin **progress bar** under the chrome; it crossfades across scene boundaries, re-renders flagged chunks through the **typing reveal** so code types in character-by-character, draws an **animated cursor** with a click ripple where a chunk supplies a `cursor_xy`, and carries an optional **Ken Burns** zoom that is off by default so figures and pages stay un-cropped ([@sec:composition]). The typing reveal is the most involved of these: for a flagged chunk the animator re-renders that chunk's `FrameState` at a `cursor_typed` count that grows with within-chunk time (capped so the chunk finishes typing after `typing_fraction` of its window), caching each distinct partial render so the cost is bounded by the number of *distinct* typed states rather than the frame count. The procedure is:

```python
# Per output frame at time t_ms, for the active chunk idx (flagged for typing):
start, end = windows[idx]                     # the chunk's measured window
total = sum(len(line) for line in state.code_lines)
win   = max(1, end - start)
frac  = (t_ms - start) / win / typing_fraction   # 0..1 over the first 70%
typed = int(total * min(1.0, frac))           # characters revealed so far
key   = (idx, typed)
if key not in cache:                          # cache distinct partial renders
    s = copy(frame_states[idx]); s.cursor_typed = typed
    cache[key] = renderer.render(s, size)     # pygments re-highlights the partial source
frame = cache[key]                            # then overlay waveform, progress, cursor
```

The waveform is computed by `animation/waveform.py`, whose `compute_envelope` reduces a 16-bit PCM WAV to normalized RMS amplitude buckets (the only disk-touching step) and whose `draw_waveform` paints mirrored played/unplayed bars; [@fig:waveform] shows the resulting scrubber at 55% progress. `animation/diagram.py` renders the architecture diagrams (such as [@fig:architecture]); `assembly/captions.py` emits SRT, VTT, and ASS subtitles purely from the demo, including a word-level path driven by `absolute_word_timestamps`; and `assembly/effects.py` provides pure Pillow image effects.

![A speech-waveform scrubber rendered by `render_waveform_strip` from a real WAV envelope at 55% progress: mirrored amplitude bars with the played portion lit (left) and the unplayed portion dimmed (right), and a thin playhead at the boundary. The animator draws this band over every frame, locked to the measured audio.](figures/waveform.png){#fig:waveform}

## `animation/`, `codebase/`, `export/`, and `paper/`

The remaining subsystems round out the build. `animation/zoom.py` and `animation/highlights.py` compute cursor-following zoom/pan and code emphasis purely; `animation/manim_scenes.py` specifies Manim [@manim2024] code-walkthrough scenes, in the manner of code-video-generator [@codevideogenerator2023] and Code2Video [@code2video2025], behind the `animation` extra. The codebase subsystem summarizes source for tours: `codebase/walker.py` extracts a `ModuleSummary` — docstring, top-level functions, classes and methods, imports, line count — using only the stdlib `ast` module, with `tree-sitter` [@treesitter2024] as the optional multi-language upgrade; `codebase/ast_viz.py` and `codebase/dependency.py` render summaries and import graphs.

The export subsystem produces deliverables. `export/formats.py` serializes a demo to JSON and a Markdown transcript; `export/interactive.py` renders a self-contained, dependency-free HTML player via a Jinja2 template, embedding the resolved timeline so the demo can be scrubbed in a browser with no server; `export/video.py` encodes the animated frames against the assembled, normalized voiceover into an H.264 MP4 with `ffmpeg` (the optional `video` extra swaps in MoviePy [@moviepy2024] for scripted compositing); and `export/verify.py` content-asserts the result ([@sec:evaluation]). The `paper/` subsystem — `pdf.py`, `extract.py`, and `script.py` — turns a research paper into a narrated demo and is the subject of [@sec:paper]. As elsewhere, the core build yields a genuine, shareable deliverable — the interactive HTML player and the transcript — while the heavy backends add the encoded video.
