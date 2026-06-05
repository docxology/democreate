"""Tests for composition: gap-aware timing, transitions, Ken Burns, scene meta."""

from __future__ import annotations

import struct
import wave
from pathlib import Path

from PIL import Image, ImageStat

from democreate.assembly.animator import (
    AnimationConfig,
    _ken_burns,
    active_index_at,
    chunk_timing,
    render_animation_frames,
)
from democreate.config import RenderConfig
from democreate.media import AudioClip
from democreate.pipeline import _scene_meta
from democreate.schema import Action, ActionType, Chunk, Demo, Scene, SceneKind


def test_chunk_timing_with_lead_gap_trail() -> None:
    clips = [AudioClip(path=Path("a"), duration_ms=1000),
             AudioClip(path=Path("b"), duration_ms=1000)]
    windows, total = chunk_timing(clips, lead_ms=300, gap_ms=200, trail_ms=500)
    assert windows == [(300, 1300), (1500, 2500)]
    assert total == 3000  # 300 lead + 1000 + 200 gap + 1000 + 500 trail


def test_active_index_holds_through_gaps() -> None:
    windows = [(300, 1300), (1500, 2500)]
    assert active_index_at(windows, 0) == 0      # lead → first
    assert active_index_at(windows, 1400) == 1   # gap → upcoming chunk
    assert active_index_at(windows, 2000) == 1
    assert active_index_at(windows, 99999) == 1  # trail → last


def test_ken_burns_zooms_over_time() -> None:
    base = Image.new("RGB", (200, 100), (10, 20, 30))
    base.putpixel((100, 50), (255, 255, 255))
    start = _ken_burns(base, 0, 1000, 1.1)
    end = _ken_burns(base, 1000, 1000, 1.1)
    assert start.size == (200, 100) and end.size == (200, 100)
    # at t=0 the zoom is ~identity; at t=dur it is magnified (pixels differ)
    assert start.tobytes() != end.tobytes()


def test_animation_config_from_video_carries_audio_and_theme() -> None:
    cfg = RenderConfig.preset("paper")
    ac = AnimationConfig.from_video(cfg.video, cfg.theme, cfg.audio)
    assert ac.lead_ms == cfg.audio.lead_silence_ms
    assert ac.gap_ms == cfg.audio.gap_ms
    assert ac.played_color == cfg.theme.wave_played
    assert ac.accent_color == cfg.theme.accent


def test_scene_meta_flags_slides_and_backgrounds() -> None:
    s1 = Scene(id="code", kind=SceneKind.CODEBASE)
    s1.chunks.append(Chunk(id="c1", text="x"))
    s2 = Scene(id="slide", kind=SceneKind.SLIDE)
    s2.chunks.append(Chunk(id="c2", text="y"))
    s3 = Scene(id="bg", kind=SceneKind.CODEBASE, context={"background_image": "/x.png"})
    s3.chunks.append(Chunk(id="c3", text="z"))
    demo = Demo(title="T", scenes=[s1, s2, s3])
    scene_ids, kb = _scene_meta(demo)
    assert scene_ids == ["code", "slide", "bg"]
    assert kb == [False, True, True]  # slide + background get Ken Burns, code does not


def _mkwav(path: Path, ms: int) -> None:
    n = int(22050 * ms / 1000)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(22050)
        w.writeframes(b"".join(struct.pack("<h", 9000 if i % 2 else -9000) for i in range(n)))


def test_render_with_transitions_and_kenburns(tmp_path: Path) -> None:
    base_dir = tmp_path / "f"
    base_dir.mkdir()
    frames = []
    for i in range(2):
        p = base_dir / f"frame_{i:04d}.png"
        Image.new("RGB", (320, 180), (20 + i * 60, 30, 40)).save(p)
        frames.append(p)
    clips = [AudioClip(path=tmp_path / "a.wav", duration_ms=1000, chunk_id="c0"),
             AudioClip(path=tmp_path / "b.wav", duration_ms=1000, chunk_id="c1")]
    voice = tmp_path / "v.wav"
    _mkwav(voice, 2000)
    cfg = AnimationConfig(fps=10, bars=40, transitions=True, transition_ms=300,
                          ken_burns=True, lead_ms=100, trail_ms=100)
    written, total = render_animation_frames(
        frames, clips, voice, tmp_path / "anim", size=(320, 180), config=cfg,
        scene_ids=["s0", "s1"], kenburns_flags=[True, True],
    )
    assert total == 2200  # 100 lead + 1000 + 1000 + 100 trail (gap_ms=0)
    assert len(written) == 22
    mid = Image.open(written[11])
    assert mid.size == (320, 180)
    assert ImageStat.Stat(mid.convert("L")).var[0] > 0


def test_default_config_no_gaps_keeps_sync() -> None:
    # with lead/gap/trail all zero, total equals the sum of durations
    clips = [AudioClip(path=Path("a"), duration_ms=500),
             AudioClip(path=Path("b"), duration_ms=700)]
    _windows, total = chunk_timing(clips)
    assert total == 1200


def test_paper_action_type_used() -> None:
    # guard: paper scenes use OPEN_FILE actions which the compositor understands
    scene = Scene(id="s", kind=SceneKind.SLIDE)
    scene.chunks.append(Chunk(id="c", text="hi", actions=[
        Action(ActionType.OPEN_FILE, {"path": "x"})]))
    assert Demo(title="T", scenes=[scene]).is_valid()
