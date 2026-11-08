#!/usr/bin/env python
"""Measure real DemoCreate performance and write ``data/benchmarks.json``.

Uses only the deterministic default backends (silent TTS, synthetic frames) so
the inputs are repeatable (wall-clock samples vary). The optional encoded-video
measurement requires both ``ffmpeg`` and ``ffprobe``. Run from the project root::

    uv run python scripts/benchmark.py

Historical manuscript measurements remain separate from newly emitted reports.
Every sample is host-specific, not a general performance guarantee.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
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
    return {
        "stage": "build_demo wall clock (validation, TTS, sync, frames, exports)",
        "runs": repeats,
        "samples_ms": times,
        "median_ms": round(median(times), 1),
        "input_construction_timed": False,
    }


def bench_render(animation_fps: int = 15) -> dict | None:
    """Full render wall clock per measured encoded-video second.

    Encoding uses the shipped default animation frame rate. Probe the resulting
    video stream outside the timer; retain its planned timeline separately.
    """
    if not ffmpeg_available() or shutil.which("ffprobe") is None:
        return None
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Workspace(tmp)
        demo = _starter_demo()
        result = Pipeline(strict=False).run(demo, ws)
        out_s = (result.timeline.total_ms / 1000) if result.timeline else 1.0
        video = ws.video / "benchmark.mp4"
        ms = _time(
            lambda: render_video(
                result, out_path=video, animate=True,
                animation_fps=animation_fps, verify=False,
            )
        )
        probe = json.loads(subprocess.check_output(
            [
                "ffprobe", "-v", "error", "-select_streams", "v:0",
                "-show_entries", "stream=duration,width,height,r_frame_rate",
                "-of", "json", str(video),
            ],
            stdin=subprocess.DEVNULL,
        ))["streams"][0]
        encoded_seconds = float(probe["duration"])
        return {
            "stage": "render_video wall clock; verify=False",
            "includes": ["voiceover", "animation", "encoding", "chapter mux", "provenance"],
            "samples_ms": [ms],
            "verification_timed": False,
            "output_seconds": encoded_seconds,
            "output_duration_basis": "ffprobe video-stream duration; outside timer",
            "timeline_seconds": out_s,
            "encoded_geometry": {"width": probe["width"], "height": probe["height"]},
            "render_ms": round(ms, 1),
            "ms_per_output_second": round(ms / encoded_seconds, 1),
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
            "kind": "heuristic structural sanity; not acoustic accuracy",
            "actions": len(actions),
            "actions_timestamped": len(with_ts),
            "monotonic": ordered,
        }


def _command_identity(argv: list[str]) -> dict:
    """Record tool output or its concrete unavailability without a fake fallback."""
    if shutil.which(argv[0]) is None:
        return {"available": False, "reason": "executable not found"}
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    return {
        "available": result.returncode == 0,
        "returncode": result.returncode,
        "output": (result.stdout + result.stderr).strip(),
    }


def _source_identity(root: Path, input_json: str) -> dict:
    """Hash runtime files, metadata, this script and the exact benchmark input.

    The retained manifest uses only repository-relative or generated-input names.
    Include package resources, not merely Python modules: templates affect the
    measured exporter just as directly as its Python implementation.
    """
    files = [
        path for path in (root / "src/democreate").rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    ]
    files += [
        root / "pyproject.toml", root / "uv.lock", root / "scripts/benchmark.py",
    ]
    source = hashlib.sha256()
    manifest = []
    for path in sorted(files):
        name = path.relative_to(root).as_posix()
        content = path.read_bytes()
        source.update(name.encode("utf-8") + b"\0")
        source.update(content + b"\0")
        manifest.append({
            "path": name,
            "sha256": hashlib.sha256(content).hexdigest(),
            "size_bytes": len(content),
        })
    content = input_json.encode("utf-8")
    name = "input/starter-demo.json"
    source.update(name.encode("utf-8") + b"\0")
    source.update(content + b"\0")
    manifest.append({
        "path": name,
        "sha256": hashlib.sha256(content).hexdigest(),
        "size_bytes": len(content),
    })
    return {"source_sha256": source.hexdigest(), "source_manifest": manifest}


def _identity() -> dict:
    """Bind samples to source bytes, exact input and interpreter/tool versions."""
    root = Path(__file__).resolve().parent.parent
    # Source identity includes non-Python runtime resources and exact input bytes.
    demo = _starter_demo()
    input_json = demo.to_json()
    packages = {
        distribution.metadata["Name"]: distribution.version
        for distribution in importlib.metadata.distributions()
        if distribution.metadata["Name"]
    }
    return {
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        **_source_identity(root, input_json),
        "input": json.loads(input_json),
        "input_sha256": hashlib.sha256(input_json.encode()).hexdigest(),
        "geometry": {"width": demo.width, "height": demo.height, "fps": demo.fps},
        "runtime": {
            "executable": sys.executable,
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "packages": dict(sorted(packages.items())),
        },
        "tools": {
            "ffmpeg": _command_identity(["ffmpeg", "-version"]),
            "ffprobe": _command_identity(["ffprobe", "-version"]),
        },
        "backends": {"tts": "silent", "transcriber": "heuristic", "capture": "synthetic"},
    }


def main() -> None:
    """Run timings and retain raw samples plus source/input/runtime identity."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "benchmarks.json",
        help="Report path; use an output/ path to preserve tracked historical data",
    )
    args = parser.parse_args()
    report = {
        "identity": _identity(),
        "build": bench_build(),
        "render": bench_render(),
        "sync": bench_sync(),
    }
    if report["render"] is None:
        missing_tools = [
            name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None
        ]
        report["render_unavailable_tools"] = missing_tools
        report["render_unavailable_reason"] = (
            "required render tools unavailable: " + ", ".join(missing_tools)
        )
    out = args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
