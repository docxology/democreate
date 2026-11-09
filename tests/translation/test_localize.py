"""Localization must use resolved measured audio windows, not authored timing."""

from __future__ import annotations

import re
import shutil
import wave
from pathlib import Path

import pytest


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is unavailable")
@pytest.mark.parametrize(
    ("voice", "configured_voice", "expected_voice"),
    [("", "", "authored"), ("operator", "", "operator"), ("", "configured", "configured")],
)
def test_localized_sidecars_use_measured_padded_audio_windows(
    tmp_path: Path, voice: str, configured_voice: str, expected_voice: str,
) -> None:
    from democreate.config import RenderConfig
    from democreate.export.verify import verify_video
    from democreate.project_paths import Workspace
    from democreate.schema import Chunk, Demo, Scene
    from democreate.translation.localize import localize_render
    from democreate.translation.translator import IdentityTranslator, LanguageConfig

    demo = Demo(title="Measured localization", width=320, height=180, voice="authored", scenes=[
        Scene(id="s", chunks=[
            Chunk(id="first", text="one", start_ms=5000, duration_ms=1, voice="cast"),
            Chunk(id="second", text="one two three", start_ms=9000, duration_ms=1),
        ]),
    ])
    original = demo.to_json()
    config = RenderConfig()
    config.audio.voice = configured_voice
    config.audio.lead_silence_ms = 125
    config.audio.gap_ms = 275
    config.audio.trail_silence_ms = 200
    config.audio.normalize = False
    config.video.animation_fps = 5
    config.video.preset = "ultrafast"
    original_config = config.to_dict()
    workspace = Workspace(tmp_path / "localized")
    result = localize_render(
        demo, workspace, languages=LanguageConfig("en", "en", "en"),
        translator=IdentityTranslator(), tts="silent", config=config, verify=False,
        voice=voice,
    )
    durations = []
    for index in range(2):
        with wave.open(str(workspace.audio / f"chunk_{index:04d}.wav"), "rb") as audio:
            durations.append(round(audio.getnframes() * 1000 / audio.getframerate()))
    first_start = config.audio.lead_silence_ms
    second_start = first_start + durations[0] + config.audio.gap_ms
    expected = [
        (first_start, first_start + durations[0]),
        (second_start, second_start + durations[1]),
    ]
    for sidecar in (result.subtitle_srt, result.subtitle_vtt):
        assert sidecar is not None
        windows = []
        for line in sidecar.read_text().splitlines():
            if " --> " not in line:
                continue
            values = []
            for stamp in line.split(" --> "):
                hours, minutes, seconds, millis = map(int, re.split(r"[:,.]", stamp))
                values.append(((hours * 60 + minutes) * 60 + seconds) * 1000 + millis)
            windows.append(tuple(values))
        assert windows == expected
    assert demo.to_json() == original
    assert config.to_dict() == original_config
    resolved = Demo.from_file(workspace.demos / "demo.json")
    assert resolved.voice == expected_voice
    assert list(resolved.iter_chunks())[0].voice == "cast"
    assert (resolved.width, resolved.height) == (320, 180)
    assert result.video_path is not None
    report = verify_video(result.video_path, check_content=False, min_duration_s=0)
    assert (report.width, report.height) == (320, 180)


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is unavailable")
def test_localized_blank_system_voice_uses_native_default(tmp_path: Path) -> None:
    from democreate.config import RenderConfig
    from democreate.narration.tts import _system_tts_command
    from democreate.project_paths import Workspace
    from democreate.schema import Chunk, Demo, Scene
    from democreate.translation.localize import localize_render
    from democreate.translation.translator import LanguageConfig

    if _system_tts_command() is None:
        pytest.skip("no usable native speech engine")
    demo = Demo(title="Native default", width=320, height=180, scenes=[
        Scene(id="s", chunks=[Chunk(id="c", text="Native voice default.")]),
    ])
    original = demo.to_json()
    config = RenderConfig()
    config.audio.normalize = False
    config.video.animation_fps = 5
    config.video.preset = "ultrafast"
    workspace = Workspace(tmp_path / "native")
    result = localize_render(
        demo, workspace, languages=LanguageConfig("en", "en", "en"),
        config=config, tts="system", verify=False,
    )
    assert result.ok
    assert demo.to_json() == original
    assert config.audio.voice == ""
    with wave.open(str(workspace.audio / "chunk_0000.wav"), "rb") as audio:
        assert audio.getnframes() > 0
        assert any(audio.readframes(audio.getnframes()))
