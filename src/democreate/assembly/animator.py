"""Timed-frame animation: turn one-frame-per-chunk into smooth, dynamic video.

The default compositor emits a single still frame per narration chunk. That is
correct but static. The animator re-samples the demo onto a fixed animation frame
rate and, for each instant, composites:

* the **base content frame** for the chunk active at that instant (loaded once and
  cached), which already carries the code/terminal/diagram + caption; over it
* a **speech waveform** of the whole voiceover drawn into the reserved bottom band,
  with the portion up to the current time lit and a **playhead** sweeping across; and
* a thin **progress bar** under the top chrome.

Because every output frame is one ``1/fps`` slice, the result encodes with the
simple ``image2`` demuxer, and — since the per-chunk durations come from the
*measured* audio — the playhead stays locked to the spoken words.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .._logging import get_logger, log_stage
from ..animation.waveform import compute_envelope, draw_waveform
from ..capture.screen import waveform_band_box
from ..media import AudioClip

__all__ = ["AnimationConfig", "chunk_timing", "active_index_at", "render_animation_frames"]

logger = get_logger(__name__)

_PROGRESS_BG = (40, 46, 58)
_PROGRESS_FG = (56, 139, 253)


@dataclass
class AnimationConfig:
    """Settings for timed-frame animation.

    Attributes:
        fps: Animation frame rate (frames generated per second of audio).
        bars: Number of waveform bars across the full demo.
        played_color: Bar color for the already-spoken portion.
        bar_color: Bar color for the not-yet-spoken portion.
        waveform: Draw the speech-waveform band.
        progress_bar: Draw the top progress bar.
        accent_color: Progress-bar / accent color.
        transitions: Crossfade between scenes.
        transition_ms: Crossfade duration in milliseconds.
        ken_burns: Slow zoom on flagged (slide/background) frames.
        ken_burns_zoom: Peak Ken Burns zoom factor.
    """

    fps: int = 15
    bars: int = 180
    played_color: tuple[int, int, int] = (80, 200, 255)
    bar_color: tuple[int, int, int] = (74, 86, 104)
    waveform: bool = True
    progress_bar: bool = True
    accent_color: tuple[int, int, int] = (56, 139, 253)
    transitions: bool = True
    transition_ms: int = 450
    ken_burns: bool = False
    ken_burns_zoom: float = 1.06
    lead_ms: int = 0
    gap_ms: int = 0
    trail_ms: int = 0
    typing: bool = True
    typing_fraction: float = 0.7
    cursor: bool = True

    @classmethod
    def from_video(cls, video, theme=None, audio=None) -> AnimationConfig:
        """Build animation settings from video (+ optional theme/audio) config."""
        kwargs: dict = {
            "fps": video.animation_fps,
            "waveform": video.waveform,
            "progress_bar": video.progress_bar,
            "transitions": video.transitions,
            "transition_ms": video.transition_ms,
            "ken_burns": video.ken_burns,
            "ken_burns_zoom": video.ken_burns_zoom,
            "typing": getattr(video, "typing", True),
            "typing_fraction": getattr(video, "typing_fraction", 0.7),
            "cursor": getattr(video, "cursor", True),
        }
        if theme is not None:
            kwargs["played_color"] = theme.wave_played
            kwargs["bar_color"] = theme.wave_bar
            kwargs["accent_color"] = theme.accent
        if audio is not None:
            kwargs["lead_ms"] = audio.lead_silence_ms
            kwargs["gap_ms"] = audio.gap_ms
            kwargs["trail_ms"] = audio.trail_silence_ms
        return cls(**kwargs)


def chunk_timing(
    clips: list[AudioClip],
    *,
    lead_ms: int = 0,
    gap_ms: int = 0,
    trail_ms: int = 0,
) -> tuple[list[tuple[int, int]], int]:
    """Return per-chunk spoken ``(start_ms, end_ms)`` windows and the total duration.

    Windows are laid out in clip order from each clip's measured duration. Optional
    ``lead_ms`` (before the first clip), ``gap_ms`` (between clips), and ``trail_ms``
    (after the last clip) reserve silent time so the frame timeline matches a
    voiceover assembled with the same pauses — keeping audio and video in lock-step.

    Args:
        clips: Narration clips in chunk order.
        lead_ms: Silent lead before the first clip.
        gap_ms: Silent gap inserted between consecutive clips.
        trail_ms: Silent trail after the last clip.

    Returns:
        ``(windows, total_ms)`` — ``total_ms`` includes lead/gaps/trail.
    """
    windows: list[tuple[int, int]] = []
    cursor = lead_ms
    for i, clip in enumerate(clips):
        if i > 0:
            cursor += gap_ms
        end = cursor + max(1, int(clip.duration_ms))
        windows.append((cursor, end))
        cursor = end
    return windows, cursor + trail_ms


def active_index_at(windows: list[tuple[int, int]], t_ms: int) -> int:
    """Return the index of the chunk active at ``t_ms`` (gap- and end-aware).

    During lead/gap silence the *upcoming* chunk's frame is shown (so the viewer
    sees it slightly before its narration); after the last window the last chunk
    holds.

    Args:
        windows: Per-chunk ``(start_ms, end_ms)`` windows from :func:`chunk_timing`.
        t_ms: Time in milliseconds.

    Returns:
        The 0-based index of the active window.
    """
    if not windows:
        return 0
    for i, (_start, end) in enumerate(windows):
        if t_ms < end:
            return i
    return len(windows) - 1


def _ken_burns(base, t_in_chunk: float, dur_ms: int, zoom: float):
    """Return ``base`` with a slow center zoom proportional to within-chunk time."""
    if dur_ms <= 0:
        return base
    frac = max(0.0, min(1.0, t_in_chunk / dur_ms))
    scale = 1.0 + (zoom - 1.0) * frac
    if scale <= 1.001:
        return base
    w, h = base.size
    cw, ch = int(w / scale), int(h / scale)
    x0, y0 = (w - cw) // 2, (h - ch) // 2
    return base.crop((x0, y0, x0 + cw, y0 + ch)).resize((w, h))


def _draw_cursor(draw, xy: tuple[int, int], scale: float, *, ripple: float = 0.0,
                 accent=(56, 139, 253)) -> None:
    """Draw an arrow cursor at ``xy`` with an optional click ripple (``ripple`` 0..1)."""
    x, y = int(xy[0]), int(xy[1])
    s = max(10, int(28 * scale))
    if ripple > 0:
        r = int(s * (0.6 + 2.4 * ripple))
        fade = int(200 * (1 - ripple))
        draw.ellipse([x - r, y - r, x + r, y + r], outline=(*accent, fade), width=3)
    # arrow cursor: a filled triangle with a tail, white with a dark outline
    pts = [(x, y), (x, y + s), (x + int(s * 0.28), y + int(s * 0.72)),
           (x + int(s * 0.5), y + int(s * 0.72)), (x + int(s * 0.28), y + int(s * 0.5))]
    draw.polygon(pts, fill=(245, 247, 250), outline=(20, 22, 28))


def _draw_overlays(frame, meta, title: str, section: str, t_ms: int,
                   total_ms: int, accent) -> None:
    """Draw the top/bottom metadata bars onto ``frame`` from a MetadataConfig."""
    from ..export.overlay import (
        draw_footer,
        draw_header,
        format_clock,
        from_metadata_config,
    )

    clock = format_clock(t_ms, total_ms) if getattr(meta, "show_clock", True) else ""
    info = from_metadata_config(meta, title=title, section=section, clock=clock)
    if meta.header:
        draw_header(frame, info, accent=accent)
    if meta.footer:
        draw_footer(frame, info, accent=accent)


def render_animation_frames(
    frame_paths: list[Path],
    clips: list[AudioClip],
    voiceover_wav: Path,
    out_dir: Path,
    *,
    size: tuple[int, int],
    config: AnimationConfig | None = None,
    scene_ids: list[str] | None = None,
    kenburns_flags: list[bool] | None = None,
    frame_states: list | None = None,
    typing_flags: list[bool] | None = None,
    theme=None,
    overlay_meta=None,
    demo_title: str = "",
) -> tuple[list[Path], int]:
    """Render uniform-cadence animated frames with motion: typing, cursor, waveform.

    Frame ``i`` corresponds to clip/chunk ``i``, held for the clip's measured
    duration. The animator composites, per output frame: a **typing reveal** that
    types code in character-by-character for flagged chunks (re-rendered from the
    chunk's :class:`~democreate.media.FrameState`); a slow **Ken Burns** zoom on
    flagged slide/background frames; scene **crossfades**; an **animated cursor**
    with a click ripple where a chunk supplies a cursor position; a moving speech
    **waveform**; and a **progress bar**.

    Args:
        frame_paths: Base content frames, one per chunk, in order.
        clips: Narration clips, one per chunk, in order (measured timing).
        voiceover_wav: The concatenated voiceover WAV (drives the waveform).
        out_dir: Directory to write ``anim_%05d.png`` frames into.
        size: ``(width, height)`` of the frames.
        config: Animation settings; defaults to :class:`AnimationConfig`.
        scene_ids: Per-chunk scene id; a change marks a crossfade boundary.
        kenburns_flags: Per-chunk Ken Burns flag.
        frame_states: Per-chunk :class:`~democreate.media.FrameState`; required to
            re-render typing/cursor frames (falls back to the static base without it).
        typing_flags: Per-chunk flag; ``True`` types that chunk's code in.
        theme: Theme used when re-rendering typing frames.

    Returns:
        ``(animated_frame_paths, total_ms)``.

    Raises:
        ValueError: If ``frame_paths`` and ``clips`` differ in length or are empty.
    """
    from PIL import Image, ImageDraw

    cfg = config or AnimationConfig()
    if not frame_paths or not clips:
        raise ValueError("render_animation_frames needs frames and clips")
    if len(frame_paths) != len(clips):
        raise ValueError(
            f"frames ({len(frame_paths)}) and clips ({len(clips)}) must match"
        )

    width, height = size
    out_dir.mkdir(parents=True, exist_ok=True)
    windows, total_ms = chunk_timing(
        clips, lead_ms=cfg.lead_ms, gap_ms=cfg.gap_ms, trail_ms=cfg.trail_ms
    )
    total_ms = max(total_ms, 1)
    n = len(clips)
    kb = kenburns_flags or [False] * n
    typing = typing_flags or [False] * n

    envelope = compute_envelope(voiceover_wav, cfg.bars) if voiceover_wav.exists() else []
    band = waveform_band_box(width, height)
    # Progress bar lives at the absolute top edge — the one zone no chrome,
    # content, or background image occupies — so it can never overlap them.
    bar_h = max(3, int(height * 0.006))
    bar_y = 0

    bases = [Image.open(p).convert("RGB") for p in frame_paths]

    # Lazily build a renderer for typing re-renders; cache rendered states.
    renderer = None
    typing_cache: dict[tuple[int, int], object] = {}

    def total_chars(idx: int) -> int:
        if frame_states is None or idx >= len(frame_states):
            return 0
        return sum(len(line) for line in getattr(frame_states[idx], "code_lines", []))

    def typed_base(idx: int, t_ms: int):
        """Re-render chunk ``idx`` with code typed to the current progress."""
        nonlocal renderer
        assert frame_states is not None  # total_chars() returning >0 guarantees frame_states.
        start, end = windows[idx]
        total = total_chars(idx)
        if total == 0:
            return bases[idx]
        win = max(1, end - start)
        frac = max(0.0, (t_ms - start) / win) / max(0.01, cfg.typing_fraction)
        typed = int(total * min(1.0, frac))
        key = (idx, typed)
        cached = typing_cache.get(key)
        if cached is None:
            if renderer is None:
                from ..capture.screen import SyntheticRenderer

                renderer = SyntheticRenderer(theme)
            import copy as _copy

            state = _copy.copy(frame_states[idx])
            state.cursor_typed = typed
            cached = renderer.render(state, size)
            typing_cache[key] = cached
        return cached

    def composed_base(idx: int, t_ms: int):
        """Base frame for chunk ``idx`` at ``t_ms`` with typing/Ken Burns/crossfade."""
        start, end = windows[idx]
        if cfg.typing and idx < len(typing) and typing[idx] and frame_states is not None:
            return typed_base(idx, t_ms).copy()
        cur = bases[idx]
        if cfg.ken_burns and idx < len(kb) and kb[idx]:
            cur = _ken_burns(cur, t_ms - start, end - start, cfg.ken_burns_zoom)
        if (
            cfg.transitions and scene_ids is not None and idx > 0
            and scene_ids[idx] != scene_ids[idx - 1]
            and t_ms - start < cfg.transition_ms
        ):
            alpha = (t_ms - start) / max(1, cfg.transition_ms)
            cur = Image.blend(bases[idx - 1], cur, alpha)
        return cur.copy()

    def cursor_xy_for(idx: int):
        if frame_states is None or idx >= len(frame_states):
            return None
        return getattr(frame_states[idx], "cursor_xy", None)

    total_frames = max(1, int(round(total_ms / 1000 * cfg.fps)))
    written: list[Path] = []
    with log_stage(f"render {total_frames} animated frames @ {cfg.fps}fps", logger):
        for k in range(total_frames):
            t_ms = int(k / cfg.fps * 1000)
            idx = active_index_at(windows, t_ms)
            progress = min(1.0, t_ms / total_ms)

            frame = composed_base(idx, t_ms)
            draw = ImageDraw.Draw(frame)
            if cfg.progress_bar:
                draw.rectangle([0, bar_y, width, bar_y + bar_h], fill=_PROGRESS_BG)
                draw.rectangle([0, bar_y, int(width * progress), bar_y + bar_h],
                               fill=cfg.accent_color)
            if cfg.waveform and envelope:
                draw_waveform(
                    draw, band, envelope, progress=progress,
                    bar_color=cfg.bar_color, played_color=cfg.played_color,
                )
            if cfg.cursor:
                xy = cursor_xy_for(idx)
                if xy is not None:
                    start, end = windows[idx]
                    rip = max(0.0, 1.0 - (t_ms - start) / 600) if t_ms - start < 600 else 0.0
                    _draw_cursor(draw, xy, height / 1080, ripple=rip,
                                 accent=cfg.accent_color)
            if overlay_meta is not None and (overlay_meta.header or overlay_meta.footer):
                _draw_overlays(frame, overlay_meta, demo_title,
                               getattr(frame_states[idx], "section", "")
                               if frame_states else "",
                               t_ms, total_ms, cfg.accent_color)
            out = out_dir / f"anim_{k:05d}.png"
            frame.save(out, format="PNG")
            written.append(out)

    logger.info("animated %d frame(s) over %d ms", len(written), total_ms)
    return written, total_ms
