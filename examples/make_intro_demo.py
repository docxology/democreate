#!/usr/bin/env python
"""Build the canonical "DemoCreate explains itself" demo artifact (comprehensive).

Running this writes ``examples/democreate_intro.json`` — a declarative
:class:`~democreate.schema.Demo` that gives a big, legible, narrated tour of the
package: a title card, a real **architecture diagram**, the declarative spine,
backends-behind-interfaces, duration-based sync, an illustrative player image,
the CLI and animated-waveform rendering.

It references two image assets under ``examples/assets/`` (regenerate with
``examples/make_assets.py``):

* ``architecture.png`` — the generated architecture diagram.
* ``dashboard.png`` — an illustrative HTML-player image.

Render it to an animated HD MP4 with a real voiceover + moving waveform via::

    democreate render examples/democreate_intro.json -o output --tts kokoro --voice af_heart
"""

from __future__ import annotations

from pathlib import Path

from democreate.schema import Action, ActionType, Chunk, Demo, Scene, SceneKind

_ASSETS = Path("assets")


def _slide(id_: str, section: str, narration: str, *, title="", subtitle="", bg=None,
           trigger=None) -> Scene:
    scene = Scene(id=id_, title=title or section, kind=SceneKind.SLIDE)
    actions = []
    if bg is not None:
        # background image carried in scene context for documentation; the chunk
        # action sets it on the frame state via the compositor.
        actions.append(Action(ActionType.OPEN_FILE, {"path": title or section}, trigger_word=trigger))
    chunk = Chunk(id=f"{id_}-c", text=narration, actions=actions)
    scene.context["section"] = section
    scene.context["subtitle"] = subtitle
    if bg is not None:
        scene.context["background_image"] = bg.as_posix()
    scene.chunks.append(chunk)
    return scene


def build() -> Demo:
    """Construct the comprehensive introduction demo (1080p)."""
    scenes: list[Scene] = []

    # 1. Title card
    scenes.append(
        _slide(
            "title", "Intro",
            "DemoCreate turns a single declarative file into a narrated, high "
            "definition walkthrough of your software.",
            title="DemoCreate", subtitle="Declarative Audio-Visual Demos",
            trigger="declarative",
        )
    )

    # 2. Architecture overview (real generated diagram as background)
    scenes.append(
        _slide(
            "arch", "Architecture",
            "A declarative spine flows through narration, rendering and export. "
            "Outputs also depend on configuration, assets and the selected "
            "runtime environment.",
            title="Architecture", bg=_ASSETS / "architecture.png", trigger="stages",
        )
    )

    # 3. The declarative spine (big code)
    spine = Scene(id="spine", title="The Declarative Spine", kind=SceneKind.CODEBASE)
    spine.context["section"] = "The Spine"
    spine.chunks.append(
        Chunk(
            id="spine-c",
            text="A demo is not a recording. It is a value: scenes of narration "
            "chunks, each chunk an ordered stream of typed actions.",
            actions=[
                Action(ActionType.CREATE_FILE, {
                    "path": "src/democreate/schema.py",
                    "code": "@dataclass\nclass Demo:\n    title: str\n    scenes: list[Scene]\n\n@dataclass\nclass Action:\n    type: ActionType\n    trigger_word: str | None",
                }, trigger_word="value"),
                Action(ActionType.HIGHLIGHT_LINES, {"lines": [2, 3, 4]}, trigger_word="scenes"),
            ],
        )
    )
    scenes.append(spine)

    # 4. Backends behind interfaces (big code)
    backends = Scene(id="backends", title="Backends Behind Interfaces", kind=SceneKind.CODEBASE)
    backends.context["section"] = "Backends"
    backends.chunks.append(
        Chunk(
            id="backends-c",
            text="Core defaults run without heavy optional packages. Installed "
            "adapters can add capabilities; some declared adapters remain "
            "unwired, and voiced output needs a working speech backend.",
            actions=[
                Action(ActionType.CREATE_FILE, {
                    "path": "src/democreate/narration/tts.py",
                    "code": "class TTSBackend(ABC): ...\nclass SilentTTSBackend:   # no heavy deps\nclass SystemTTSBackend:   # needs usable OS speech\nclass KokoroTTSBackend:   # needs optional model",
                }, trigger_word="interface"),
                Action(ActionType.HIGHLIGHT_LINES, {"lines": [2, 3]}, trigger_word="default"),
            ],
        )
    )
    scenes.append(backends)

    # 5. Audio is ground truth (sync)
    sync = Scene(id="sync", title="Audio Is Ground Truth", kind=SceneKind.CODEBASE)
    sync.context["section"] = "Sync"
    sync.chunks.append(
        Chunk(
            id="sync-c",
            text="Clip durations are measured. Known words are interpolated by length, "
            "not detected acoustically. Frames and waveform use the clip timeline.",
            actions=[
                Action(ActionType.CREATE_FILE, {
                    "path": "src/democreate/narration/sync.py",
                    "code": "clips = synthesize_demo(demo, ws)\nsync_demo(demo, clips)   # measured clips, heuristic words\n# video times are quantized to output frames",
                }, trigger_word="measured"),
            ],
        )
    )
    scenes.append(sync)

    # 6. The interactive dashboard (real screenshot background)
    scenes.append(
        _slide(
            "dashboard", "Dashboard",
            "The same demo exports an HTML caption and chapter preview with "
            "per-chunk frame navigation. The HTML preview has no audio track.",
            title="Interactive Player", bg=_ASSETS / "dashboard.png", trigger="player",
        )
    )

    # 7. Build (terminal)
    build_scene = Scene(id="build", title="One Command", kind=SceneKind.TERMINAL)
    build_scene.context["section"] = "Build"
    build_scene.chunks.append(
        Chunk(
            id="build-c",
            text="One command builds the deterministic demo: audio, frames, "
            "captions, and the player.",
            actions=[Action(ActionType.RUN_COMMAND, {
                "command": "democreate build demo.json -o output",
                "output": "✓ player: output/web/player.html",
            }, trigger_word="builds")],
        )
    )
    scenes.append(build_scene)

    # 8. Render + verify (terminal)
    render_scene = Scene(id="render", title="Render And Verify", kind=SceneKind.TERMINAL)
    render_scene.context["section"] = "Render"
    render_scene.chunks.append(
        Chunk(
            id="render-c",
            text="Voiced rendering needs an explicitly selected speech backend. "
            "Basic verification checks streams, audio energy and picture variance, "
            "not intelligibility or acoustic word alignment.",
            actions=[Action(ActionType.RUN_COMMAND, {
                "command": "democreate render demo.json --tts kokoro --voice af_heart",
                "output": "Illustrative output — not executed by DemoCreate: verification summary",
            }, trigger_word="renders")],
        )
    )
    scenes.append(render_scene)

    # 9. Outro
    scenes.append(
        _slide(
            "outro", "Dogfooded",
            "This authored demonstration uses the same rendering pipeline. Edit "
            "the artifact and rebuild; inspect outputs and record their source "
            "and runtime identity before treating them as evidence.",
            title="DemoCreate", subtitle="github.com/docxology/democreate",
            trigger="dogfooded",
        )
    )

    return Demo(
        title="DemoCreate: Declarative Audio-Visual Demos",
        scenes=scenes,
        width=1920,
        height=1080,
        fps=30,
        voice="af_heart",
        metadata={"author": "Daniel Ari Friedman", "self_referential": True},
    )


def main() -> None:
    """Write the demo artifact next to this script."""
    demo = build()
    problems = demo.validate()
    if problems:
        raise SystemExit(f"demo invalid: {problems}")
    out = Path(__file__).resolve().parent / "democreate_intro.json"
    out.write_text(demo.to_json(), encoding="utf-8")
    print(f"wrote {out} — {len(demo.scenes)} scenes, {len(demo.iter_chunks())} chunks")


if __name__ == "__main__":
    main()
