"""Media-facing CLI commands: render, verify, thumbnail, gif, stego.

Split out of :mod:`democreate.cli` (agent refactoring lane); the commands are
registered on the shared ``app`` there, so ``democreate render`` etc. are
unchanged.
"""

from __future__ import annotations

import json
from pathlib import Path

import typer

from ._cli_common import (
    _load_demo,
    _resolve_config,
    _validate_aspect,
    _validate_resolution,
    _validate_theme,
    console,
)

def render(
    demo: Path = typer.Argument(..., help="Path to a demo .json/.yaml"),
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    tts: str = typer.Option("system", "--tts", help="TTS backend: system|silent|kokoro|elevenlabs|chatterbox"),
    voice: str = typer.Option("", "--voice", "-v", help="Optional voice id (system: e.g. Samantha, Daniel)"),
    fps: int = typer.Option(0, "--fps", help="Frame rate (0 = demo default)"),
    captions: bool = typer.Option(False, "--captions/--no-captions", help="Burn subtitles into the video"),
    animate: bool = typer.Option(True, "--animate/--no-animate", help="Moving waveform + progress bar"),
    animation_fps: int = typer.Option(15, "--animation-fps", help="Animated render frame rate"),
    theme: str = typer.Option("noir", "--theme", help="Theme preset: noir|dark|light|midnight|paper"),
    aspect: str = typer.Option("", "--aspect", help="Aspect preset: 16:9|9:16|1:1|4:3|4:5"),
    resolution: str = typer.Option("", "--resolution", help="16:9 tier: 720p|1080p|1440p|2160p|4k"),
    author: str = typer.Option("", "--author", help="Creator name (overlay + metadata + provenance)"),
    watermark: str = typer.Option("", "--watermark", help="Persistent watermark text"),
    header: bool = typer.Option(False, "--header/--no-header", help="Show the top metadata bar"),
    config: Path = typer.Option(None, "--config", help="RenderConfig YAML (overrides --theme/--voice)"),
) -> None:
    """Render a demo to an HD MP4 with real voiceover, then verify its content."""
    from .narration.tts import get_tts_backend
    from .pipeline import Pipeline, render_video
    from .project_paths import Workspace

    theme = _validate_theme(theme)
    aspect = _validate_aspect(aspect)
    resolution = _validate_resolution(resolution)
    d = _load_demo(demo)
    cfg = _resolve_config(config, theme, voice, tts)
    if resolution:
        cfg.set_resolution(resolution)
        d.width, d.height = cfg.video.width, cfg.video.height
    if aspect:
        cfg.set_aspect(aspect)
        d.width, d.height = cfg.video.width, cfg.video.height
    if author:
        cfg.metadata.author = author
    if watermark:
        cfg.metadata.watermark = watermark
    cfg.metadata.header = header
    use_voice = cfg.audio.voice if cfg.audio.backend in {"system", "kokoro", "elevenlabs", "chatterbox"} else None
    backend = get_tts_backend(cfg.audio.backend, voice=use_voice)
    console.print(
        f"[cyan]rendering[/] {d.title!r} at {d.width}x{d.height} "
        f"via '{cfg.audio.backend}' voice, '{cfg.theme.name}' theme…"
    )
    result = Pipeline(tts_backend=backend, strict=False, config=cfg).run(d, Workspace(output))
    out, report = render_video(
        result,
        fps=fps or None,
        burn_captions=captions,
        verify=True,
        animate=animate,
        animation_fps=animation_fps,
        config=cfg,
    )
    console.print(f"[green]✓[/] video: {out}")
    if report is not None:
        console.print_json(json.dumps(report.to_dict()))
        if not report.ok:
            console.print("[red]✗ verification failed[/]")
            raise typer.Exit(code=1)
        console.print("[green]✓ verified: real video + non-silent audio[/]")




def verify(
    video: Path = typer.Argument(..., help="Path to a video file to verify"),
    width: int = typer.Option(0, "--width", help="Expected width (0 = skip)"),
    height: int = typer.Option(0, "--height", help="Expected height (0 = skip)"),
    min_duration: float = typer.Option(1.0, "--min-duration", help="Minimum seconds"),
) -> None:
    """Content-assert a video: real streams, expected size, non-silent, non-black."""
    from .export.verify import verify_video

    report = verify_video(
        video,
        expected_width=width or None,
        expected_height=height or None,
        min_duration_s=min_duration,
    )
    console.print_json(json.dumps(report.to_dict()))
    raise typer.Exit(code=0 if report.ok else 1)




def thumbnail(
    demo: Path = typer.Argument(..., help="Path to a demo .json/.yaml"),
    out: Path = typer.Option(Path("poster.png"), "--out", "-o"),
    theme: str = typer.Option("dark", "--theme"),
    subtitle: str = typer.Option("", "--subtitle"),
) -> None:
    """Render a poster / thumbnail frame for a demo."""
    from .config import THEMES
    from .export.poster import render_poster

    theme = _validate_theme(theme)
    d = _load_demo(demo)
    render_poster(
        d, out, size=(d.width, d.height), theme=THEMES.get(theme),
        subtitle=subtitle or None,
    )
    console.print(f"[green]✓[/] poster: {out}")




def gif(
    demo: Path = typer.Argument(..., help="Path to a demo .json/.yaml"),
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    out: Path = typer.Option(Path("demo.gif"), "--gif"),
    fps: int = typer.Option(8, "--fps"),
    theme: str = typer.Option("dark", "--theme"),
) -> None:
    """Build a demo and export an animated GIF preview of its frames."""
    from .config import RenderConfig
    from .export.poster import demo_to_gif
    from .pipeline import Pipeline
    from .project_paths import Workspace

    theme = _validate_theme(theme)
    d = _load_demo(demo)
    cfg = RenderConfig.preset(theme)
    result = Pipeline(strict=False, config=cfg).run(d, Workspace(output))
    demo_to_gif(result.frame_paths, out, fps=fps)
    console.print(f"[green]✓[/] gif: {out}")




def stego(
    image: Path = typer.Argument(..., help="A signed PNG (e.g. output/provenance/poster_signed.png)"),
    demo: Path = typer.Option(None, "--demo", help="Demo to verify the payload against"),
) -> None:
    """Extract (and optionally verify) the steganographic provenance in a PNG."""
    from PIL import Image

    from .export.stego import extract_provenance, verify_provenance

    img = Image.open(image).convert("RGB")
    prov = extract_provenance(img)
    console.print_json(json.dumps(prov))
    if demo is not None:
        ok = verify_provenance(img, _load_demo(demo))
        console.print(
            "[green]✓ provenance matches the demo[/]" if ok
            else "[red]✗ provenance does NOT match the demo[/]"
        )
        raise typer.Exit(code=0 if ok else 1)
