"""Speech-waveform visualization for demo frames.

A tiny, pure, deterministic toolkit for turning a narration WAV file into a
legible "audio scrubber" — the mirrored-bar waveform strips you see under a
video timeline, with a played/unplayed split and a playhead marker.

Three functions cover the pipeline:

* :func:`compute_envelope` — read a 16-bit PCM mono/stereo WAV with the stdlib
  ``wave`` module and reduce it to a fixed number of normalized RMS amplitude
  buckets (peak bucket = 1.0). This is the only function that touches the disk.
* :func:`draw_waveform` — paint mirrored vertical bars (played vs. unplayed) plus
  a playhead onto an existing :class:`PIL.ImageDraw.ImageDraw`.
* :func:`render_waveform_strip` — convenience wrapper that allocates an image,
  draws the full-area waveform, and hands the image back.

No randomness, no network, no heavy dependencies: only the stdlib (``wave``,
``array``, ``math``) plus Pillow, which is a core dependency.
"""

from __future__ import annotations

import array
import math
import sys
import wave
from pathlib import Path

from PIL import Image, ImageDraw

from .._logging import get_logger

__all__ = ["compute_envelope", "draw_waveform", "render_waveform_strip"]

logger = get_logger(__name__)


def compute_envelope(wav_path: Path, bars: int) -> list[float]:
    """Reduce a 16-bit PCM WAV file to ``bars`` normalized RMS amplitudes.

    The file is read with the stdlib :mod:`wave` module and unpacked as signed
    16-bit samples via :mod:`array`. Stereo (or multi-channel) audio is collapsed
    to mono by averaging channels per frame. Samples are split into ``bars``
    contiguous buckets; the root-mean-square amplitude of each bucket is computed
    and the whole envelope is normalized so the loudest bucket equals ``1.0``.

    Args:
        wav_path: Path to a 16-bit PCM WAV file.
        bars: Number of output buckets (must be positive).

    Returns:
        A list of ``bars`` floats in ``[0.0, 1.0]``. All zeros for silent or
        empty audio; shorter-than-``bars`` audio is padded with trailing zeros.

    Raises:
        ValueError: If ``bars`` is not a positive integer.
    """
    if bars <= 0:
        raise ValueError(f"bars must be a positive integer, got {bars!r}")

    with wave.open(str(wav_path), "rb") as wav:
        n_channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        n_frames = wav.getnframes()
        raw = wav.readframes(n_frames)

    if sample_width != 2:
        raise ValueError(
            f"expected 16-bit PCM (sample width 2), got width {sample_width}"
        )

    samples = array.array("h")
    samples.frombytes(raw)
    # array("h") is native-endian; WAV is little-endian. Byteswap on big-endian.
    if sys.byteorder == "big":  # pragma: no cover - depends on host
        samples.byteswap()

    # Collapse to mono by averaging channels for each frame.
    if n_channels > 1 and len(samples) >= n_channels:
        mono: list[float] = []
        for i in range(0, len(samples) - n_channels + 1, n_channels):
            frame = samples[i : i + n_channels]
            mono.append(sum(frame) / n_channels)
    else:
        mono = [float(s) for s in samples]

    envelope = [0.0] * bars
    total = len(mono)
    if total == 0:
        return envelope

    # Contiguous buckets. If there are fewer samples than bars, the trailing
    # buckets simply receive no samples and stay at 0.0 (graceful padding).
    bucket_size = total / bars
    for b in range(bars):
        start = int(math.floor(b * bucket_size))
        end = int(math.floor((b + 1) * bucket_size))
        if b == bars - 1:
            end = total
        if end <= start:
            continue
        acc = 0.0
        for i in range(start, end):
            value = mono[i]
            acc += value * value
        envelope[b] = math.sqrt(acc / (end - start))

    peak = max(envelope)
    if peak <= 0.0:
        return [0.0] * bars
    return [value / peak for value in envelope]


def draw_waveform(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    envelope: list[float],
    *,
    progress: float = 1.0,
    bar_color: tuple[int, int, int] = (90, 110, 130),
    played_color: tuple[int, int, int] = (80, 200, 255),
    playhead_color: tuple[int, int, int] = (240, 245, 255),
    gap: int = 2,
) -> None:
    """Draw a mirrored-bar waveform with a played/unplayed split and a playhead.

    Bars are centered vertically within ``box`` and mirror around that midline,
    so each amplitude paints both upward and downward. Bars whose center falls
    left of the ``progress`` x-position use ``played_color``; the rest use
    ``bar_color``. A 2-3px vertical playhead line is drawn at the progress x.
    Bar heights are clamped so they never exceed the box. An empty ``envelope``
    is a no-op.

    Args:
        draw: The :class:`PIL.ImageDraw.ImageDraw` to paint on.
        box: ``(x0, y0, x1, y1)`` pixel bounds of the waveform area.
        envelope: Normalized amplitudes (typically in ``[0, 1]``).
        progress: Playback position as a fraction ``0..1`` across the box width.
        bar_color: RGB color for unplayed bars.
        played_color: RGB color for played bars.
        playhead_color: RGB color for the vertical playhead line.
        gap: Horizontal gap in pixels between adjacent bars.

    Returns:
        ``None``. The image backing ``draw`` is mutated in place.
    """
    if not envelope:
        return

    x0, y0, x1, y1 = box
    width = x1 - x0
    height = y1 - y0
    if width <= 0 or height <= 0:
        return

    progress = min(1.0, max(0.0, progress))
    gap = max(0, int(gap))
    n = len(envelope)

    # Slot width per bar (including its gap); ensure at least 1px of bar.
    slot = width / n
    bar_w = max(1.0, slot - gap)
    mid_y = (y0 + y1) / 2.0
    half_max = height / 2.0
    progress_x = x0 + progress * width

    for i, amp in enumerate(envelope):
        amp = min(1.0, max(0.0, float(amp)))
        bx0 = x0 + i * slot
        bx1 = bx0 + bar_w
        if bx1 > x1:
            bx1 = float(x1)
        if bx1 <= bx0:
            continue

        half_h = amp * half_max
        if half_h <= 0.0:
            # Still draw a 1px seed line so silent regions read as a baseline.
            half_h = 0.5

        top = mid_y - half_h
        bottom = mid_y + half_h
        # Clamp to the box just in case of rounding at the extremes.
        top = max(float(y0), top)
        bottom = min(float(y1), bottom)

        center_x = (bx0 + bx1) / 2.0
        color = played_color if center_x <= progress_x else bar_color
        draw.rectangle(
            [(bx0, top), (bx1, bottom)],
            fill=color,
        )

    # Playhead: a crisp 2-3px vertical line at the progress position.
    head_w = 2
    head_x0 = progress_x - head_w / 2.0
    head_x1 = progress_x + head_w / 2.0
    # Keep the playhead fully inside the box.
    head_x0 = max(float(x0), head_x0)
    head_x1 = min(float(x1), head_x1)
    if head_x1 > head_x0:
        draw.rectangle(
            [(head_x0, float(y0)), (head_x1, float(y1))],
            fill=playhead_color,
        )


def render_waveform_strip(
    envelope: list[float],
    size: tuple[int, int],
    *,
    progress: float = 1.0,
    bg: tuple[int, int, int] = (15, 18, 26),
) -> Image.Image:
    """Render a full-frame waveform strip image.

    Allocates a new RGB image filled with ``bg`` and draws the waveform over its
    entire area via :func:`draw_waveform`.

    Args:
        envelope: Normalized amplitudes (typically in ``[0, 1]``).
        size: ``(width, height)`` of the output image in pixels.
        progress: Playback position as a fraction ``0..1`` across the width.
        bg: RGB background color.

    Returns:
        A :class:`PIL.Image.Image` of exactly ``size``.
    """
    width, height = size
    width = max(1, int(width))
    height = max(1, int(height))
    image = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(image)
    draw_waveform(draw, (0, 0, width, height), envelope, progress=progress)
    return image
