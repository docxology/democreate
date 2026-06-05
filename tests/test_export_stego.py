"""Tests for :mod:`democreate.export.stego`.

All computation is real: payloads are embedded into real PIL images, saved to
real PNG files, reopened, and extracted. No mocks. Determinism is checked by
asserting exact byte round-trips.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from democreate.errors import DemoCreateError
from democreate.export import stego
from democreate.schema import Demo

PIL_Image = pytest.importorskip("PIL.Image")
Image = PIL_Image


def _solid(width: int, height: int, color=(120, 200, 35)) -> Image.Image:
    """Return a solid-color RGB image (deterministic cover material)."""
    return Image.new("RGB", (width, height), color)


# --------------------------------------------------------------------------- #
# capacity_bytes
# --------------------------------------------------------------------------- #


def test_capacity_bytes_math() -> None:
    # 100x100 px * 3 bits = 30000 bits = 3750 bytes, minus 4-byte header.
    assert stego.capacity_bytes((100, 100)) == (100 * 100 * 3) // 8 - 4
    assert stego.capacity_bytes((8, 1)) == (8 * 3) // 8 - 4  # 3 - 4 == -1


def test_capacity_grows_with_size() -> None:
    small = stego.capacity_bytes((10, 10))
    big = stego.capacity_bytes((100, 100))
    assert big > small > 0


# --------------------------------------------------------------------------- #
# embed / extract byte round-trips
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"x",
        b"hello world",
        bytes(range(256)),
        b"\x00\x00\x00\x00",
        "unicode: é☃".encode(),
    ],
)
def test_embed_extract_roundtrip(payload: bytes) -> None:
    img = _solid(64, 64)
    stego_img = stego.embed(img, payload)
    assert stego.extract(stego_img) == payload


def test_embed_does_not_mutate_original() -> None:
    img = _solid(32, 32)
    before = img.tobytes()
    stego.embed(img, b"some payload bytes")
    assert img.tobytes() == before


def test_embed_is_deterministic() -> None:
    img = _solid(40, 40)
    a = stego.embed(img, b"deterministic payload")
    b = stego.embed(img, b"deterministic payload")
    assert a.tobytes() == b.tobytes()


def test_near_capacity_roundtrip() -> None:
    img = _solid(48, 48)
    cap = stego.capacity_bytes((48, 48))
    payload = bytes((i * 7 + 3) & 0xFF for i in range(cap))
    assert len(payload) == cap
    stego_img = stego.embed(img, payload)
    assert stego.extract(stego_img) == payload


def test_exact_capacity_accepted_over_capacity_rejected() -> None:
    img = _solid(48, 48)
    cap = stego.capacity_bytes((48, 48))
    stego.embed(img, b"\x00" * cap)  # exactly at capacity: ok
    with pytest.raises(ValueError):
        stego.embed(img, b"\x00" * (cap + 1))


def test_too_large_payload_raises_value_error() -> None:
    img = _solid(16, 16)
    cap = stego.capacity_bytes((16, 16))
    with pytest.raises(ValueError):
        stego.embed(img, b"A" * (cap + 50))


def test_tiny_image_rejects_big_payload() -> None:
    img = _solid(4, 4)  # capacity = 48//8 - 4 = 2 bytes
    assert stego.capacity_bytes((4, 4)) == 2
    with pytest.raises(ValueError):
        stego.embed(img, b"this payload is way too big for a 4x4 image")


# --------------------------------------------------------------------------- #
# PNG lossless round-trip (the load-bearing survivability claim)
# --------------------------------------------------------------------------- #


def test_survives_png_save_reopen(tmp_path: Path) -> None:
    img = _solid(80, 60)
    payload = b"provenance survives a lossless PNG round-trip" * 3
    stego_img = stego.embed(img, payload)

    out = tmp_path / "stego.png"
    stego_img.save(out, format="PNG")
    reopened = Image.open(out)
    assert stego.extract(reopened) == payload


# --------------------------------------------------------------------------- #
# extract on plain images
# --------------------------------------------------------------------------- #


def test_extract_on_plain_image_raises() -> None:
    # A large solid white image: LSBs are all 1, so the declared length header
    # (0xFFFFFFFF) wildly exceeds capacity -> DemoCreateError.
    img = _solid(64, 64, color=(255, 255, 255))
    with pytest.raises(DemoCreateError):
        stego.extract(img)


def test_extract_too_small_image_raises() -> None:
    img = _solid(1, 1)  # cannot even hold the 4-byte header
    with pytest.raises(DemoCreateError):
        stego.extract(img)


# --------------------------------------------------------------------------- #
# provenance
# --------------------------------------------------------------------------- #


def test_build_provenance_fields(sample_demo: Demo) -> None:
    rec = stego.build_provenance(
        sample_demo,
        author="Daniel",
        version="0.6",
        extra={"date": "2026-06-04", "license": "MIT"},
    )
    assert rec["tool"] == "democreate"
    assert rec["version"] == "0.6"
    assert rec["title"] == sample_demo.title
    assert rec["author"] == "Daniel"
    assert rec["scenes"] == len(sample_demo.scenes)
    assert rec["chunks"] == len(sample_demo.iter_chunks())
    assert rec["created_hint"] == "2026-06-04"
    assert rec["license"] == "MIT"
    # the digest covers stable content and is deterministic + verifiable
    assert len(rec["content_sha256"]) == 64
    assert rec["content_sha256"] == stego.build_provenance(sample_demo)["content_sha256"]


def test_build_provenance_is_jsonable(sample_demo: Demo) -> None:
    rec = stego.build_provenance(sample_demo)
    # Must serialize without error and round-trip equal.
    assert json.loads(json.dumps(rec)) == rec


def test_build_provenance_no_extra_defaults(sample_demo: Demo) -> None:
    rec = stego.build_provenance(sample_demo)
    assert rec["author"] == ""
    assert rec["version"] == ""
    assert rec["created_hint"] == ""


def test_embed_then_extract_provenance(sample_demo: Demo) -> None:
    img = _solid(128, 128)
    stego_img, record = stego.embed_provenance(
        img, sample_demo, author="Ada", version="1.2"
    )
    out = stego.extract_provenance(stego_img)
    assert out["title"] == record["title"] == sample_demo.title
    assert out["author"] == "Ada"
    assert out["content_sha256"] == record["content_sha256"]


def test_embed_provenance_survives_png(sample_demo: Demo, tmp_path: Path) -> None:
    img = _solid(120, 90)
    stego_img, record = stego.embed_provenance(
        img, sample_demo, author="Grace", extra={"date": "2026-01-01"}
    )
    path = tmp_path / "poster.png"
    stego_img.save(path, format="PNG")
    out = stego.extract_provenance(Image.open(path))
    assert out == record


def test_verify_provenance_true(sample_demo: Demo) -> None:
    img = _solid(96, 96)
    stego_img, _ = stego.embed_provenance(img, sample_demo, author="me")
    assert stego.verify_provenance(stego_img, sample_demo) is True


def test_verify_provenance_false_for_mutated_demo(sample_demo: Demo) -> None:
    img = _solid(96, 96)
    stego_img, _ = stego.embed_provenance(img, sample_demo)
    mutated = Demo.from_json(sample_demo.to_json())
    mutated.title = sample_demo.title + " (edited)"
    assert stego.verify_provenance(stego_img, mutated) is False


def test_verify_provenance_false_on_plain_image(sample_demo: Demo) -> None:
    plain = _solid(96, 96, color=(255, 255, 255))
    assert stego.verify_provenance(plain, sample_demo) is False


def test_extract_provenance_bad_json_raises() -> None:
    img = _solid(64, 64)
    # Embed bytes that are valid to extract but are not JSON.
    stego_img = stego.embed(img, b"\xff\xfe not json at all")
    with pytest.raises(DemoCreateError):
        stego.extract_provenance(stego_img)


def test_extract_provenance_non_object_raises() -> None:
    img = _solid(64, 64)
    stego_img = stego.embed(img, json.dumps([1, 2, 3]).encode("utf-8"))
    with pytest.raises(DemoCreateError):
        stego.extract_provenance(stego_img)
