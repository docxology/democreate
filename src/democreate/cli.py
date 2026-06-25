"""The ``democreate`` command-line interface.

A thin orchestration layer over the library — every command resolves to a few
calls into :mod:`democreate.pipeline` and the subsystems, so the CLI carries no
business logic of its own.

Commands::

    democreate init      [PATH]            write a starter demo artifact
    democreate inspect   DEMO              validate and summarize a demo
    democreate build     DEMO  [--output]  run the full pipeline -> frames/audio/player
    democreate render    DEMO  [--output]  render an animated HD MP4 + voiceover, verify
    democreate tour      REPO  [--output]  generate a codebase tour (--render for MP4)
    democreate portfolio DIR   [--output]  a timestamped summary video per project
    democreate paper     PDF   [--repo]    narrated demo of a research paper (PDF)
    democreate captions  DEMO  [--format]  emit subtitles to stdout
    democreate verify    VIDEO             content-assert a video (real/non-silent/non-black)
    democreate config    [OUT] [--theme]   write a commented render-config YAML
    democreate thumbnail DEMO  [--out]     render a poster/thumbnail frame
    democreate gif       DEMO  [--output]  build + export an animated GIF preview
    democreate stego     IMAGE [--demo]    extract/verify steganographic provenance
    democreate fetch-voice                 download the Kokoro neural-TTS model
    democreate backends                    list backends and their availability
    democreate version                     print the version
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from . import __version__
from .pipeline import build_demo
from .schema import Action, ActionType, Chunk, Demo, Scene, SceneKind

app = typer.Typer(
    name="democreate",
    help="Declarative, deterministic audio-visual demo generation.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


def _validate_theme(value: str) -> str:
    """Return ``value`` when it is a known theme, else exit with a usage error."""
    from .config import THEMES

    if value in THEMES:
        return value
    valid = ", ".join(sorted(THEMES))
    typer.echo(f"unknown theme {value!r}; choose one of: {valid}")
    raise typer.Exit(code=2)


def _validate_aspect(value: str) -> str:
    """Return ``value`` when it is a known aspect ratio or empty."""
    from .config import ASPECTS

    if not value or value in ASPECTS:
        return value
    valid = ", ".join(sorted(ASPECTS))
    typer.echo(f"unknown aspect {value!r}; choose one of: {valid}")
    raise typer.Exit(code=2)


def _validate_resolution(value: str) -> str:
    """Return ``value`` when it is a known resolution tier or empty."""
    from .config import RESOLUTIONS

    if not value or value in RESOLUTIONS:
        return value
    valid = ", ".join(sorted(RESOLUTIONS))
    typer.echo(f"unknown resolution {value!r}; choose one of: {valid}")
    raise typer.Exit(code=2)


def _load_demo(path: Path) -> Demo:
    """Load a :class:`Demo` from a ``.json`` or ``.yaml`` file."""
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        return Demo.from_yaml(text)
    return Demo.from_json(text)


def _starter_demo() -> Demo:
    """A small, valid demo used by ``init`` and as documentation-by-example."""
    scene = Scene(id="intro", title="Welcome", kind=SceneKind.CODEBASE)
    scene.chunks.append(
        Chunk(
            id="c1",
            text="Welcome to this project. Let us open the main module.",
            actions=[
                Action(ActionType.OPEN_FILE, {"path": "main.py"}, trigger_word="open"),
                Action(
                    ActionType.TYPE_CODE,
                    {"code": "print('hello, world')"},
                    trigger_word="main",
                ),
            ],
        )
    )
    term = Scene(id="run", title="Run It", kind=SceneKind.TERMINAL)
    term.chunks.append(
        Chunk(
            id="c2",
            text="Now we run the program from the terminal.",
            actions=[
                Action(
                    ActionType.RUN_COMMAND,
                    {"command": "python main.py", "output": "hello, world"},
                    trigger_word="run",
                )
            ],
        )
    )
    return Demo(title="Starter Demo", scenes=[scene, term])


@app.command()
def version() -> None:
    """Print the installed DemoCreate version."""
    console.print(f"democreate {__version__}")


@app.command()
def init(
    path: Path = typer.Argument(Path("demo.json"), help="Where to write the starter demo."),
    fmt: str = typer.Option("json", "--format", "-f", help="json or yaml"),
) -> None:
    """Write a starter demo artifact you can edit and then ``build``."""
    demo = _starter_demo()
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "yaml":
        path.write_text(demo.to_yaml(), encoding="utf-8")
    else:
        path.write_text(demo.to_json(), encoding="utf-8")
    console.print(f"[green]✓[/] wrote starter demo to {path}")


@app.command()
def inspect(demo: Path = typer.Argument(..., help="Path to a demo .json/.yaml")) -> None:
    """Validate a demo and print a structural summary."""
    d = _load_demo(demo)
    problems = d.validate()
    table = Table(title=f"Demo: {d.title}")
    table.add_column("metric")
    table.add_column("value", justify="right")
    table.add_row("scenes", str(len(d.scenes)))
    table.add_row("chunks", str(len(d.iter_chunks())))
    table.add_row("actions", str(len(d.iter_actions())))
    table.add_row("estimated duration (s)", f"{d.estimated_duration_ms() / 1000:.1f}")
    table.add_row("valid", "yes" if not problems else f"NO ({len(problems)} problems)")
    console.print(table)
    for p in problems:
        console.print(f"  [red]•[/] {p}")
    if problems:
        raise typer.Exit(code=1)


@app.command()
def build(
    demo: Path = typer.Argument(..., help="Path to a demo .json/.yaml"),
    output: Path = typer.Option(Path("output"), "--output", "-o", help="Output directory"),
    tts: str = typer.Option("auto", "--tts", help="TTS backend: auto|silent|kokoro|chatterbox"),
    strict: bool = typer.Option(True, "--strict/--no-strict", help="Fail on invalid demo"),
) -> None:
    """Run the full pipeline: TTS, sync, frames, captions, and HTML player."""
    from .narration.tts import get_tts_backend
    from .project_paths import Workspace

    d = _load_demo(demo)
    backend = get_tts_backend(tts)
    result = build_demo(d, Workspace(output), tts_backend=backend, strict=strict)
    console.print_json(json.dumps(result.summary()))
    console.print(f"[green]✓[/] player: {result.player_path}")


@app.command()
def tour(
    repo: Path = typer.Argument(..., help="Repository or directory to tour"),
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    title: str = typer.Option("Codebase Tour", "--title", "-t"),
    build_it: bool = typer.Option(True, "--build/--no-build", help="Build the HTML player"),
    render_it: bool = typer.Option(
        False, "--render/--no-render", help="Render an MP4 with a real voiceover"
    ),
    tts: str = typer.Option("system", "--tts", help="TTS backend when --render: system|silent"),
    voice: str = typer.Option("", "--voice", "-v", help="Voice id when --render"),
    theme: str = typer.Option("noir", "--theme", help="Theme preset when --render"),
) -> None:
    """Generate a codebase tour demo from a repository (build and/or render it)."""
    from .codebase.walker import walk_repository
    from .narration.script import generate_codebase_demo
    from .project_paths import Workspace

    summaries = walk_repository(repo)
    d = generate_codebase_demo(summaries, title=title)
    ws = Workspace(output)
    ws.demos.mkdir(parents=True, exist_ok=True)
    (ws.demos / "tour.json").write_text(d.to_json(), encoding="utf-8")
    console.print(f"[green]✓[/] generated tour with {len(d.scenes)} scenes")
    if render_it:
        from .narration.tts import get_tts_backend
        from .pipeline import Pipeline, render_video

        cfg = _resolve_config(None, _validate_theme(theme), voice, tts)
        use_voice = cfg.audio.voice if cfg.audio.backend != "silent" else None
        backend = get_tts_backend(cfg.audio.backend, voice=use_voice)
        result = Pipeline(tts_backend=backend, strict=False, config=cfg).run(d, ws)
        out, report = render_video(result, verify=True, config=cfg)
        console.print(f"[green]✓[/] video: {out}")
        if report is not None and not report.ok:
            console.print("[red]✗ verification failed[/]")
            raise typer.Exit(code=1)
        return
    if build_it:
        result = build_demo(d, ws, strict=False)
        console.print(f"[green]✓[/] player: {result.player_path}")


@app.command()
def portfolio(
    projects_dir: Path = typer.Argument(..., help="Directory of project subdirectories"),
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    tts: str = typer.Option("system", "--tts", help="TTS backend: system|silent|kokoro"),
    voice: str = typer.Option("", "--voice", "-v", help="Voice id (system: e.g. Samantha)"),
    theme: str = typer.Option("noir", "--theme", help="Theme preset: noir|dark|light|midnight|paper"),
    resolution: str = typer.Option("1080p", "--resolution", help="720p|1080p|1440p|2160p|4k"),
    max_projects: int = typer.Option(0, "--max-projects", help="Cap projects (0 = all)"),
    max_modules: int = typer.Option(3, "--max-modules", help="Key-module code scenes per project"),
    skip: str = typer.Option("", "--skip", help="Comma-separated project names to skip"),
) -> None:
    """Render a timestamped summary video for every project under a directory.

    Each project gets its own ``output/<name>/`` folder; a failing project is
    recorded and the batch continues. Writes a portfolio index (JSON + HTML).
    """
    from .portfolio import render_portfolio

    theme = _validate_theme(theme)
    resolution = _validate_resolution(resolution)
    cfg = _resolve_config(None, theme, voice, tts)
    if resolution:
        cfg.set_resolution(resolution)
    skip_names = tuple(s.strip() for s in skip.split(",") if s.strip())
    console.print(
        f"[cyan]portfolio[/] {projects_dir} → {output} "
        f"at {cfg.video.width}x{cfg.video.height}, '{cfg.theme.name}' theme…"
    )
    report = render_portfolio(
        projects_dir,
        output,
        config=cfg,
        tts=cfg.audio.backend,
        voice=cfg.audio.voice,
        max_projects=max_projects,
        max_modules=max_modules,
        skip=skip_names,
    )
    for r in report.results:
        mark = "[green]✓[/]" if r.ok else "[red]✗[/]"
        detail = f"{r.duration_s:.0f}s · {r.scenes} scenes" if r.ok else (r.error or "failed")
        console.print(f"  {mark} {r.name}: {detail}")
    console.print(
        f"[green]✓[/] {report.ok_count}/{len(report.results)} rendered · "
        f"index: {report.index_html}"
    )
    if report.ok_count == 0 and report.results:
        raise typer.Exit(code=1)


@app.command()
def captions(
    demo: Path = typer.Argument(...),
    fmt: str = typer.Option("srt", "--format", "-f", help="srt|vtt|ass"),
) -> None:
    """Emit subtitles for a demo to stdout."""
    from .assembly import captions as captions_mod

    d = _load_demo(demo)
    emitters = {
        "srt": captions_mod.to_srt,
        "vtt": captions_mod.to_vtt,
        "ass": captions_mod.to_ass,
    }
    if fmt not in emitters:
        raise typer.BadParameter(f"unknown format {fmt!r}; choose srt|vtt|ass")
    typer.echo(emitters[fmt](d))


@app.command()
def render(
    demo: Path = typer.Argument(..., help="Path to a demo .json/.yaml"),
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    tts: str = typer.Option("system", "--tts", help="TTS backend: system|silent|kokoro|chatterbox"),
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
    use_voice = cfg.audio.voice if cfg.audio.backend in {"system", "kokoro", "chatterbox"} else None
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


def _resolve_config(config_path: Path | None, theme: str, voice: str, tts: str):
    """Build a RenderConfig from a --config file or a --theme preset, with overrides."""
    from .config import RenderConfig

    cfg = RenderConfig.from_file(config_path) if config_path else RenderConfig.preset(theme)
    if voice:
        cfg.audio.voice = voice
    elif not config_path:
        cfg.audio.voice = ""
    if tts:
        cfg.audio.backend = tts
    return cfg


@app.command()
def paper(
    pdf: Path = typer.Argument(..., help="Path to the paper PDF"),
    repo: Path = typer.Option(None, "--repo", "-r", help="Associated codebase directory"),
    figures: Path = typer.Option(None, "--figures", help="Directory of exported figure images"),
    output: Path = typer.Option(Path("output"), "--output", "-o"),
    pages: str = typer.Option("1", "--pages", help="Comma-separated 1-based PDF pages to show"),
    theme: str = typer.Option("paper", "--theme", help="Theme preset: paper|dark|light|midnight"),
    voice: str = typer.Option("", "--voice", "-v"),
    tts: str = typer.Option("system", "--tts"),
    aspect: str = typer.Option("", "--aspect", help="Aspect preset: 16:9|9:16|1:1|4:3|4:5"),
    resolution: str = typer.Option("", "--resolution", help="16:9 tier: 720p|1080p|1440p|2160p|4k"),
    author: str = typer.Option("", "--author", help="Override author (default: the PDF's author)"),
    watermark: str = typer.Option("", "--watermark", help="Persistent watermark text"),
    max_figures: int = typer.Option(6, "--max-figures", help="How many figures to feature"),
    config: Path = typer.Option(None, "--config", help="RenderConfig YAML (overrides --theme)"),
    render_it: bool = typer.Option(True, "--render/--no-render", help="Render the video"),
) -> None:
    """Generate a narrated demo of a research paper (PDF + optional codebase)."""
    from .paper import (
        build_paper_demo,
        render_pages,
        summarize_paper,
        summarize_structure,
    )
    from .pipeline import Pipeline, render_video
    from .project_paths import Workspace

    theme = _validate_theme(theme)
    aspect = _validate_aspect(aspect)
    resolution = _validate_resolution(resolution)
    ws = Workspace(output)
    console.print(f"[cyan]reading paper[/] {pdf}")
    summary = summarize_paper(pdf, figures_dir=figures)
    # Deeper structure: a correct abstract (skipping the TOC), real figure
    # captions, and the paper's section list.
    figure_captions: list = []
    sections: list = []
    try:
        structure = summarize_structure(pdf)
        if structure.get("abstract"):
            summary.abstract = structure["abstract"]
        figure_captions = structure.get("figure_captions", [])
        sections = structure.get("sections", [])
    except Exception as exc:  # noqa: BLE001 - structure is best-effort
        console.print(f"[yellow]structure extraction skipped:[/] {exc}")
    console.print(
        f"[green]✓[/] '{summary.title}' — {summary.page_count} pages, "
        f"{len(summary.figures)} figures, {len(sections)} sections"
    )

    page_nums = [int(p) for p in pages.split(",") if p.strip()]
    page_imgs = render_pages(pdf, ws.root / "pages", pages=page_nums, dpi=140) if page_nums else []

    code_summaries = None
    arch_img = None
    if repo is not None:
        from .animation.diagram import DiagramNode, render_architecture_diagram
        from .codebase.walker import walk_repository
        from .paper.script import _group_modules

        code_summaries = walk_repository(repo)
        columns = [
            (name, [DiagramNode(label=m) for m in mods])
            for name, mods in _group_modules(code_summaries)
        ]
        if columns:
            arch_img = ws.root / "assets" / "architecture.png"
            arch_img.parent.mkdir(parents=True, exist_ok=True)
            render_architecture_diagram(
                (1920, 1080), title="Codebase Architecture", columns=columns
            ).save(arch_img)
        console.print(f"[green]✓[/] codebase: {len(code_summaries)} modules")

    demo = build_paper_demo(
        summary,
        max_figures=max_figures,
        code_summaries=code_summaries,
        page_images=page_imgs,
        architecture_image=arch_img,
        figure_captions=figure_captions,
        sections=sections,
        voice=voice,
    )
    demo_out = ws.demos / "paper.json"
    demo_out.write_text(demo.to_json(), encoding="utf-8")
    console.print(f"[green]✓[/] generated demo with {len(demo.scenes)} scenes")

    if not render_it:
        return
    cfg = _resolve_config(config, theme, voice, tts)
    if resolution:
        cfg.set_resolution(resolution)
        demo.width, demo.height = cfg.video.width, cfg.video.height
    if aspect:
        cfg.set_aspect(aspect)
        demo.width, demo.height = cfg.video.width, cfg.video.height
    # Attribute the video to the paper's author by default (PDF metadata).
    cfg.metadata.author = author or summary.authors
    cfg.metadata.source = summary.title
    if watermark:
        cfg.metadata.watermark = watermark
    from .narration.tts import get_tts_backend

    backend = get_tts_backend(cfg.audio.backend, voice=cfg.audio.voice)
    result = Pipeline(tts_backend=backend, strict=False, config=cfg).run(demo, ws)
    out, report = render_video(result, verify=True, config=cfg)
    console.print(f"[green]✓[/] video: {out}")
    if report is not None:
        console.print_json(json.dumps(report.to_dict()))
        if not report.ok:
            raise typer.Exit(code=1)
        console.print("[green]✓ verified: real video + non-silent audio[/]")


@app.command()
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


@app.command()
def config(
    out: Path = typer.Argument(Path("democreate.yaml"), help="Where to write the config"),
    theme: str = typer.Option("dark", "--theme", help="Base theme preset"),
) -> None:
    """Write a fully-commented render-config YAML you can edit and pass to --config."""
    from .config import RenderConfig

    theme = _validate_theme(theme)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(RenderConfig.commented_yaml(theme), encoding="utf-8")
    console.print(f"[green]✓[/] wrote config to {out}")
    console.print("Edit it, then: [cyan]democreate render demo.json --config " f"{out}[/]")


@app.command()
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


@app.command()
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


@app.command()
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


@app.command(name="fetch-voice")
def fetch_voice() -> None:
    """Download the Kokoro neural-TTS model files (~340 MB) for `--tts kokoro`.

    Installs them into the DemoCreate cache so `--tts kokoro` works offline
    thereafter. Requires the `tts` extra (`uv pip install -e ".[tts]"`).
    """
    from .narration.tts import _kokoro_cache_dir, fetch_kokoro_model

    console.print(f"[cyan]fetching Kokoro model[/] → {_kokoro_cache_dir()} (~340 MB)…")
    model, voices = fetch_kokoro_model()
    console.print(f"[green]✓[/] model:  {model}")
    console.print(f"[green]✓[/] voices: {voices}")
    console.print("Now render with a neural voice: [cyan]democreate render demo.json --tts kokoro --voice af_heart[/]")


@app.command()
def backends() -> None:
    """List subsystem backends and whether their optional extras are installed."""
    import shutil

    from .narration.tts import _system_tts_command

    rows = [
        ("TTS (kokoro)", "kokoro_onnx", "tts"),
        ("TTS (chatterbox)", "chatterbox", "tts"),
        ("Transcribe (whisper)", "whisper", "whisper"),
        ("Capture (mss)", "mss", "capture"),
        ("Browser (playwright)", "playwright", "browser"),
        ("Animation (manim)", "manim", "animation"),
        ("Replay (pynput)", "pynput", "replay"),
        ("Legacy compositor slot (moviepy)", "moviepy", "video"),
        ("Codebase (tree-sitter)", "tree_sitter", "codebase"),
    ]
    table = Table(title="DemoCreate backends")
    table.add_column("capability")
    table.add_column("status")
    table.add_column("install")
    system_tts = _system_tts_command()
    system_rows = [
        (
            "TTS (system voice)",
            system_tts is not None,
            f"usable OS voice: {system_tts or 'say/espeak'}",
        ),
        (
            "Video assembly (ffmpeg)",
            shutil.which("ffmpeg") is not None,
            "OS binary: ffmpeg",
        ),
    ]
    for label, present, install in system_rows:
        status = "[green]available[/]" if present else "[yellow]absent[/]"
        table.add_row(label, status, install)
    for label, module, extra in rows:
        available = importlib.util.find_spec(module) is not None
        status = "[green]installed[/]" if available else "[yellow]default[/]"
        table.add_row(label, status, f"uv sync --extra {extra}")
    console.print(table)
    console.print("All capabilities have a working deterministic default backend.")


def main() -> None:  # pragma: no cover - console-script entry
    """Entry point for the ``democreate`` console script."""
    app()


if __name__ == "__main__":  # pragma: no cover
    main()
