"""Deterministic scheduled playback and bounded image-retention regressions."""

from __future__ import annotations

import json
import weakref
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from democreate.assembly.animator import (
    AnimationConfig,
    _BaseFrames,
    _draw_cursor,
    _StateFrames,
    chunk_timing,
    frame_hold_durations,
    render_animation_frames,
)
from democreate.assembly.audio import write_silence
from democreate.assembly.compositor import build_timeline
from democreate.capture.screen import SyntheticRenderer
from democreate.media import AudioClip, FrameState
from democreate.schema import Action, ActionType, Chunk, Demo, Scene


def _config(**kwargs) -> AnimationConfig:
    return AnimationConfig(
        fps=10, waveform=False, progress_bar=False, cursor=False,
        transitions=False, **kwargs,
    )


@pytest.mark.parametrize("typing", [True, False])
def test_rendered_action_is_absent_before_trigger_and_reveals_over_duration(
    tmp_path: Path, typing: bool,
) -> None:
    demo = Demo(title="Timed", scenes=[Scene(id="s", chunks=[Chunk(
        id="c", text="watch the code", duration_ms=1000,
        actions=[Action(
            ActionType.CREATE_FILE, {"path": "a.py", "code": "abcdefgh"},
            timestamp_ms=500, duration_ms=200,
        )],
    )])])
    entry = build_timeline(demo).entries[0]
    stored = json.dumps(entry.to_dict())
    authored = json.dumps(demo.to_dict())
    size = (640, 360)
    renderer = SyntheticRenderer()
    still = tmp_path / "still.png"
    renderer.render(entry.state, size).save(still)
    voice = write_silence(tmp_path / "voice.wav", 1000)
    written, _ = render_animation_frames(
        [still], [AudioClip(path=voice, duration_ms=1000)], voice, tmp_path / "anim",
        size=size, config=_config(typing=typing), timeline_entries=[entry],
    )
    before = FrameState(caption="watch the code")
    at_trigger = FrameState(
        caption="watch the code", title="a.py", file_path="a.py",
        code_lines=[] if typing else ["abcdefgh"],
    )
    halfway = FrameState(
        caption="watch the code", title="a.py", file_path="a.py",
        code_lines=["abcd"] if typing else ["abcdefgh"],
    )
    with Image.open(written[4]) as image:
        assert image.tobytes() == renderer.render(before, size).tobytes()
    with Image.open(written[5]) as image:
        assert image.tobytes() == renderer.render(at_trigger, size).tobytes()
    with Image.open(written[6]) as image:
        assert image.tobytes() == renderer.render(halfway, size).tobytes()
    with Image.open(written[8]) as image, Image.open(still) as final:
        assert image.tobytes() == final.tobytes()
    assert json.dumps(entry.to_dict()) == stored
    assert json.dumps(demo.to_dict()) == authored


@pytest.mark.parametrize("typing", [True, False])
def test_direct_frame_states_typing_remains_supported(
    tmp_path: Path, typing: bool,
) -> None:
    size = (640, 360)
    state = FrameState(title="a.py", file_path="a.py", code_lines=["abcdefgh"])
    stored = json.dumps(state.to_dict())
    renderer = SyntheticRenderer()
    still = tmp_path / "still.png"
    renderer.render(state, size).save(still)
    voice = write_silence(tmp_path / "voice.wav", 1000)
    written, _ = render_animation_frames(
        [still], [AudioClip(path=voice, duration_ms=1000)], voice, tmp_path / "anim",
        size=size, config=_config(typing=typing, typing_fraction=1.0),
        frame_states=[state], typing_flags=[True],
    )
    expected = FrameState(
        title="a.py", file_path="a.py", code_lines=["abcdefgh"],
        cursor_typed=4 if typing else None,
    )
    with Image.open(written[5]) as image:
        assert image.tobytes() == renderer.render(expected, size).tobytes()
    assert json.dumps(state.to_dict()) == stored


def test_gap_crossfade_never_extrapolates_input_pixels(tmp_path: Path) -> None:
    paths = [tmp_path / "first.png", tmp_path / "second.png"]
    for path, gray in zip(paths, [100, 200], strict=True):
        Image.new("RGB", (64, 48), (gray, gray, gray)).save(path)
    voice = write_silence(tmp_path / "voice.wav", 2220)
    clips = [AudioClip(path=voice, duration_ms=1000) for _ in paths]
    config = AnimationConfig(
        fps=10, gap_ms=220, waveform=False, progress_bar=False, cursor=False,
        transitions=True, transition_ms=450,
    )
    written, _ = render_animation_frames(
        paths, clips, voice, tmp_path / "anim", size=(64, 48), config=config,
        scene_ids=["first", "second"],
    )
    for path in written:
        with Image.open(path) as image:
            assert all(100 <= low <= high <= 200 for low, high in image.getextrema())


def test_lead_silence_has_no_early_cursor_ripple(tmp_path: Path) -> None:
    size = (320, 180)
    base = Image.new("RGB", size, (100, 100, 100))
    path = tmp_path / "base.png"
    base.save(path)
    voice = write_silence(tmp_path / "voice.wav", 1300)
    config = AnimationConfig(
        fps=10, lead_ms=300, waveform=False, progress_bar=False, cursor=True,
        transitions=False,
    )
    written, _ = render_animation_frames(
        [path], [AudioClip(path=voice, duration_ms=1000)], voice, tmp_path / "anim",
        size=size, config=config, frame_states=[FrameState(cursor_xy=(160, 90))],
    )
    _draw_cursor(ImageDraw.Draw(base), (160, 90), size[1] / 1080, ripple=0)
    with Image.open(written[0]) as image:
        assert image.tobytes() == base.tobytes()
    with Image.open(written[3]) as image:
        assert image.tobytes() != base.tobytes()


def test_typing_and_base_image_retention_is_bounded(tmp_path: Path) -> None:
    paths = []
    for index in range(6):
        path = tmp_path / f"base{index}.png"
        Image.new("RGB", (160, 90), (index, index, index)).save(path)
        paths.append(path)
    bases = _BaseFrames(paths)
    rendered = _StateFrames((160, 90))
    base_references = []
    state_references = []
    for index in range(6):
        base_references.append(weakref.ref(bases.get(index)))
        for count in range(20):
            state = FrameState(file_path="a.py", code_lines=["x" * count])
            state_references.append(weakref.ref(rendered.get(index, state)))
        assert len(bases.images) <= 2
        assert len(rendered.images) <= 2
    assert sum(reference() is not None for reference in base_references) == 2
    assert sum(reference() is not None for reference in state_references) == 2


@pytest.mark.parametrize("kwargs", [
    {"fps": 0}, {"fps": -1}, {"fps": 1.5}, {"fps": float("nan")},
    {"lead_ms": -1}, {"gap_ms": -1}, {"trail_ms": -1},
    {"transition_ms": -1}, {"typing_fraction": 0},
    {"typing_fraction": float("inf")}, {"ken_burns_zoom": float("nan")},
])
def test_animation_config_rejects_invalid_numeric_values(kwargs: dict) -> None:
    with pytest.raises(ValueError):
        AnimationConfig(**kwargs)


@pytest.mark.parametrize("name", ["lead_ms", "gap_ms", "trail_ms"])
def test_chunk_timing_rejects_negative_silence(name: str) -> None:
    with pytest.raises(ValueError):
        chunk_timing([AudioClip(path=Path("unused.wav"), duration_ms=100)], **{name: -1})


def test_mutated_config_is_validated_before_rendering(tmp_path: Path) -> None:
    path = tmp_path / "base.png"
    Image.new("RGB", (64, 48)).save(path)
    voice = write_silence(tmp_path / "voice.wav", 100)
    config = AnimationConfig()
    config.fps = 0
    with pytest.raises(ValueError):
        render_animation_frames(
            [path], [AudioClip(path=voice, duration_ms=100)], voice,
            tmp_path / "anim", size=(64, 48), config=config,
        )


def test_static_frame_holds_preserve_real_audio_lead_gaps_and_trail(
    tmp_path: Path,
) -> None:
    clips = [
        AudioClip(path=write_silence(tmp_path / f"clip{i}.wav", 400), duration_ms=400)
        for i in range(3)
    ]
    holds = frame_hold_durations(clips, lead_ms=300, gap_ms=220, trail_ms=600)
    assert holds == [920, 620, 1000]
    windows, total = chunk_timing(clips, lead_ms=300, gap_ms=220, trail_ms=600)
    assert sum(holds) == total == 2540
    assert holds[0] == windows[1][0]
    assert sum(holds[:2]) == windows[2][0]
    assert frame_hold_durations(clips[:1], lead_ms=300, trail_ms=600) == [1300]
    assert frame_hold_durations([], lead_ms=300, trail_ms=600) == []


@pytest.mark.parametrize("name", ["lead_ms", "gap_ms", "trail_ms"])
def test_static_frame_holds_reject_negative_padding(name: str) -> None:
    with pytest.raises(ValueError):
        frame_hold_durations([], **{name: -1})
