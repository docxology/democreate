"""End-to-end orchestration: a declarative :class:`Demo` becomes rendered output.

The :class:`Pipeline` wires the subsystems together in the canonical order::

    script? -> validate -> TTS -> TTS->STT sync -> timeline -> compose(frames+manifest)
            -> captions -> interactive player + transcript + chapters

Every stage is a pure function of the (mutated) demo plus a
:class:`~democreate.project_paths.Workspace`. With only the core dependencies
installed, the deterministic default backends carry the whole pipeline to a real,
inspectable result (silent audio, synthetic frames, a manifest, captions, an HTML
player). Optional extras and system binaries upgrade individual surfaces without
changing this orchestration; guarded adapter slots fail explicitly when an
integration is not available.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ._logging import get_logger, log_stage
from .assembly import captions as captions_mod
from .assembly.compositor import (
    Compositor,
    ManifestCompositor,
    Timeline,
    build_timeline,
)
from .errors import RenderError, SchemaValidationError
from .export import formats as formats_mod
from .export.interactive import export_html_player
from .media import AudioClip
from .narration.sync import Transcriber, sync_demo
from .narration.tts import TTSBackend, synthesize_demo
from .project_paths import Workspace
from .schema import Demo

logger = get_logger(__name__)

__all__ = ["PipelineResult", "Pipeline", "build_demo", "render_video"]


@dataclass
class PipelineResult:
    """Paths and artifacts produced by a pipeline run.

    Attributes:
        demo: The (synced) demo that was rendered.
        workspace: The workspace everything was written under.
        clips: Rendered narration audio clips, in chunk order.
        timeline: The computed render timeline.
        manifest_path: The deterministic render manifest JSON.
        frame_paths: Rendered still frames, in order.
        caption_paths: Generated subtitle files keyed by format ("srt"/"vtt").
        player_path: The interactive HTML player.
        transcript_path: The Markdown transcript.
        demo_path: The serialized demo JSON.
    """

    demo: Demo
    workspace: Workspace
    clips: list[AudioClip] = field(default_factory=list)
    timeline: Timeline | None = None
    manifest_path: Path | None = None
    frame_paths: list[Path] = field(default_factory=list)
    caption_paths: dict[str, Path] = field(default_factory=dict)
    player_path: Path | None = None
    transcript_path: Path | None = None
    demo_path: Path | None = None

    def summary(self) -> dict[str, object]:
        """A compact JSON-able summary of what was produced."""
        return {
            "title": self.demo.title,
            "scenes": len(self.demo.scenes),
            "chunks": len(self.demo.iter_chunks()),
            "actions": len(self.demo.iter_actions()),
            "duration_ms": self.timeline.total_ms if self.timeline else None,
            "frames": len(self.frame_paths),
            "clips": len(self.clips),
            "player": str(self.player_path) if self.player_path else None,
        }


class Pipeline:
    """Configurable orchestrator over the DemoCreate subsystems.

    Args:
        tts_backend: TTS backend; default is the deterministic silent backend.
        transcriber: Transcriber for sync; default is the heuristic transcriber.
        compositor: Frame/manifest compositor; default is :class:`ManifestCompositor`.
        wpm: Narration pace used for duration estimates when no audio exists yet.
        strict: When ``True``, raise :class:`SchemaValidationError` on an invalid
            demo instead of logging warnings.
    """

    def __init__(
        self,
        *,
        tts_backend: TTSBackend | None = None,
        transcriber: Transcriber | None = None,
        compositor: Compositor | None = None,
        wpm: int = 150,
        strict: bool = True,
        config=None,
    ) -> None:
        from .config import RenderConfig

        self.tts_backend = tts_backend
        self.transcriber = transcriber
        # When no compositor is supplied, build one sized to each demo in run()
        # so frames render at the demo's true resolution (e.g. HD 1920x1080).
        self._compositor_override = compositor
        self.wpm = wpm
        self.strict = strict
        self.config = config or RenderConfig()

    def run(self, demo: Demo, workspace: Workspace | None = None) -> PipelineResult:
        """Render ``demo`` end-to-end, returning a :class:`PipelineResult`.

        Args:
            demo: The demo to render. It is mutated in place (audio paths, timing).
            workspace: Output workspace; a default ``./output`` workspace is used
                if omitted.
        """
        ws = workspace or Workspace()
        result = PipelineResult(demo=demo, workspace=ws)

        problems = demo.validate()
        if problems:
            if self.strict:
                raise SchemaValidationError(problems)
            for p in problems:
                logger.warning("demo validation: %s", p)

        with log_stage("narration synthesis (TTS)", logger):
            result.clips = synthesize_demo(demo, ws, backend=self.tts_backend)

        with log_stage("TTS->STT synchronization", logger):
            # Anchor chunk/action times to the SAME silence model used to
            # assemble the voiceover and lay out the frames, so captions and the
            # interactive player stay locked to the spoken audio (no drift).
            sync_demo(demo, result.clips, transcriber=self.transcriber,
                      lead_ms=self.config.audio.lead_silence_ms,
                      gap_ms=self.config.audio.gap_ms)

        with log_stage("timeline", logger):
            result.timeline = build_timeline(demo, fps=demo.fps, wpm=self.wpm)

        with log_stage("compose frames + manifest", logger):
            compositor = self._compositor_override or ManifestCompositor(
                width=demo.width, height=demo.height, theme=self.config.theme
            )
            result.manifest_path = compositor.compose(result.timeline, ws)
            result.frame_paths = sorted(ws.frames.glob("frame_*.png"))

        with log_stage("captions", logger):
            srt = ws.captions / "captions.srt"
            vtt = ws.captions / "captions.vtt"
            srt.write_text(captions_mod.to_srt(demo), encoding="utf-8")
            vtt.write_text(captions_mod.to_vtt(demo), encoding="utf-8")
            result.caption_paths = {"srt": srt, "vtt": vtt}

        with log_stage("export player + transcript + json", logger):
            # The player needs its own caption/chapter timeline (built from the
            # demo), not the compositor's frame timeline. Frames live in a sibling
            # directory, so reference them relatively for a portable player.
            result.player_path = export_html_player(
                demo,
                None,
                ws.web / "player.html",
                frames_dir="../frames",
            )
            transcript = ws.demos / "transcript.md"
            transcript.write_text(formats_mod.to_markdown(demo), encoding="utf-8")
            result.transcript_path = transcript
            demo_path = ws.demos / "demo.json"
            demo_path.write_text(
                formats_mod.to_json(demo, relative_to=ws.root), encoding="utf-8"
            )
            result.demo_path = demo_path

        logger.info("pipeline complete: %s", result.summary())
        return result


def build_demo(demo: Demo, workspace: Workspace | None = None, **kwargs: object) -> PipelineResult:
    """Convenience one-shot: construct a default :class:`Pipeline` and run it.

    Args:
        demo: The demo to render.
        workspace: Output workspace (default ``./output``).
        **kwargs: Forwarded to :class:`Pipeline` (e.g. ``strict=False``).
    """
    return Pipeline(**kwargs).run(demo, workspace)  # type: ignore[arg-type]


def _build_voiceover(result: PipelineResult, out_path: Path, audio_config) -> Path:
    """Assemble the voiceover: concat with pauses, then normalize + fade if able.

    Inter-chunk gaps and lead/trail silence (from ``audio_config``) give the
    narration breathing room; loudness normalization and fades are applied with
    ffmpeg when present and ``audio_config.normalize`` is set, and skipped
    gracefully otherwise.
    """
    from .assembly.audio import (
        apply_fade,
        concat_with_gaps,
        ffmpeg_audio_available,
        normalize_audio,
    )
    from .errors import BackendUnavailableError

    clip_paths = [Path(c.path) for c in result.clips]
    raw = out_path.with_name("voiceover_raw.wav")
    concat_with_gaps(
        clip_paths,
        raw,
        gap_ms=audio_config.gap_ms,
        lead_ms=audio_config.lead_silence_ms,
        trail_ms=audio_config.trail_silence_ms,
    )
    if audio_config.normalize and ffmpeg_audio_available():
        try:
            norm = out_path.with_name("voiceover_norm.wav")
            normalize_audio(raw, norm)
            if audio_config.fade_ms > 0:
                apply_fade(norm, out_path, fade_ms=audio_config.fade_ms)
            else:
                norm.replace(out_path)
            logger.info("voiceover normalized + faded")
            return out_path
        except (RenderError, BackendUnavailableError, OSError) as exc:
            logger.warning("audio post-processing skipped: %s", exc)
    raw.replace(out_path)
    return out_path


def _scene_meta(demo: Demo) -> tuple[list[str], list[bool]]:
    """Return per-chunk ``(scene_ids, kenburns_flags)`` for the animator.

    Ken Burns is applied to slide scenes and any scene using a full-frame
    background image (diagrams, screenshots, PDF pages) — never to code/terminal
    frames, where a drifting zoom would clip text.
    """
    from .schema import SceneKind

    scene_ids: list[str] = []
    kenburns: list[bool] = []
    for scene in demo.scenes:
        has_bg = bool(scene.context.get("background_image"))
        kb = has_bg or scene.kind == SceneKind.SLIDE
        for _chunk in scene.chunks:
            scene_ids.append(scene.id)
            kenburns.append(kb)
    return scene_ids, kenburns


def _typing_flags(demo: Demo) -> list[bool]:
    """Per-chunk flag: ``True`` to type a code chunk's text in character-by-character.

    A chunk types when its scene is an editor (codebase) view, it has no full-frame
    background, and it carries a ``type_code`` or ``create_file`` action.
    """
    from .schema import ActionType, SceneKind

    typing: list[bool] = []
    for scene in demo.scenes:
        is_editor = scene.kind == SceneKind.CODEBASE and not scene.context.get(
            "background_image"
        )
        for chunk in scene.chunks:
            has_type = any(
                a.type in (ActionType.TYPE_CODE, ActionType.CREATE_FILE)
                for a in chunk.actions
            )
            typing.append(is_editor and has_type)
    return typing


def render_video(
    result: PipelineResult,
    out_path: Path | None = None,
    *,
    fps: int | None = None,
    burn_captions: bool = False,
    verify: bool = True,
    animate: bool = True,
    animation_fps: int | None = None,
    config=None,
):
    """Assemble an audio-synced MP4 from a completed pipeline result.

    Frames map one-to-one to narration clips (one timeline entry per chunk), so
    each frame is held on screen for its clip's *measured* duration and the
    concatenated voiceover shares the same timebase by construction — no drift.

    With ``animate=True`` (the default), the still per-chunk frames are re-sampled
    onto a fixed ``animation_fps`` and overlaid with a moving speech waveform and a
    progress bar, producing dynamic video instead of a slideshow.

    Args:
        result: A :class:`PipelineResult` from :meth:`Pipeline.run`.
        out_path: Destination ``.mp4`` (default ``<workspace>/video/demo.mp4``).
        fps: Output frame rate (default the demo's fps; with ``animate`` the output
            is encoded at ``animation_fps``).
        burn_captions: Burn the SRT into the picture (best-effort; needs libass).
        verify: Run content-asserting verification on the result.
        animate: Render a moving waveform + progress bar at ``animation_fps``.
        animation_fps: Frame rate of the animated render.

    Returns:
        ``(out_path, report)`` where ``report`` is a
        :class:`~democreate.export.verify.VideoReport` or ``None`` if ``verify``
        is ``False``.

    Raises:
        RenderError: If the result lacks frames/clips or their counts disagree.
        BackendUnavailableError: If ffmpeg is not installed.
    """
    from .config import RenderConfig
    from .export.verify import verify_video
    from .export.video import assemble_video

    cfg = config or RenderConfig()
    demo = result.demo
    ws = result.workspace
    if not result.clips or not result.frame_paths:
        raise RenderError("result has no clips/frames; run the pipeline first")
    if len(result.frame_paths) != len(result.clips):
        raise RenderError(
            f"frame/clip count mismatch: {len(result.frame_paths)} frames vs "
            f"{len(result.clips)} clips — cannot align audio to video"
        )

    out_path = out_path or (ws.video / "demo.mp4")
    durations_ms = [clip.duration_ms for clip in result.clips]
    anim_fps = animation_fps or cfg.video.animation_fps

    with log_stage("assemble voiceover audio", logger):
        voiceover = _build_voiceover(result, ws.audio / "voiceover.wav", cfg.audio)

    if animate:
        from .assembly.animator import AnimationConfig, render_animation_frames
        from .export.video import encode_frame_sequence

        scene_ids, kenburns = _scene_meta(demo)
        typing_flags = _typing_flags(demo)
        frame_states = (
            [e.state for e in result.timeline.entries] if result.timeline else None
        )
        anim_cfg = AnimationConfig.from_video(cfg.video, cfg.theme, cfg.audio)
        anim_cfg.fps = anim_fps
        with log_stage("render animated frames", logger):
            anim_frames, _total = render_animation_frames(
                result.frame_paths,
                result.clips,
                voiceover,
                ws.frames / "anim",
                size=(demo.width, demo.height),
                config=anim_cfg,
                scene_ids=scene_ids,
                kenburns_flags=kenburns,
                frame_states=frame_states,
                typing_flags=typing_flags,
                theme=cfg.theme,
                overlay_meta=cfg.metadata,
                demo_title=cfg.metadata.title or demo.title,
            )
        with log_stage("encode animated HD video (ffmpeg)", logger):
            encode_frame_sequence(
                anim_frames, voiceover, out_path, fps=anim_fps,
                crf=cfg.video.crf, preset=cfg.video.preset,
            )
    else:
        with log_stage("assemble HD video (ffmpeg)", logger):
            srt = result.caption_paths.get("srt") if burn_captions else None
            assemble_video(
                result.frame_paths,
                durations_ms,
                voiceover,
                out_path,
                fps=fps or demo.fps,
                size=(demo.width, demo.height),
                subtitles=srt,
                crf=cfg.video.crf,
                preset=cfg.video.preset,
            )

    # Chapter markers: a YouTube chapter file plus chapters embedded in the MP4.
    # When animating, align them to the measured audio timeline (not estimates).
    with log_stage("chapters", logger):
        _embed_chapters(demo, out_path, ws, result if animate else None, cfg)

    # Provenance: container metadata tags + steganographic poster/bookend PNGs.
    with log_stage("metadata + provenance", logger):
        _embed_provenance(demo, out_path, ws, cfg)

    report = None
    if verify:
        with log_stage("verify video content", logger):
            expected_s = max(1.0, sum(durations_ms) / 1000 * 0.5)
            report = verify_video(
                out_path,
                expected_width=demo.width,
                expected_height=demo.height,
                min_duration_s=expected_s,
            )
            if not report.ok:
                logger.warning("video verification problems: %s", report.problems)
    logger.info("rendered video → %s", out_path)
    return out_path, report


def _embed_provenance(demo: Demo, out_path: Path, ws: Workspace, cfg) -> None:
    """Embed MP4 metadata tags and a steganographic provenance poster/bookends.

    Container tags are read by players/``ffprobe``. The steganographic payload —
    a signed (content-hashed) provenance record — is written into *lossless* PNG
    sidecars (a poster plus first/last "transmission bookend" frames), because LSB
    steganography does not survive an H.264 re-encode of the video pixels.
    """
    from . import __version__
    from .errors import BackendUnavailableError
    from .export.metadata import build_tags, embed_tags
    from .export.video import ffmpeg_available

    meta = cfg.metadata
    # 1. MP4 container metadata tags
    if getattr(meta, "container_tags", True):
        try:
            tags = build_tags(demo, meta, version=__version__)
            if tags and ffmpeg_available() and out_path.exists():
                tagged = out_path.with_name(out_path.stem + "_meta.mp4")
                embed_tags(out_path, tagged, tags)
                tagged.replace(out_path)
        except (RenderError, BackendUnavailableError, OSError) as exc:
            logger.warning("container metadata skipped: %s", exc)

    # 2. Steganographic provenance in lossless PNG sidecars
    if getattr(meta, "steganography", True):
        try:
            from PIL import Image

            from .export.poster import render_poster
            from .export.stego import embed_provenance

            prov_dir = ws.root / "provenance"
            prov_dir.mkdir(parents=True, exist_ok=True)
            poster = render_poster(
                demo, prov_dir / "poster.png",
                size=(demo.width, demo.height), theme=cfg.theme,
                subtitle=meta.author or None,
            )
            img = Image.open(poster).convert("RGB")
            stego, prov = embed_provenance(
                img, demo, author=meta.author, version=__version__,
                extra={"date": meta.date, "source": meta.source, "url": meta.url},
            )
            stego.save(prov_dir / "poster_signed.png", format="PNG")
            import json as _json

            (prov_dir / "provenance.json").write_text(
                _json.dumps(prov, indent=2), encoding="utf-8"
            )
        except (RenderError, OSError, ValueError) as exc:
            logger.warning("steganographic provenance skipped: %s", exc)


def _embed_chapters(demo: Demo, out_path: Path, ws: Workspace,
                    result=None, cfg=None) -> None:
    """Write a YouTube chapter file and embed chapter markers into the MP4.

    When ``result`` (with measured clips) and ``cfg`` are supplied — i.e. an
    animated render — chapter starts are computed from the real audio timeline so
    they land on the true scene transitions; otherwise they fall back to the
    estimated timeline.
    """
    from .errors import BackendUnavailableError
    from .export.chapters import embed_chapters, measured_chapters, write_chapters
    from .export.video import ffmpeg_available

    chapters = total_ms = None
    if result is not None and getattr(result, "clips", None) and cfg is not None:
        from .assembly.animator import AnimationConfig
        acfg = AnimationConfig.from_video(cfg.video, cfg.theme, cfg.audio)
        chapters, total_ms = measured_chapters(
            demo, result.clips, lead_ms=acfg.lead_ms, gap_ms=acfg.gap_ms,
            trail_ms=acfg.trail_ms)

    try:
        chap = write_chapters(demo, ws.root / "chapters",
                              chapters=chapters, total_ms=total_ms)
        if ffmpeg_available() and out_path.exists():
            chaptered = out_path.with_name(out_path.stem + "_ch.mp4")
            embed_chapters(out_path, chap["ffmetadata"], chaptered)
            chaptered.replace(out_path)
    except (RenderError, BackendUnavailableError, OSError) as exc:
        logger.warning("chapter embedding skipped: %s", exc)
