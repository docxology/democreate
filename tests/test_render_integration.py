"""Real end-to-end video render integration test (requires the ffmpeg binary).

Skipped automatically when ffmpeg is absent. Uses the deterministic silent TTS so
it is fast and reproducible; content (silence/black) checks are therefore left to
the dedicated unit tests — here we assert the real mux: a 1920x1080 H.264 video
with an audio stream covering it, produced via the concat-demuxer path. This is
the regression guard for the relative-path concat bug.
"""

from __future__ import annotations

import pytest

from democreate.export.video import ffmpeg_available
from democreate.pipeline import build_demo, render_video
from democreate.schema import Action, ActionType, Chunk, Demo, Scene, SceneKind

pytestmark = [
    pytest.mark.backend,
    pytest.mark.skipif(not ffmpeg_available(), reason="ffmpeg not installed"),
]


def _tiny_hd_demo() -> Demo:
    s = Scene(id="s", title="Hi", kind=SceneKind.CODEBASE)
    s.chunks.append(
        Chunk(
            id="c1",
            text="One two three four five six.",
            actions=[Action(ActionType.OPEN_FILE, {"path": "a.py", "code": "x = 1"})],
        )
    )
    s.chunks.append(Chunk(id="c2", text="Seven eight nine ten."))
    return Demo(title="Render IT", scenes=[s], width=1920, height=1080, fps=24)


def test_render_video_produces_real_hd_mp4(tmp_workspace) -> None:
    from democreate.export.verify import verify_video

    demo = _tiny_hd_demo()
    result = build_demo(demo, tmp_workspace, strict=False)
    # one frame per chunk, so frames and clips align
    assert len(result.frame_paths) == len(result.clips)

    out, report = render_video(result, verify=True)
    assert out.exists() and out.stat().st_size > 1000

    # structural verification (silent TTS, so skip the non-silent content gate)
    structural = verify_video(
        out, expected_width=1920, expected_height=1080,
        min_duration_s=0.5, check_content=False,
    )
    assert structural.has_video
    assert structural.width == 1920 and structural.height == 1080
    assert structural.has_audio
    assert structural.duration_s > 0.5


def test_render_video_relative_output_path(tmp_path, monkeypatch) -> None:
    # Regression: the concat demuxer resolves frame paths relative to the concat
    # script's dir, so a relative -o must still work (frames written absolute).
    monkeypatch.chdir(tmp_path)
    from democreate.project_paths import Workspace

    demo = _tiny_hd_demo()
    result = build_demo(demo, Workspace("relout"), strict=False)
    out, _ = render_video(result, out_path=None, verify=False)
    assert out.exists()
