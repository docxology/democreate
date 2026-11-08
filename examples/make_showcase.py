#!/usr/bin/env python
"""Build the definitive "DemoCreate showcase" demo artifact (v0.8.0).

This self-referential tour includes slides, typed codebase views, illustrative
terminal output and fitted figure backgrounds. Camera zoom or overlays can
obscure content. The canonical recipe selects a real Kokoro voice; a silent
render does not establish voiced narration or acoustic alignment.

It reuses generated assets (regenerate with ``examples/make_assets.py`` and
``docs/manuscript/figures/make_figures.py``):

* ``examples/assets/architecture.png`` — generated architecture diagram
* ``examples/assets/dashboard.png`` — illustrative player image
* ``docs/manuscript/figures/graphical_abstract.png`` — the one-glance cover
* ``docs/manuscript/figures/themes.png``    — the five-theme strip
* ``docs/manuscript/figures/paper_fig.png`` — a real research-paper figure

Render it to an animated 4K MP4 with a real voiceover via::

    uv run democreate render examples/democreate_showcase.json -o output \
        --tts kokoro --voice af_heart --resolution 2160p \
        --author "Daniel Ari Friedman" --watermark "github.com/docxology/democreate"
"""

from __future__ import annotations

import shutil
from pathlib import Path

from democreate.schema import Action, ActionType, Chunk, Demo, Scene, SceneKind

_REPO = Path(__file__).resolve().parents[1]
_ASSETS = Path("assets")
_FIGS = _REPO / "docs" / "manuscript" / "figures"


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
        scene.context["background_image"] = bg.as_posix()
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
    """Construct the definitive showcase demo (~15 scenes)."""
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
               "One declarative artifact describes a codebase or research paper "
               "and compiles into frames, captions and video. Its provenance "
               "records are unsigned, not authentication.",
               title="The whole idea", bg=_ASSETS / "graphical_abstract.png",
               trigger="glance"),

        # 3 — What it is (bullet slide)
        _slide("what", "What it is",
               "A demo is a declarative spine: scenes of narration chunks, each an "
               "ordered stream of typed actions. Three ideas carry the whole system.",
               title="A demo is a value, not a recording",
               bullets=[
                   "Core defaults reproduce bytes for the same artifact, assets, "
                   "configuration and environment.",
                   "Optional adapters load on demand; default narration is "
                   "silent, not an automatically installed neural voice.",
                   "Measured WAV durations set clip windows; word positions "
                   "remain character-weighted estimates.",
               ],
               trigger="three"),

        # 4 — The declarative spine (code, types in)
        _code("spine", "The Spine",
              "The spine is plain data: scenes contain narration chunks and typed "
              "actions. Synthesis records audio paths and measured timing in the "
              "resolved output artifact.",
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
              "Interfaces separate the core defaults from optional adapters. "
              "Silent narration uses the standard library; a system voice needs "
              "a usable speech binary. This canonical recipe selects locally "
              "provisioned Kokoro.",
              "src/democreate/narration/tts.py",
              "class TTSBackend(ABC):\n"
              "    @abstractmethod\n"
              "    def synthesize(self, text, out_path, *, voice=None): ...\n"
              "\n"
              "class SilentTTSBackend(TTSBackend):   # no heavy deps\n"
              "class SystemTTSBackend(TTSBackend):   # macOS say / espeak\n"
              "class KokoroTTSBackend(TTSBackend):   # neural, optional",
              highlight=[5, 6], trigger="interface"),

        # 6 — Audio is ground truth (code, types in)
        _code("sync", "Sync",
              "Clip duration is measured. Word timing is estimated: the default "
              "transcriber spreads known text across the clip by character length. "
              "It does not detect spoken word onsets.",
              "src/democreate/narration/sync.py",
              "clips = synthesize_demo(demo, ws)\n"
              "sync_demo(demo, clips)        # duration-based word estimates\n"
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
                   "The canonical recipe selects Kokoro with local model files; "
                   "the default backend remains silent.",
                   "The waveform samples assembled audio at output-frame times.",
                   "Backgrounds start fitted to the viewport; camera zoom and "
                   "overlays can crop or obscure content.",
               ],
               trigger="generated"),

        # 8 — Themes (themes strip background)
        _slide("themes", "Configurable",
               "YAML configuration selects themes, layout, resolution presets "
               "including four K, and encoding controls. Actual quality depends "
               "on input detail and encoding settings.",
               title="Fully configurable", bg=_ASSETS / "themes.png", trigger="themes"),

        # 9 — Research papers (real figure background)
        _slide("paper", "Research Papers",
               "PDF text extraction uses poppler system binaries. Abstract, "
               "section and caption detection are heuristic. Figure backgrounds "
               "need locally available images.",
               title="Papers, not just packages", bg=_ASSETS / "paper_fig.png",
               trigger="paper"),

        # 9b — Describes ANY codebase (the 0.7.0 portfolio capability)
        _slide("portfolio", "Describe repositories",
               "A portfolio pass describes repository folders from README files "
               "and Python definitions. It attempts one video per selected project "
               "and reports failures, rather than inventing unsupported details.",
               title="One video per project, automatically",
               bullets=[
                   "Portfolio reads available README text, Python definitions "
                   "and bounded repository statistics.",
                   "Selection and extraction do not use a language model; "
                   "voiced video still needs working TTS and ffmpeg.",
                   "This showcase is hand authored; portfolio shares its "
                   "rendering and export pipeline.",
               ],
               trigger="repositories"),

        # 10 — Architecture (diagram background)
        _slide("arch", "Architecture",
               "Eight subsystems share a declarative spine. Narration, rendering "
               "and export also depend on configuration, assets and the selected "
               "runtime environment.",
               title="Eight subsystems, one spine",
               bg=_ASSETS / "architecture.png", trigger="subsystems"),

        # 11 — By the numbers (stat slide)
        _slide("numbers", "By the numbers",
               "Engineering gates check the core with real files and a coverage "
               "threshold. Eight subsystems, five themes, four K presets, and "
               "no external media executables for the core build.",
               title="DemoCreate by the numbers",
               stats=[(">=90%", "core coverage gate"), ("8", "subsystems"),
                      ("5", "built-in themes"), ("4K", "resolution preset"),
                      ("0", "required media tools")],
               trigger="real"),

        # 12 — Provenance (bullet slide)
        _slide("provenance", "Provenance",
               "Renders carry attribution three ways. These records are unsigned: "
               "they associate content, but do not authenticate an author or video.",
               title="Unsigned provenance and consistency",
               bullets=[
                   "On-screen metadata bars — author, source, a running clock.",
                   "Container tags in the MP4, readable by any player or ffprobe.",
                   "An unsigned poster payload checks a Demo digest; it does not "
                   "authenticate cover pixels, video bytes or authorship.",
               ],
               trigger="three"),

        # 13 — Build + render (terminal)
        _terminal("render", "Render",
                  "Rendering and basic verification check stream shape, audio "
                  "energy and sampled picture variance. These checks do not "
                  "establish intelligibility or acoustic word alignment.",
                  "democreate render demo.json --tts kokoro --voice af_heart",
                  "Illustrative output — not executed by DemoCreate: verification summary",
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
        title="DemoCreate: The Showcase",
        scenes=scenes,
        width=1920,
        height=1080,
        fps=30,
        voice="af_heart",
        metadata={"author": "Daniel Ari Friedman", "self_referential": True,
                  "version": "0.8.0"},
    )


def main() -> None:
    """Write the showcase demo artifact next to this script."""
    for name in ("graphical_abstract.png", "themes.png", "paper_fig.png"):
        source = _FIGS / name
        target = Path(__file__).resolve().parent / "assets" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    demo = build()
    problems = demo.validate()
    if problems:
        raise SystemExit(f"demo invalid: {problems}")
    out = _REPO / "examples" / "democreate_showcase.json"
    out.write_text(demo.to_json(), encoding="utf-8")
    print(f"wrote {out} — {len(demo.scenes)} scenes, {len(demo.iter_chunks())} chunks")


if __name__ == "__main__":
    main()
