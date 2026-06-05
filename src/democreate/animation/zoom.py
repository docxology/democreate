"""Cursor-following zoom and pan math.

A "zoom" effect tracks the mouse: when the cursor moves, the virtual camera eases
in toward it, holds, and eases back out. This module is pure math plus a small
Pillow applicator:

* easing curves — :func:`linear`, :func:`ease_in_out_quad`,
  :func:`ease_in_out_cubic` (all map ``t`` in ``[0, 1]`` to ``[0, 1]``).
* :class:`ZoomKeyframe` — a camera state at a point in time.
* :func:`compute_zoom_path` — turn a list of timestamped cursor points into a
  keyframe track that zooms toward each point and relaxes back out.
* :func:`interpolate` — sample camera state at an arbitrary time, clamping
  outside the track's range.
* :func:`apply_zoom` — crop a region around the keyframe center sized by
  ``1/scale`` and resize it back to the original frame size (a Pillow op).

Everything is deterministic. There is no randomness and no I/O.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .._logging import get_logger

__all__ = [
    "linear",
    "ease_in_out_quad",
    "ease_in_out_cubic",
    "ZoomKeyframe",
    "compute_zoom_path",
    "interpolate",
    "apply_zoom",
]

logger = get_logger(__name__)


def _clamp01(t: float) -> float:
    """Clamp ``t`` into the closed unit interval ``[0, 1]``."""
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return t


def linear(t: float) -> float:
    """Identity easing.

    Args:
        t: Normalized time in ``[0, 1]`` (clamped).

    Returns:
        ``t`` unchanged (after clamping).
    """
    return _clamp01(t)


def ease_in_out_quad(t: float) -> float:
    """Quadratic ease-in-out.

    Args:
        t: Normalized time in ``[0, 1]`` (clamped).

    Returns:
        The eased value in ``[0, 1]``.
    """
    t = _clamp01(t)
    if t < 0.5:
        return 2.0 * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 2) / 2.0


def ease_in_out_cubic(t: float) -> float:
    """Cubic ease-in-out.

    Args:
        t: Normalized time in ``[0, 1]`` (clamped).

    Returns:
        The eased value in ``[0, 1]``.
    """
    t = _clamp01(t)
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - ((-2.0 * t + 2.0) ** 3) / 2.0


@dataclass
class ZoomKeyframe:
    """A virtual-camera state at one instant.

    Attributes:
        t_ms: Time of this keyframe in milliseconds from the track start.
        center_x: Camera focus x in pixels.
        center_y: Camera focus y in pixels.
        scale: Zoom factor (``1.0`` == no zoom; ``> 1`` zooms in).
    """

    t_ms: int
    center_x: float
    center_y: float
    scale: float


def compute_zoom_path(
    cursor_points: list[tuple[int, int, int]],
    frame_size: tuple[int, int],
    *,
    zoom: float = 1.6,
    hold_ms: int = 400,
) -> list[ZoomKeyframe]:
    """Build a zoom keyframe track that follows the cursor.

    For each cursor point ``(t_ms, x, y)`` the camera eases in to ``zoom`` centered
    on the cursor and holds for ``hold_ms``, producing two keyframes per point: a
    "zoomed-in, centered on cursor" frame at the cursor time and a "held" frame
    ``hold_ms`` later. The track is bookended by fully-zoomed-out keyframes
    (``scale == 1`` centered on the frame) so it eases out at both ends.

    Args:
        cursor_points: Cursor samples as ``(t_ms, x, y)`` tuples. Need not be
            sorted; the result is sorted by time. Duplicate timestamps are
            de-duplicated keeping the last sample.
        frame_size: ``(width, height)`` of the frame in pixels.
        zoom: Target zoom factor while tracking the cursor (must be ``>= 1``).
        hold_ms: How long to hold the zoom after reaching a cursor point.

    Returns:
        A time-sorted list of :class:`ZoomKeyframe` with non-decreasing ``t_ms``
        and every ``scale >= 1``.

    Raises:
        ValueError: If ``zoom < 1`` or ``hold_ms < 0``.
    """
    if zoom < 1.0:
        raise ValueError(f"zoom must be >= 1, got {zoom}")
    if hold_ms < 0:
        raise ValueError(f"hold_ms must be >= 0, got {hold_ms}")

    width, height = frame_size
    cx0, cy0 = width / 2.0, height / 2.0

    if not cursor_points:
        return [ZoomKeyframe(t_ms=0, center_x=cx0, center_y=cy0, scale=1.0)]

    # De-duplicate by timestamp (last write wins), then sort by time.
    by_time: dict[int, tuple[int, int]] = {}
    for t_ms, x, y in cursor_points:
        by_time[t_ms] = (x, y)
    ordered = sorted(by_time.items())

    keyframes: list[ZoomKeyframe] = []
    first_t = ordered[0][0]
    # Lead-in: zoomed out just before the first cursor event.
    keyframes.append(
        ZoomKeyframe(t_ms=first_t, center_x=cx0, center_y=cy0, scale=1.0)
    )
    for t_ms, (x, y) in ordered:
        keyframes.append(
            ZoomKeyframe(t_ms=t_ms, center_x=float(x), center_y=float(y), scale=zoom)
        )
        keyframes.append(
            ZoomKeyframe(
                t_ms=t_ms + hold_ms,
                center_x=float(x),
                center_y=float(y),
                scale=zoom,
            )
        )
    # Tail: ease back out after the last hold.
    last_t = ordered[-1][0] + hold_ms
    keyframes.append(
        ZoomKeyframe(t_ms=last_t + hold_ms, center_x=cx0, center_y=cy0, scale=1.0)
    )

    keyframes.sort(key=lambda k: k.t_ms)
    return keyframes


def interpolate(
    keyframes: list[ZoomKeyframe],
    t_ms: int,
    *,
    easing: Callable[[float], float] = ease_in_out_cubic,
) -> ZoomKeyframe:
    """Sample camera state at time ``t_ms`` by easing between bracketing keyframes.

    Args:
        keyframes: A time-sorted, non-empty keyframe track (as produced by
            :func:`compute_zoom_path`).
        t_ms: The time to sample, in milliseconds.
        easing: Easing curve applied to the normalized segment time.

    Returns:
        A :class:`ZoomKeyframe` at ``t_ms``. Times before the first or after the
        last keyframe clamp to that endpoint's state.

    Raises:
        ValueError: If ``keyframes`` is empty.
    """
    if not keyframes:
        raise ValueError("keyframes must be non-empty")

    track = sorted(keyframes, key=lambda k: k.t_ms)
    if t_ms <= track[0].t_ms:
        first = track[0]
        return ZoomKeyframe(t_ms, first.center_x, first.center_y, first.scale)
    if t_ms >= track[-1].t_ms:
        last = track[-1]
        return ZoomKeyframe(t_ms, last.center_x, last.center_y, last.scale)

    # Find the bracketing pair [lo, hi] with lo.t_ms <= t_ms <= hi.t_ms.
    for lo, hi in zip(track, track[1:], strict=False):
        if lo.t_ms <= t_ms <= hi.t_ms:
            span = hi.t_ms - lo.t_ms
            raw = 0.0 if span == 0 else (t_ms - lo.t_ms) / span
            e = easing(raw)
            return ZoomKeyframe(
                t_ms=t_ms,
                center_x=lo.center_x + (hi.center_x - lo.center_x) * e,
                center_y=lo.center_y + (hi.center_y - lo.center_y) * e,
                scale=lo.scale + (hi.scale - lo.scale) * e,
            )

    # Unreachable given the clamps above, but keep the type checker happy.
    last = track[-1]  # pragma: no cover
    return ZoomKeyframe(t_ms, last.center_x, last.center_y, last.scale)  # pragma: no cover


def apply_zoom(image, kf: ZoomKeyframe):
    """Crop around the keyframe center and resize back to the original size.

    The cropped region is ``1/scale`` of the frame in each dimension, centered on
    ``(kf.center_x, kf.center_y)`` and clamped to stay inside the image, then
    resized back to the original dimensions. A ``scale <= 1`` returns a copy at
    the same size (identity zoom).

    Args:
        image: A :class:`PIL.Image.Image` to zoom into.
        kf: The keyframe describing center and scale.

    Returns:
        A new :class:`PIL.Image.Image` of the same size as ``image``.
    """
    width, height = image.size
    scale = max(1.0, kf.scale)
    if scale <= 1.0:
        return image.copy()

    crop_w = max(1, int(round(width / scale)))
    crop_h = max(1, int(round(height / scale)))

    left = int(round(kf.center_x - crop_w / 2.0))
    top = int(round(kf.center_y - crop_h / 2.0))
    # Clamp the crop box fully inside the frame.
    left = max(0, min(left, width - crop_w))
    top = max(0, min(top, height - crop_h))

    box = (left, top, left + crop_w, top + crop_h)
    cropped = image.crop(box)
    from PIL import Image

    return cropped.resize((width, height), Image.Resampling.LANCZOS)
