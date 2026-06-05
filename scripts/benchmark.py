#!/usr/bin/env python
"""Measure real DemoCreate performance and write ``data/benchmarks.json``.

Uses only the deterministic default backends (silent TTS, synthetic frames) so
the numbers are reproducible and need no system binaries beyond ``ffmpeg`` for
the optional encode timing. Run from the project root::

    uv run python scripts/benchmark.py

The manuscript's evaluation section reads the emitted JSON, so every reported
number is *measured*, not asserted.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from statistics import median

from democreate.cli import _starter_demo
from democreate.export.video import ffmpeg_available
from democreate.narration.sync import HeuristicTranscriber, sync_demo
from democreate.narration.tts import SilentTTSBackend, synthesize_demo
from democreate.pipeline import Pipeline, build_demo, render_video
from democreate.project_paths import Workspace


def _time(fn) -> float:
    """Return wall-clock milliseconds for calling ``fn``."""
    start = time.perf_counter()
    fn()
    return (time.perf_counter() - start) * 1000


def bench_build(repeats: int = 5) -> dict:
    """Median build-pipeline (TTS→sync→frames→export) latency for the starter demo."""
    import tempfile

    times = []
    for _ in range(repeats):
        with tempfile.TemporaryDirectory() as tmp:
            demo = _starter_demo()
            times.append(_time(lambda d=demo, t=tmp: build_demo(d, Workspace(t))))
    return {"runs": repeats, "median_ms": round(median(times), 1)}


def bench_render(animation_fps: int = 15) -> dict | None:
    """Animated-render throughput (ms of compute per second of output).

    Uses the package default ``animation_fps`` (``VideoConfig.animation_fps``) so
    the recorded throughput reflects the shipped default render, not an ad-hoc
    frame rate.
    """
    if not ffmpeg_available():
        return None
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Workspace(tmp)
        demo = _starter_demo()
        result = Pipeline(strict=False).run(demo, ws)
        out_s = (result.timeline.total_ms / 1000) if result.timeline else 1.0
        ms = _time(
            lambda: render_video(
                result, animate=True, animation_fps=animation_fps, verify=False
            )
        )
        return {
            "output_seconds": round(out_s, 2),
            "render_ms": round(ms, 1),
            "ms_per_output_second": round(ms / max(out_s, 0.1), 1),
            "animation_fps": animation_fps,
        }


def bench_sync() -> dict:
    """Heuristic sync sanity: word timestamps stay within the clip and ordered."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Workspace(tmp)
        demo = _starter_demo()
        clips = synthesize_demo(demo, ws, backend=SilentTTSBackend())
        sync_demo(demo, clips, transcriber=HeuristicTranscriber())
        actions = demo.iter_actions()
        with_ts = [a for a in actions if a.timestamp_ms is not None]
        ordered = all(
            with_ts[i].timestamp_ms <= with_ts[i + 1].timestamp_ms
            for i in range(len(with_ts) - 1)
        )
        return {
            "actions": len(actions),
            "actions_timestamped": len(with_ts),
            "monotonic": ordered,
        }


def main() -> None:
    """Run all benchmarks and write the JSON report."""
    report = {
        "build": bench_build(),
        "render": bench_render(),
        "sync": bench_sync(),
    }
    out = Path(__file__).resolve().parent.parent / "data" / "benchmarks.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
