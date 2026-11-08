"""Cross-artifact frame identity across scene boundaries."""
from __future__ import annotations

from pathlib import Path


def test_player_cues_resolve_the_correct_rendered_scene(tmp_path: Path) -> None:
    """A scene boundary must not reset frame names onto an earlier scene's image."""
    from PIL import Image

    from democreate.export.interactive import build_timeline
    from democreate.pipeline import Pipeline
    from democreate.project_paths import Workspace
    from democreate.schema import Chunk, Demo, Scene, SceneKind

    blue, red = (20, 80, 160), (180, 30, 40)
    for name, color in (("blue", blue), ("red", red)):
        Image.new("RGB", (64, 32), color).save(tmp_path / f"{name}.png")
    demo = Demo(title="Scenes", width=320, height=180, scenes=[
        Scene(id="one", kind=SceneKind.SLIDE,
              context={"background_image": "blue.png"},
              chunks=[Chunk(id="a", text="first"), Chunk(id="b", text="second")]),
        Scene(id="two", kind=SceneKind.SLIDE,
              context={"background_image": "red.png"},
              chunks=[Chunk(id="c", text="third")]),
    ])
    result = Pipeline(asset_root=tmp_path).run(demo, Workspace(tmp_path / "run"))
    visible_colors = []
    for cue in build_timeline(result.demo)["captions"]:
        with Image.open(result.workspace.frames / cue["frame"]) as frame:
            visible_colors.append(frame.convert("RGB").getpixel((160, 90)))
    assert visible_colors == [blue, blue, red]
