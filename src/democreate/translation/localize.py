"""Render a demo with audio in one language and subtitles in another.

Thin orchestration over :mod:`democreate.pipeline` and the translation helpers:

1. translate the narration to the **audio** language (if different) and synthesize
   it — this drives the audio, the frames, and the timing;
2. emit a **subtitle** track translated to the subtitle language against that same
   (audio-derived) timing, so the two languages stay in lock-step;
3. write the MP4 with a filename that makes both languages explicit, e.g.
   ``demo-audio_en-subs_ru.mp4``.

The deterministic default translator is a no-op, so with it this simply renders the
source language for both surfaces. A real ``ollama`` translator localizes for real.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .._logging import get_logger
from ..schema import Demo
from .translator import (
    LanguageConfig,
    Translator,
    get_translator,
    localized_captions,
    translate_demo,
)

__all__ = ["LocalizedResult", "localize_render", "localize_batch", "KOKORO_AUDIO_LANGS"]

logger = get_logger(__name__)

# Audio-language code → (Kokoro lang code, a default voice for it). Kokoro can
# *speak* these; subtitles work for any language regardless. Unknown audio
# languages fall back to English (and need an explicit, suitable voice).
KOKORO_AUDIO_LANGS: dict[str, tuple[str, str]] = {
    "en": ("en-us", "af_heart"),
    "es": ("es", "ef_dora"),
    "fr": ("fr-fr", "ff_siwis"),
    "it": ("it", "if_sara"),
    "pt": ("pt-br", "pf_dora"),
    "ja": ("ja", "jf_alpha"),
    "zh": ("zh", "zf_xiaobei"),
    "hi": ("hi", "hf_alpha"),
}


@dataclass
class LocalizedResult:
    """One localized render (one audio/subtitle language pair).

    Attributes:
        languages: The :class:`LanguageConfig` used.
        video_path: The produced MP4 (``None`` on failure).
        subtitle_srt / subtitle_vtt: Subtitle sidecar files in the subtitle language.
        duration_s: Verified duration (``0`` when unverified/failed).
        ok: Whether content verification passed.
        error: Error message on failure.
    """

    languages: LanguageConfig
    video_path: Path | None = None
    subtitle_srt: Path | None = None
    subtitle_vtt: Path | None = None
    duration_s: float = 0.0
    ok: bool = False
    error: str = ""

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-ready dict."""
        return {
            "source": self.languages.source,
            "audio": self.languages.audio,
            "subtitle": self.languages.subtitle,
            "video_path": str(self.video_path) if self.video_path else None,
            "subtitle_srt": str(self.subtitle_srt) if self.subtitle_srt else None,
            "duration_s": round(self.duration_s, 2),
            "ok": self.ok,
            "error": self.error,
        }


def localize_render(
    demo: Demo,
    workspace,
    *,
    languages: LanguageConfig,
    translator: Translator | None = None,
    config=None,
    tts: str = "system",
    voice: str = "",
    burn: bool = False,
    verify: bool = True,
    name: str | None = None,
) -> LocalizedResult:
    """Render one audio/subtitle language pair; return a :class:`LocalizedResult`.

    Args:
        demo: The source demo.
        workspace: A :class:`~democreate.project_paths.Workspace`.
        languages: Which languages for audio and subtitles.
        translator: Translator to use (default: the no-op :class:`IdentityTranslator`).
        config: Optional :class:`~democreate.config.RenderConfig`.
        tts: TTS backend for the audio language (``system``/``kokoro``/``silent``).
        voice: Voice id for the audio language (must suit ``languages.audio``).
        burn: Burn the subtitle-language track into the picture.
        verify: Content-verify the produced MP4.
        name: Base filename stem (default: the demo title slug).
    """
    from ..config import RenderConfig
    from ..narration.tts import get_tts_backend
    from ..pipeline import Pipeline, render_video

    cfg = config or RenderConfig()
    tr = translator or get_translator("identity")
    stem = name or _slug(demo.title)
    tag = languages.tag()

    # 1. Audio-language demo drives synthesis, frames, and timing.
    audio_demo = translate_demo(
        demo, tr, source=languages.source, target=languages.audio
    )
    # Pick a Kokoro language code + a default voice for the audio language so
    # non-English audio is phonemized correctly (an explicit ``voice`` wins).
    klang, default_voice = KOKORO_AUDIO_LANGS.get(languages.audio, ("en-us", "af_heart"))
    use_voice = (voice or default_voice) if tts != "silent" else None
    backend = get_tts_backend(tts, voice=use_voice, lang=klang)
    result = Pipeline(tts_backend=backend, strict=False, config=cfg).run(
        audio_demo, workspace
    )

    # 2. Subtitle-language track: translated from the ORIGINAL (source) text, timed
    #    by the audio-language demo — never from the (already-translated) audio demo.
    srt = localized_captions(
        demo, tr, source=languages.source, target=languages.subtitle,
        fmt="srt", timing_demo=audio_demo,
    )
    vtt = localized_captions(
        demo, tr, source=languages.source, target=languages.subtitle,
        fmt="vtt", timing_demo=audio_demo,
    )
    # Name sidecars with the FULL audio+subtitle tag (matching the video): the
    # subtitle timing is derived from the audio, so two renders sharing a subtitle
    # language but differing in audio (e.g. en/ru vs ru/ru) must not collide.
    srt_path = Path(workspace.captions) / f"{stem}-{tag}.srt"
    vtt_path = Path(workspace.captions) / f"{stem}-{tag}.vtt"
    srt_path.write_text(srt, encoding="utf-8")
    vtt_path.write_text(vtt, encoding="utf-8")

    # 3. Render; when burning, burn the subtitle-language track (not the audio one).
    if burn:
        result.caption_paths["srt"] = srt_path
    out_path = Path(workspace.video) / f"{stem}-{tag}.mp4"
    _out, report = render_video(
        result, out_path=out_path, burn_captions=burn, verify=verify, config=cfg
    )
    ok = bool(report.ok) if report is not None else out_path.exists()
    duration = float(report.duration_s) if report is not None else 0.0
    logger.info(
        "localized render %s → audio=%s subs=%s ok=%s",
        stem, languages.audio, languages.subtitle, ok,
    )
    return LocalizedResult(
        languages=languages,
        video_path=out_path,
        subtitle_srt=srt_path,
        subtitle_vtt=vtt_path,
        duration_s=duration,
        ok=ok,
    )


def localize_batch(
    demo: Demo,
    workspace,
    *,
    pairs: list[tuple[str, str]],
    source: str = "en",
    translator: Translator | None = None,
    config=None,
    tts: str = "system",
    voice: str = "",
    burn: bool = False,
    verify: bool = True,
    name: str | None = None,
) -> list[LocalizedResult]:
    """Render one localized video per ``(audio_lang, subtitle_lang)`` pair.

    A pair that fails to render is recorded as ``ok=False`` and the batch
    continues. Returns one :class:`LocalizedResult` per pair.
    """
    results: list[LocalizedResult] = []
    for audio_lang, subtitle_lang in pairs:
        languages = LanguageConfig(source=source, audio=audio_lang, subtitle=subtitle_lang)
        try:
            results.append(
                localize_render(
                    demo, workspace, languages=languages, translator=translator,
                    config=config, tts=tts, voice=voice, burn=burn, verify=verify,
                    name=name,
                )
            )
        except Exception as exc:  # noqa: BLE001 - one pair must not abort the batch
            logger.warning("localized pair %s/%s failed: %s", audio_lang, subtitle_lang, exc)
            results.append(
                LocalizedResult(languages=languages, error=str(exc))
            )
    return results


def _slug(title: str) -> str:
    """A filesystem-safe stem from a demo title."""
    out = "".join(c if c.isalnum() else "-" for c in title.lower())
    return "-".join(p for p in out.split("-") if p) or "demo"
