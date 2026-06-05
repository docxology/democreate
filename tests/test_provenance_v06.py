"""Tests for v0.6: resolution/quality config, overlays, container metadata, stego CLI."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image
from typer.testing import CliRunner

from democreate.cli import app
from democreate.config import RESOLUTIONS, MetadataConfig, RenderConfig

runner = CliRunner()


# --- config: resolution + quality + commented yaml ------------------------

def test_set_resolution_tiers() -> None:
    c = RenderConfig()
    c.set_resolution("2160p")
    assert (c.video.width, c.video.height) == RESOLUTIONS["2160p"] == (3840, 2160)
    c.set_resolution("720p")
    assert (c.video.width, c.video.height) == (1280, 720)


def test_default_quality_is_high() -> None:
    assert RenderConfig().video.crf == 18  # near-visually-lossless default


def test_commented_yaml_parses_and_documents() -> None:
    y = RenderConfig.commented_yaml("paper")
    assert "# DemoCreate render configuration" in y
    assert "crf:" in y and "metadata:" in y and "steganography:" in y
    cfg = RenderConfig.from_yaml(y)
    assert cfg.theme.name == "paper"


def test_metadata_config_in_render_config() -> None:
    c = RenderConfig()
    assert isinstance(c.metadata, MetadataConfig)
    assert c.metadata.footer is True and c.metadata.steganography is True
    c.metadata.author = "Ada"
    c2 = RenderConfig.from_yaml(c.to_yaml())
    assert c2.metadata.author == "Ada"


# --- CLI: config command --------------------------------------------------

def test_cli_config_writes_commented_yaml(tmp_path: Path) -> None:
    out = tmp_path / "cfg.yaml"
    res = runner.invoke(app, ["config", str(out), "--theme", "midnight"])
    assert res.exit_code == 0
    text = out.read_text(encoding="utf-8")
    assert "theme: midnight" in text
    assert RenderConfig.from_yaml(text).theme.name == "midnight"


# --- overlay wiring in the animator ---------------------------------------

def test_animator_draws_overlay_band(tmp_path: Path) -> None:
    import struct
    import wave

    from democreate.assembly.animator import AnimationConfig, render_animation_frames
    from democreate.media import AudioClip, FrameState
    from democreate.schema import SceneKind

    p = tmp_path / "f0.png"
    Image.new("RGB", (640, 360), (18, 20, 26)).save(p)
    clip = AudioClip(path=tmp_path / "a.wav", duration_ms=1000, chunk_id="c0")
    n = int(22050 * 1.0)
    with wave.open(str(tmp_path / "v.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", 5000 if i % 2 else -5000) for i in range(n)))
    meta = MetadataConfig(author="Ada", footer=True, header=False)
    state = FrameState(scene_kind=SceneKind.CODEBASE, section="Intro")
    written, _ = render_animation_frames(
        [p], [clip], tmp_path / "v.wav", tmp_path / "anim", size=(640, 360),
        config=AnimationConfig(fps=8, bars=20, cursor=False),
        frame_states=[state], overlay_meta=meta, demo_title="My Demo",
    )
    # the bottom edge band should differ from the plain base (footer drawn)
    base_band = Image.open(p).crop((0, 344, 640, 360)).tobytes()
    frame_band = Image.open(written[3]).crop((0, 344, 640, 360)).tobytes()
    assert frame_band != base_band


# --- stego CLI ------------------------------------------------------------

def test_cli_stego_extract_and_verify(tmp_path: Path) -> None:
    from democreate.export.stego import embed_provenance
    from democreate.schema import Chunk, Demo, Scene

    demo = Demo(title="Signed", scenes=[Scene(id="s", chunks=[Chunk(id="c", text="hi")])])
    demo_path = tmp_path / "d.json"
    demo_path.write_text(demo.to_json(), encoding="utf-8")
    img = Image.new("RGB", (300, 200), (30, 40, 60))
    stego_img, _ = embed_provenance(img, demo, author="Ada", version="0.6.0")
    signed = tmp_path / "signed.png"
    stego_img.save(signed, format="PNG")

    res = runner.invoke(app, ["stego", str(signed), "--demo", str(demo_path)])
    assert res.exit_code == 0
    assert "matches the demo" in res.stdout

    # tamper → non-zero exit
    demo.title = "Tampered"
    demo_path.write_text(demo.to_json(), encoding="utf-8")
    res2 = runner.invoke(app, ["stego", str(signed), "--demo", str(demo_path)])
    assert res2.exit_code == 1


def test_cli_stego_extract_only(tmp_path: Path) -> None:
    from democreate.export.stego import embed_provenance
    from democreate.schema import Chunk, Demo, Scene

    demo = Demo(title="P", scenes=[Scene(id="s", chunks=[Chunk(id="c", text="x")])])
    img = Image.new("RGB", (200, 200), (10, 10, 10))
    stego_img, _ = embed_provenance(img, demo, author="Bob")
    signed = tmp_path / "s.png"
    stego_img.save(signed, format="PNG")
    res = runner.invoke(app, ["stego", str(signed)])
    assert res.exit_code == 0
    assert "democreate" in res.stdout


# --- container metadata build ---------------------------------------------

def test_build_tags_from_metadata() -> None:
    from democreate.export.metadata import build_tags
    from democreate.schema import Chunk, Demo, Scene

    demo = Demo(title="T", scenes=[Scene(id="s", chunks=[Chunk(id="c", text="x")])])
    tags = build_tags(demo, MetadataConfig(author="Ada", source="repo/x"), version="0.6.0")
    assert tags["title"] == "T"
    assert tags["artist"] == "Ada"
    assert "DemoCreate" in tags["comment"]
    assert json.dumps(tags)  # serializable
