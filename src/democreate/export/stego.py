"""LSB steganography and signed provenance payloads for lossless frames.

This module hides a provenance record inside the least-significant bits of an
image's R, G, and B channels. The technique embeds one bit per channel per
pixel, prefixed by a 4-byte big-endian length header, so a decoder can recover
exactly the bytes that were written.

Honesty note — survivability
-----------------------------
LSB pixel steganography survives **only** in a lossless container such as PNG.
Any lossy step — most importantly an H.264 (or any other lossy codec) video
re-encode — re-quantizes the pixels and destroys the hidden bits completely.
This is therefore used on the *poster* and on the "transmission bookend" frames
that DemoCreate exports as PNG, **not** on the video pixels themselves. Do not
expect a provenance payload to round-trip through a rendered ``.mp4``.

The provenance record (see :func:`build_provenance`) carries a SHA-256 of the
demo's *stable authored content* (via :func:`_content_digest`, excluding
render-state fields). Because that hash is embedded in the image, the pairing
is tamper-evident: mutating either the demo or the image breaks
:func:`verify_provenance`. The payload is plain JSON — this is provenance, not
encryption; anyone with this module can read it.
"""

from __future__ import annotations

import hashlib
import json
import struct
from typing import TYPE_CHECKING, Any, cast

from .._logging import get_logger
from ..errors import DemoCreateError

if TYPE_CHECKING:
    from PIL import Image

    from ..schema import Demo

__all__ = [
    "capacity_bytes",
    "embed",
    "extract",
    "build_provenance",
    "embed_provenance",
    "extract_provenance",
    "verify_provenance",
]

_log = get_logger(__name__)

# A 4-byte big-endian unsigned length header precedes the payload bytes.
_HEADER_BYTES = 4
_HEADER_FORMAT = ">I"
# Bits carried per pixel: one LSB in each of the R, G, B channels.
_BITS_PER_PIXEL = 3


def capacity_bytes(size: tuple[int, int]) -> int:
    """Return the maximum payload size, in bytes, for an image of ``size``.

    Each pixel carries three usable bits (one per RGB channel), so the raw
    capacity is ``width * height * 3 // 8`` bytes. The 4-byte length header is
    subtracted because it consumes capacity too.

    Args:
        size: The ``(width, height)`` of the target image in pixels.

    Returns:
        The largest payload, in bytes, that :func:`embed` will accept for an
        image of this size. May be ``0`` (or treated as such) for tiny images.
    """
    width, height = size
    total_bits = width * height * _BITS_PER_PIXEL
    total_bytes = total_bits // 8
    return total_bytes - _HEADER_BYTES


def _iter_bits(data: bytes):
    """Yield the bits of ``data`` most-significant-bit first, as 0/1 ints."""
    for byte in data:
        for shift in range(7, -1, -1):
            yield (byte >> shift) & 1


def embed(image: Image.Image, payload: bytes) -> Image.Image:
    """Return a copy of ``image`` with ``payload`` hidden in its RGB LSBs.

    The image is converted to ``RGB`` and copied; the original is never
    mutated. A 4-byte big-endian length header is written first, followed by the
    payload bytes, into the least-significant bit of the R, G, B channels in
    row-major (left-to-right, top-to-bottom) order. The operation is fully
    deterministic.

    Args:
        image: The cover image. Converted to ``RGB`` internally.
        payload: The raw bytes to hide.

    Returns:
        A new ``RGB`` :class:`PIL.Image.Image` carrying the payload.

    Raises:
        ValueError: If ``payload`` is too large to fit in an image of this size.
    """
    rgb = image.convert("RGB")
    width, height = rgb.size
    capacity = capacity_bytes((width, height))
    if len(payload) > capacity:
        raise ValueError(
            f"payload of {len(payload)} bytes exceeds capacity {capacity} "
            f"for a {width}x{height} image"
        )

    header = struct.pack(_HEADER_FORMAT, len(payload))
    message = header + payload

    out = rgb.copy()
    pixels = out.load()
    assert pixels is not None  # RGB copies always expose addressable pixel access.
    bits = _iter_bits(message)

    done = False
    for y in range(height):
        if done:
            break
        for x in range(width):
            r, g, b = cast(tuple[int, int, int], pixels[x, y])
            channels = [r, g, b]
            for i in range(_BITS_PER_PIXEL):
                bit = next(bits, None)
                if bit is None:
                    done = True
                    break
                channels[i] = (channels[i] & ~1) | bit
            pixels[x, y] = (channels[0], channels[1], channels[2])
            if done:
                break
    return out


def _read_bytes(pixels, size: tuple[int, int], count: int) -> bytes:
    """Read ``count`` bytes from the RGB LSBs of ``pixels`` in row-major order."""
    width, height = size
    out = bytearray()
    current = 0
    filled = 0
    needed_bits = count * 8

    collected = 0
    for y in range(height):
        if collected >= needed_bits:
            break
        for x in range(width):
            r, g, b = pixels[x, y]
            for channel in (r, g, b):
                current = (current << 1) | (channel & 1)
                filled += 1
                collected += 1
                if filled == 8:
                    out.append(current)
                    current = 0
                    filled = 0
                if collected >= needed_bits:
                    break
            if collected >= needed_bits:
                break
    return bytes(out)


def extract(image: Image.Image) -> bytes:
    """Recover the payload hidden in ``image`` by :func:`embed`.

    Reads the 4-byte big-endian length header from the RGB LSBs, then reads that
    many payload bytes. The image is converted to ``RGB`` (read-only).

    Args:
        image: The stego image to read.

    Returns:
        The recovered payload bytes (possibly empty).

    Raises:
        DemoCreateError: If the declared length exceeds the image's capacity,
            which indicates a corrupt header or an image with no payload.
    """
    rgb = image.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    assert pixels is not None  # RGB images always expose addressable pixel access.

    header = _read_bytes(pixels, (width, height), _HEADER_BYTES)
    if len(header) < _HEADER_BYTES:
        raise DemoCreateError("image too small to contain a payload header")
    (length,) = struct.unpack(_HEADER_FORMAT, header)

    capacity = capacity_bytes((width, height))
    if length > capacity or length < 0:
        raise DemoCreateError(
            f"declared payload length {length} exceeds capacity {capacity}; "
            f"image is corrupt or carries no payload"
        )

    total = _read_bytes(pixels, (width, height), _HEADER_BYTES + length)
    return total[_HEADER_BYTES:]


def _content_digest(demo) -> str:
    """Return a sha256 over the demo's *stable content*, ignoring render state.

    Render mutates the demo (audio paths, synced timestamps), so hashing the full
    serialization would make a freshly-authored demo fail to verify against the
    one embedded at render time. This digest covers only the authored content —
    title, geometry, and the scene/chunk/action structure with narration text and
    action params, excluding ``audio_path``/``start_ms``/``timestamp_ms``/
    ``duration_ms`` — so verification is stable.
    """
    import json as _json

    scenes = []
    for scene in demo.scenes:
        chunks = []
        for chunk in scene.chunks:
            actions = [
                {
                    "type": getattr(a.type, "value", str(a.type)),
                    "params": a.params,
                    "trigger_word": a.trigger_word,
                }
                for a in chunk.actions
            ]
            chunks.append({"id": chunk.id, "text": chunk.text, "actions": actions})
        scenes.append(
            {
                "id": scene.id,
                "title": scene.title,
                "kind": getattr(scene.kind, "value", str(scene.kind)),
                "chunks": chunks,
            }
        )
    payload = {
        "title": demo.title,
        "width": demo.width,
        "height": demo.height,
        "scenes": scenes,
    }
    blob = _json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_provenance(
    demo: Demo,
    *,
    author: str = "",
    version: str = "",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-able provenance record for ``demo``.

    The record pins the demo to a SHA-256 of its *stable authored content* via
    :func:`_content_digest` (title, geometry, and the scene/chunk/action structure
    with narration text and action params) — deliberately EXCLUDING render-state
    fields (``audio_path``, ``start_ms``, ``timestamp_ms``, ``duration_ms``) so the
    seal verifies before and after a render. Any later pairing is tamper-evident.
    No clock is read — any timestamp must be supplied via ``extra`` (e.g. ``date``), which
    keeps the function pure and deterministic.

    Args:
        demo: The demo to describe.
        author: Optional author/attribution string.
        version: Optional tool/content version string.
        extra: Additional JSON-able fields merged into the record. A ``date``
            key, if present, also populates ``created_hint``.

    Returns:
        A flat dict with at least ``tool``, ``version``, ``title``, ``author``,
        ``scenes``, ``chunks``, ``content_sha256``, and ``created_hint`` keys,
        plus any extra fields supplied.
    """
    extra = dict(extra or {})
    content_sha256 = _content_digest(demo)

    record: dict[str, Any] = {
        "tool": "democreate",
        "version": version,
        "title": demo.title,
        "author": author,
        "scenes": len(demo.scenes),
        "chunks": len(demo.iter_chunks()),
        "content_sha256": content_sha256,
        "created_hint": extra.get("date", ""),
    }
    record.update(extra)
    return record


def embed_provenance(
    image: Image.Image,
    demo: Demo,
    *,
    author: str = "",
    version: str = "",
    extra: dict[str, Any] | None = None,
) -> tuple[Image.Image, dict[str, Any]]:
    """Build a provenance record and embed it into ``image``.

    Args:
        image: The cover image (poster or bookend frame, exported as PNG).
        demo: The demo to describe and pin.
        author: Optional author/attribution string.
        version: Optional tool/content version string.
        extra: Additional JSON-able provenance fields (see
            :func:`build_provenance`).

    Returns:
        A ``(stego_image, provenance_dict)`` tuple. The image is a new ``RGB``
        copy carrying the JSON-encoded record; the dict is the record itself.

    Raises:
        ValueError: If the encoded record is too large for the image.
    """
    record = build_provenance(demo, author=author, version=version, extra=extra)
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True).encode("utf-8")
    stego = embed(image, payload)
    return stego, record


def extract_provenance(image: Image.Image) -> dict[str, Any]:
    """Extract and JSON-decode the provenance record from ``image``.

    Args:
        image: A stego image produced by :func:`embed_provenance`.

    Returns:
        The decoded provenance dict.

    Raises:
        DemoCreateError: If no valid payload is present or the bytes are not
            valid UTF-8 JSON describing an object.
    """
    payload = extract(image)
    try:
        record = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DemoCreateError(
            "embedded payload is not valid UTF-8 JSON provenance"
        ) from exc
    if not isinstance(record, dict):
        raise DemoCreateError(
            f"embedded provenance is not a JSON object (got {type(record).__name__})"
        )
    return record


def verify_provenance(image: Image.Image, demo: Demo) -> bool:
    """Return ``True`` iff ``image``'s hidden record matches ``demo``.

    The check recomputes :func:`_content_digest` (the stable-content SHA-256, not
    ``demo.to_json()``) and compares it against the ``content_sha256`` stored in
    the image — so it holds across a render. A mismatch (mutated demo, swapped
    image) yields ``False``; a missing or corrupt payload also yields ``False``.

    Args:
        image: The stego image to verify.
        demo: The demo the image is claimed to describe.

    Returns:
        ``True`` if the embedded content hash matches this demo, else ``False``.
    """
    try:
        record = extract_provenance(image)
    except DemoCreateError:
        return False
    expected = _content_digest(demo)
    return record.get("content_sha256") == expected
