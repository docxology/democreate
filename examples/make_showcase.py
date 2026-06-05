#!/usr/bin/env python
"""Build the definitive "DemoCreate showcase" demo artifact (v0.6.2).

This is the most comprehensive self-referential demo: a tightly-paced, narrated
tour that exercises *every* renderable surface — a title card, a one-glance
graphical abstract, **bullet slides**, **stat-card slides**, autosizing **code**
scenes that type in, real **figure/diagram/screenshot** backgrounds (shown whole,
never cropped), **terminal** scenes, and a closing card — all locked to a real
spoken voiceover with a moving waveform.

It reuses generated assets (regenerate with ``examples/make_assets.py`` and
``manuscript/figures/make_figures.py``):

* ``examples/assets/architecture.png`` — generated architecture diagram
* ``examples/assets/dashboard.png``    — real browser screenshot of the player
* ``manuscript/figures/graphical_abstract.png`` — the one-glance cover
* ``manuscript/figures/themes.png``    — the five-theme strip
* ``manuscript/figures/paper_fig.png`` — a real research-paper figure

Render it to an animated HD MP4 with a real voiceover via::

    democreate render examples/democreate_showcase.json -o output --voice Samantha \
        --author "Daniel Ari Friedman" --watermark "github.com/docxology/democreate"
"""

from __future__ import annotations

from pathlib import Path

from democreate.schema import Action, ActionType, Chunk, Demo, Scene, SceneKind

_REPO = Path(__file__).resolve().parents[1]
_ASSETS = _REPO / "examples" / "assets"
_FIGS = _REPO / "manuscript" / "figures"


def _slide(id_, section, narration, *, title="", subtitle="", bg=None,
           bullets=None, stats=None, trigger=None) -> Scene:
    """A SLIDE scene — a title card, a bullet list, a stat row, or a background."""
    scene = Scene(id=id_, title=title or section, kind=SceneKind.SLIDE)
    actions = []
    if bg is not None:
        actions.append(Action(ActionType.OPEN_FILE, {"path": title or section},
                              trigger_word=trigger))
    scene.context["section"] = section
    if subtitle:
        scene.context["subtitle"] = subtitle
    if bg is not None:
        scene.context["background_image"] = str(bg)
    if bullets:
        scene.context["bullets"] = bullets
    if stats:
        scene.context["stats"] = stats
    scene.chunks.append(Chunk(id=f"{id_}-c", text=narration, actions=actions))
    return scene


def _code(id_, section, narration, path, code, *, highlight=None, trigger=None) -> Scene:
    """A CODEBASE scene whose code types in character-by-character."""
    scene = Scene(id=id_, title=path, kind=SceneKind.CODEBASE)
    scene.context["section"] = section
    actions = [Action(ActionType.CREATE_FILE, {"path": path, "code": code},
                      trigger_word=trigger)]
    if highlight:
        actions.append(Action(ActionType.HIGHLIGHT_LINES, {"lines": highlight},
                              trigger_word=trigger))
    scene.chunks.append(Chunk(id=f"{id_}-c", text=narration, actions=actions))
    return scene


def _terminal(id_, section, narration, command, output, *, trigger=None) -> Scene:
    scene = Scene(id=id_, title="terminal", kind=SceneKind.TERMINAL)
    scene.context["section"] = section
    scene.chunks.append(Chunk(id=f"{id_}-c", text=narration, actions=[
        Action(ActionType.RUN_COMMAND, {"command": command, "output": output},
               trigger_word=trigger)]))
    return scene


def build() -> Demo:
    """Construct the definitive showcase demo (1080p, ~14 scenes)."""
    scenes: list[Scene] = [
        # 1 — Hero title
        _slide("title", "DemoCreate",
               "What if a demo video was not a recording you capture, but a value "
               "you compile? This is DemoCreate.",
               title="DemoCreate",
               subtitle="Declarative, deterministic narrated demos",
               trigger="compile"),

        # 2 — The whole idea at a glance (graphical abstract)
        _slide("abstract", "At a glance",
               "One declarative artifact — describing a codebase or a research "
               "paper — compiles through a deterministic pipeline into a verified, "
               "provenance-signed video. Here is the whole idea on one screen.",
               title="The whole idea", bg=_FIGS / "graphical_abstract.png",
               trigger="glance"),

        # 3 — What it is (bullet slide)
        _slide("what", "What it is",
               "A demo is a declarative spine: scenes of narration chunks, each an "
               "ordered stream of typed actions. Three ideas carry the whole system.",
               title="A demo is a value, not a recording",
               bullets=[
                   "Rendering is a pure function of the artifact — edit it and "
                   "re-render, never re-record.",
                   "Every heavy backend has a pure-Python or system-binary default, "
                   "so a real demo needs zero heavy installs.",
                   "Audio is the single source of timing truth: frames are locked "
                   "to the measured voiceover.",
               ],
               trigger="three"),

        # 4 — The declarative spine (code, types in)
        _code("spine", "The Spine",
              "The spine is plain data. A demo is scenes; a scene is chunks; a "
              "chunk is typed actions. Rendering never mutates it.",
              "src/democreate/schema.py",
              "@dataclass\n"
              "class Demo:\n"
              "    title: str\n"
              "    scenes: list[Scene]\n"
              "    width: int = 1920\n"
              "    height: int = 1080\n"
              "\n"
              "@dataclass\n"
              "class Action:\n"
              "    type: ActionType\n"
              "    params: dict\n"
              "    trigger_word: str | None = None",
              highlight=[2, 3, 4], trigger="data"),

        # 5 — Deterministic defaults (code, types in)
        _code("backends", "Backends",
              "Every capability hides behind an interface with a deterministic "
              "default. Silent gives you zero dependencies; the system voice is a "
              "real OS binary; neural backends are an optional upgrade.",
              "src/democreate/narration/tts.py",
              "class TTSBackend(ABC):\n"
              "    @abstractmethod\n"
              "    def synth(self, text: str) -> AudioClip: ...\n"
              "\n"
              "class SilentTTSBackend(TTSBackend):   # zero deps\n"
              "class SystemTTSBackend(TTSBackend):   # macOS say / espeak\n"
              "class KokoroTTSBackend(TTSBackend):   # neural, optional",
              highlight=[5, 6], trigger="interface"),

        # 6 — Audio is ground truth (code, types in)
        _code("sync", "Sync",
              "Timing is measured, never guessed. We synthesize the narration, "
              "measure its real duration, transcribe it back to word timestamps, "
              "and anchor each action to the word it is spoken on.",
              "src/democreate/narration/sync.py",
              "clips = synthesize_demo(demo, ws)\n"
              "sync_demo(demo, clips)        # TTS -> STT\n"
              "for action in chunk.actions:\n"
              "    action.timestamp_ms = word_time(action.trigger_word)\n"
              "# every frame is held for its measured clip",
              highlight=[2, 4], trigger="measured"),

        # 7 — The craft you are watching (bullet slide, meta)
        _slide("craft", "The Craft",
               "Everything you are watching is generated from that spine. The code "
               "you just saw typed itself in. Look at this frame.",
               title="What you are seeing, right now",
               bullets=[
                   "The narration is a real spoken voice — macOS say, zero pip.",
                   "The waveform below sweeps in lockstep with the audio.",
                   "Nothing is cropped: figures fit whole, code autosizes — the "
                   "frame is a page, not a camera.",
               ],
               trigger="generated"),

        # 8 — Themes (themes strip background)
        _slide("themes", "Configurable",
               "One commented YAML controls the whole look and sound — five built-in "
               "themes, any aspect ratio, resolution up to four K, and "
               "near-lossless quality.",
               title="Fully configurable", bg=_FIGS / "themes.png", trigger="themes"),

        # 9 — Research papers (real figure background)
        _slide("paper", "Research Papers",
               "The same engine demos a research paper: it reads the PDF with no "
               "Python dependency, recovers the real abstract, the real figure "
               "captions, and the sections — and shows each figure whole.",
               title="Papers, not just packages", bg=_FIGS / "paper_fig.png",
               trigger="paper"),

        # 10 — Architecture (diagram background)
        _slide("arch", "Architecture",
               "Under the hood, seven subsystems compose: the spine flows into "
               "narration, then rendering, then export — every stage a pure "
               "function of the one artifact.",
               title="Seven subsystems, one spine",
               bg=_ASSETS / "architecture.png", trigger="subsystems"),

        # 11 — By the numbers (stat slide)
        _slide("numbers", "By the numbers",
               "And it is real. Nearly six hundred tests, seven subsystems, five "
               "themes, four K output — and zero pip dependencies for the core.",
               title="DemoCreate by the numbers",
               stats=[("625", "tests passing"), ("7", "subsystems"),
                      ("5", "built-in themes"), ("4K", "max resolution"),
                      ("0", "pip for core")],
               trigger="real"),

        # 12 — Provenance (bullet slide)
        _slide("provenance", "Provenance",
               "Every render carries its own provenance, three ways — so a video "
               "can prove where it came from, and resist tampering.",
               title="Signed, tamper-evident provenance",
               bullets=[
                   "On-screen metadata bars — author, source, a running clock.",
                   "Container tags in the MP4, readable by any player or ffprobe.",
                   "A steganographic signed poster whose hash verifies against the "
                   "demo and fails on any edit.",
               ],
               trigger="three"),

        # 13 — Build + render (terminal)
        _terminal("render", "Render",
                  "Then one command renders a high-definition video with a real "
                  "voiceover, and proves it is genuine — real streams, not silent, "
                  "not black.",
                  "democreate render demo.json --voice Samantha",
                  "✓ verified: real video + non-silent audio",
                  trigger="renders"),

        # 14 — Outro
        _slide("outro", "Dogfooded",
               "Declarative. Deterministic. Dogfooded. This entire video was "
               "compiled by DemoCreate from one file. Edit it, re-render, and never "
               "record a take again.",
               title="DemoCreate",
               subtitle="github.com/docxology/democreate",
               trigger="dogfooded"),
    ]

    return Demo(
        title="DemoCreate — The Showcase",
        scenes=scenes,
        width=1920,
        height=1080,
        fps=30,
        voice="Samantha",
        metadata={"author": "Daniel Ari Friedman", "self_referential": True,
                  "version": "0.6.2"},
    )


def main() -> None:
    """Write the showcase demo artifact next to this script."""
    demo = build()
    problems = demo.validate()
    if problems:
        raise SystemExit(f"demo invalid: {problems}")
    out = _REPO / "examples" / "democreate_showcase.json"
    out.write_text(demo.to_json(), encoding="utf-8")
    print(f"wrote {out} — {len(demo.scenes)} scenes, {len(demo.iter_chunks())} chunks")


if __name__ == "__main__":
    main()
