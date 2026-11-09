"""Behavioral regressions for output custody and portable asset staging."""
from __future__ import annotations

import json
import struct
import zlib
from pathlib import Path

import pytest
from PIL import Image

from democreate import Chunk, Demo, Pipeline, Scene, SceneKind, Workspace
from democreate.errors import RenderError


def _demo(image: Path | None = None) -> Demo:
    return Demo(
        title="Owned assets", width=320, height=180,
        scenes=[Scene(id="s", kind=SceneKind.SLIDE,
                      context={"background_image": str(image)} if image else {},
                      chunks=[Chunk(id="c", text="A short narration.")])],
    )


@pytest.mark.parametrize("relative", [
    "audio/chunk_0000.wav", "demos/transcript.md",
    "frames/frame_0000.png", "web/player.html",
])
def test_build_refuses_existing_linked_output(tmp_path: Path, relative: str) -> None:
    workspace = Workspace(tmp_path / "build")
    victim = tmp_path / "outside"
    victim.write_bytes(b"preserve original data")
    linked = workspace.root / relative
    linked.parent.mkdir(parents=True, exist_ok=True)
    linked.symlink_to(victim)
    with pytest.raises(RenderError, match="symbolic link"):
        Pipeline().run(_demo(), workspace)
    assert victim.read_bytes() == b"preserve original data"
    assert not (workspace.root / "manifests").exists()


def test_build_refuses_linked_output_directory(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "build")
    outside = tmp_path / "outside"
    outside.mkdir()
    workspace.root.mkdir()
    (workspace.root / "audio").symlink_to(outside, target_is_directory=True)
    with pytest.raises(RenderError, match="symbolic link"):
        Pipeline().run(_demo(), workspace)
    assert list(outside.iterdir()) == []


def test_background_requires_explicit_input_authority(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    private = tmp_path / "private.png"
    Image.new("RGB", (100, 60), "red").save(private)
    workspace = Workspace(tmp_path / "build")
    with pytest.raises(RenderError, match="outside the asset root"):
        Pipeline(asset_root=allowed).run(_demo(private), workspace)
    assert not workspace.root.exists()
    (allowed / "linked.png").symlink_to(private)
    with pytest.raises(RenderError, match="outside the asset root"):
        Pipeline(asset_root=allowed).run(_demo(Path("linked.png")), workspace)


def test_missing_required_background_fails_before_rendering(tmp_path: Path) -> None:
    workspace = Workspace(tmp_path / "build")
    with pytest.raises(RenderError, match="required background image is missing"):
        Pipeline(asset_root=tmp_path).run(_demo(Path("missing.png")), workspace)
    assert not workspace.root.exists()


def test_staged_assets_and_manifests_are_workspace_independent(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    image = inputs / "figure.png"
    Image.new("RGB", (100, 60), "blue").save(image)
    results = [
        Pipeline(asset_root=inputs).run(_demo(Path("figure.png")), Workspace(tmp_path / name))
        for name in ("first", "second")
    ]
    assert results[0].manifest_path.read_bytes() == results[1].manifest_path.read_bytes()
    assert results[0].demo_path.read_bytes() == results[1].demo_path.read_bytes()
    for result in results:
        serialized = json.loads(result.demo_path.read_text())
        relative = Path(serialized["scenes"][0]["context"]["background_image"])
        assert not relative.is_absolute()
        assert relative.parts[0] == "assets"
        assert (result.workspace.root / relative).read_bytes() == image.read_bytes()


@pytest.mark.parametrize("corruption", ["unidentified", "crc"])
def test_invalid_background_fails_before_generating_artifacts(
    tmp_path: Path, corruption: str
) -> None:
    image = tmp_path / "invalid.png"
    if corruption == "crc":
        Image.new("RGB", (24, 24), "red").save(image)
        data = bytearray(image.read_bytes())
        data[data.index(b"IDAT") + 4] ^= 1
        image.write_bytes(data)
    else:
        image.write_bytes(b"not an image")
    workspace = Workspace(tmp_path / "build")
    with pytest.raises(RenderError, match="background image"):
        Pipeline(asset_root=tmp_path).run(_demo(image), workspace)
    assert not workspace.root.exists()


def test_authored_demo_can_be_reused_with_updated_assets(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    image = inputs / "figure.png"
    Image.new("RGB", (100, 60), "blue").save(image)
    demo = _demo(Path("figure.png"))
    authored = demo.to_json()
    pipeline = Pipeline(asset_root=inputs)
    first = pipeline.run(demo, Workspace(tmp_path / "first"))
    first_frame = first.frame_paths[0].read_bytes()
    Image.new("RGB", (100, 60), "green").save(image)
    second = pipeline.run(demo, Workspace(tmp_path / "second"))
    assert demo.to_json() == authored
    assert second.frame_paths[0].read_bytes() != first_frame
    assert first.frame_paths[0].read_bytes() == first_frame


def test_invalid_pixel_stream_preserves_prior_build_and_inputs(tmp_path: Path) -> None:
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    image = inputs / "figure.png"
    Image.new("RGB", (24, 24), "blue").save(image)
    workspace = Workspace(tmp_path / "build")
    pipeline = Pipeline(asset_root=inputs)
    prior = pipeline.run(_demo(Path("figure.png")), workspace)
    assert prior.manifest_path is not None
    assert prior.clips[0].path.is_file() and prior.frame_paths[0].is_file()
    protected = {
        path: path.read_bytes()
        for path in workspace.root.rglob("*")
        if path.is_file()
    }

    def png_chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload))
        )

    # Every chunk CRC is valid, but IDAT is not a decodable zlib pixel stream.
    invalid = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", b"not a zlib pixel stream")
        + png_chunk(b"IEND", b"")
    )
    image.write_bytes(invalid)
    with Image.open(image) as container:
        container.verify()
    with Image.open(image) as pixels, pytest.raises(OSError):
        pixels.convert("RGB")

    demo = _demo(Path("figure.png"))
    demo.scenes[0].chunks[0].text = (
        "Different, much longer narration would replace the prior WAV if "
        "required pixel decoding were deferred until frame rendering."
    )
    authored = demo.to_json()
    authored_path = inputs / "demo.json"
    authored_path.write_text(authored, encoding="utf-8")
    authored_bytes = authored_path.read_bytes()
    with pytest.raises(RenderError, match="cannot decode background image") as exc:
        pipeline.run(demo, workspace)
    assert isinstance(exc.value.__cause__, OSError)
    assert {
        path: path.read_bytes()
        for path in workspace.root.rglob("*")
        if path.is_file()
    } == protected
    assert demo.to_json() == authored
    assert authored_path.read_bytes() == authored_bytes
    assert image.read_bytes() == invalid
