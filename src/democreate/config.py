"""Configuration and theming for DemoCreate renders.

A single :class:`RenderConfig` controls the look (theme colors, font scale), the
sound (voice, pacing, normalization), and the motion (fps, transitions, waveform,
Ken Burns) of a render. It is plain data — serializable to/from YAML — so a render
can be reproduced from one file::

    democreate render demo.json --config my_theme.yaml

Everything has a sensible default that matches the package's out-of-the-box look,
so config is purely additive: omit it and nothing changes.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, replace
from pathlib import Path
from typing import Any

__all__ = [
    "RGB", "Theme", "AudioConfig", "VideoConfig", "MetadataConfig", "RenderConfig",
    "THEMES", "ASPECTS", "RESOLUTIONS",
]

RGB = tuple[int, int, int]


@dataclass
class Theme:
    """Colors and font scale for rendered frames.

    Colors are ``(r, g, b)`` 0–255 tuples. Font ratios are fractions of the frame
    height, so text stays proportional at any resolution.
    """

    name: str = "dark"
    # surfaces
    bg_editor: RGB = (24, 27, 33)
    bg_terminal: RGB = (14, 16, 20)
    bg_browser: RGB = (248, 249, 251)
    bg_slide: RGB = (18, 21, 28)
    title_bar: RGB = (38, 42, 51)
    gutter: RGB = (31, 35, 43)
    band_bg: RGB = (12, 14, 20)
    # text
    text: RGB = (223, 227, 233)
    dim: RGB = (122, 130, 143)
    text_dark: RGB = (32, 36, 44)
    # accents
    accent: RGB = (56, 139, 253)
    section_fg: RGB = (150, 200, 255)
    prompt: RGB = (122, 224, 146)
    cursor: RGB = (240, 244, 250)
    # code highlight band
    highlight: RGB = (52, 64, 44)
    highlight_bar: RGB = (124, 214, 124)
    # caption
    caption_bg: RGB = (8, 10, 14)
    caption_fg: RGB = (245, 248, 252)
    # waveform
    wave_played: RGB = (80, 200, 255)
    wave_bar: RGB = (74, 86, 104)
    # syntax (pygments-ish)
    syn_keyword: RGB = (197, 134, 232)
    syn_string: RGB = (152, 195, 121)
    syn_comment: RGB = (110, 118, 129)
    syn_number: RGB = (224, 175, 104)
    syn_name: RGB = (122, 184, 255)
    # font scale (fraction of frame height) — larger for legibility on video
    title_ratio: float = 0.094
    subtitle_ratio: float = 0.040
    code_ratio: float = 0.030
    terminal_ratio: float = 0.032
    caption_ratio: float = 0.038
    section_ratio: float = 0.026

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Theme:
        """Build a theme from a dict, coercing color lists to tuples."""
        known = {f.name for f in fields(cls)}
        kwargs: dict[str, Any] = {}
        for key, value in data.items():
            if key not in known:
                continue
            kwargs[key] = tuple(value) if isinstance(value, list) else value
        return cls(**kwargs)


# --- preset themes --------------------------------------------------------

_LIGHT = Theme(
    name="light",
    bg_editor=(250, 250, 252),
    bg_terminal=(28, 30, 36),
    bg_slide=(244, 246, 250),
    title_bar=(228, 231, 236),
    gutter=(236, 238, 242),
    band_bg=(224, 228, 236),
    text=(28, 32, 40),
    dim=(120, 128, 140),
    accent=(37, 99, 235),
    section_fg=(37, 99, 235),
    caption_bg=(20, 24, 32),
    caption_fg=(245, 248, 252),
    highlight=(214, 232, 255),
    highlight_bar=(37, 99, 235),
    wave_played=(37, 99, 235),
    wave_bar=(178, 188, 204),
    syn_keyword=(166, 38, 164),
    syn_string=(80, 161, 79),
    syn_name=(17, 99, 196),
)

_MIDNIGHT = Theme(
    name="midnight",
    bg_editor=(13, 17, 28),
    bg_terminal=(8, 11, 20),
    bg_slide=(10, 14, 26),
    title_bar=(20, 26, 44),
    gutter=(16, 21, 36),
    band_bg=(8, 11, 22),
    accent=(124, 92, 255),
    section_fg=(170, 150, 255),
    wave_played=(150, 120, 255),
    wave_bar=(60, 66, 96),
)

# An academic look for research-paper demos: warm paper-white surfaces, dark ink,
# light code with light-background-appropriate syntax colors.
_PAPER = Theme(
    name="paper",
    bg_editor=(245, 243, 237),
    bg_slide=(247, 244, 238),
    bg_browser=(252, 250, 245),
    title_bar=(236, 231, 222),
    gutter=(238, 234, 226),
    band_bg=(232, 228, 219),
    text=(40, 37, 32),
    dim=(140, 132, 120),
    text_dark=(40, 37, 32),
    accent=(176, 96, 42),
    section_fg=(176, 96, 42),
    cursor=(60, 56, 50),
    highlight=(244, 232, 210),
    highlight_bar=(176, 96, 42),
    caption_bg=(28, 26, 22),
    caption_fg=(248, 245, 239),
    wave_played=(196, 120, 60),
    wave_bar=(190, 182, 168),
    # syntax tuned for a light background
    syn_keyword=(166, 38, 164),
    syn_string=(76, 142, 60),
    syn_comment=(150, 142, 128),
    syn_number=(176, 96, 42),
    syn_name=(20, 92, 170),
)

# NOIR — the default. Black and white carry the design; a single refined red is
# the only chroma, used sparingly for emphasis (played waveform, cursor, keywords,
# the section pill, the line-highlight bar, the top progress line).
_RED: RGB = (224, 49, 57)
_NOIR = Theme(
    name="noir",
    bg_editor=(16, 16, 18),
    bg_terminal=(10, 10, 12),
    bg_browser=(248, 248, 250),
    bg_slide=(12, 12, 14),
    title_bar=(24, 24, 28),
    gutter=(22, 22, 26),
    band_bg=(8, 8, 10),
    text=(242, 242, 244),
    dim=(146, 146, 152),
    text_dark=(20, 20, 24),
    accent=_RED,
    section_fg=(242, 242, 244),
    prompt=_RED,
    cursor=_RED,
    highlight=(40, 16, 18),
    highlight_bar=_RED,
    caption_bg=(6, 6, 8),
    caption_fg=(244, 244, 246),
    wave_played=_RED,
    wave_bar=(70, 70, 76),
    # syntax — monochrome with red keywords
    syn_keyword=(232, 72, 78),
    syn_string=(178, 178, 184),
    syn_comment=(102, 102, 108),
    syn_number=(226, 132, 96),
    syn_name=(242, 242, 244),
)

THEMES: dict[str, Theme] = {
    "noir": _NOIR,
    "dark": Theme(),
    "light": _LIGHT,
    "midnight": _MIDNIGHT,
    "paper": _PAPER,
}


@dataclass
class AudioConfig:
    """Voice and audio-assembly settings.

    Attributes:
        backend: TTS backend (``"system"``/``"silent"``/``"kokoro"``/...).
        voice: Voice id for voiced backends.
        rate_wpm: Optional speaking rate override (system voices).
        lead_silence_ms: Silence prepended to the whole voiceover.
        trail_silence_ms: Silence appended to the whole voiceover.
        gap_ms: Silence inserted between chunks (breathing room).
        normalize: Apply ffmpeg ``loudnorm`` to even out loudness.
        fade_ms: Fade-in/out applied to the final track.
    """

    backend: str = "system"
    voice: str = "Samantha"
    rate_wpm: int | None = None
    lead_silence_ms: int = 300
    trail_silence_ms: int = 600
    gap_ms: int = 220
    normalize: bool = True
    fade_ms: int = 180


@dataclass
class VideoConfig:
    """Geometry and motion settings.

    Attributes:
        width / height: Output dimensions in pixels.
        fps: Nominal demo frame rate.
        animation_fps: Frame rate of the animated render.
        animate: Render the moving waveform + progress (vs a slideshow).
        waveform: Draw the speech waveform band.
        progress_bar: Draw the top progress bar.
        transitions: Crossfade between scenes.
        transition_ms: Crossfade duration.
        ken_burns: Slow zoom on background-image scenes.
        ken_burns_zoom: Peak zoom factor for Ken Burns.
    """

    width: int = 1920
    height: int = 1080
    fps: int = 30
    animation_fps: int = 15
    animate: bool = True
    waveform: bool = True
    progress_bar: bool = True
    transitions: bool = True
    transition_ms: int = 450
    # Ken Burns (slow zoom) is OFF by default: zooming crops content off the frame
    # edges, losing information. Motion comes from typing, the waveform, and
    # crossfades instead. Enable only if you accept the edge crop.
    ken_burns: bool = False
    ken_burns_zoom: float = 1.06
    typing: bool = True
    typing_fraction: float = 0.7  # fraction of a chunk spent typing before it holds
    cursor: bool = True
    # H.264 encode quality: lower CRF = higher quality/bitrate (18 ≈ visually
    # lossless, 23 = x264 default). `preset` trades encode speed for compression.
    crf: int = 18
    preset: str = "medium"


# Named aspect-ratio presets → (width, height) at 1080-class resolution.
ASPECTS: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:3": (1440, 1080),
    "4:5": (1080, 1350),
}

# Named 16:9 resolution tiers → (width, height). Every visual element scales with
# the frame height, so a higher tier is genuinely higher resolution, not upscaled.
RESOLUTIONS: dict[str, tuple[int, int]] = {
    "720p": (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "2160p": (3840, 2160),
    "4k": (3840, 2160),
}


@dataclass
class MetadataConfig:
    """Provenance/metadata shown on screen, written to the container, and hidden.

    The same fields drive three carriers: visible top/bottom overlay bars, MP4
    container tags (read by players/``ffprobe``), and a steganographic payload
    embedded in lossless poster/bookend PNGs.

    Attributes:
        author: Creator name (footer + container ``artist``).
        title: Overrides the demo title in overlays/tags when set.
        date: Date string (footer + container ``date``).
        source: Source label — repo, paper, or project (footer).
        url: A URL shown in the footer.
        watermark: Small persistent watermark text (footer-right).
        header: Draw a top metadata bar (title · section).
        footer: Draw a bottom metadata bar (author · source · url · clock).
        show_clock: Show a running time readout in the footer.
        container_tags: Write MP4 metadata tags via ffmpeg.
        steganography: Embed a signed provenance payload in lossless PNG sidecars.
    """

    author: str = ""
    title: str = ""
    date: str = ""
    source: str = ""
    url: str = ""
    watermark: str = ""
    header: bool = False
    footer: bool = True
    show_clock: bool = True
    container_tags: bool = True
    steganography: bool = True


@dataclass
class RenderConfig:
    """Top-level render configuration: theme + audio + video + metadata."""

    theme: Theme = field(default_factory=lambda: replace(_NOIR))
    audio: AudioConfig = field(default_factory=AudioConfig)
    video: VideoConfig = field(default_factory=VideoConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)

    @classmethod
    def preset(cls, theme_name: str = "noir") -> RenderConfig:
        """Return a config using a named preset theme (default ``"noir"``)."""
        theme = THEMES.get(theme_name, _NOIR)
        return cls(theme=replace(theme))

    def set_aspect(self, name: str) -> RenderConfig:
        """Set ``video.width``/``video.height`` from a named aspect preset.

        Args:
            name: One of :data:`ASPECTS` (e.g. ``"16:9"``, ``"9:16"``, ``"1:1"``).

        Returns:
            ``self`` (for chaining). Unknown names are ignored.
        """
        if name in ASPECTS:
            self.video.width, self.video.height = ASPECTS[name]
        return self

    def set_resolution(self, name: str) -> RenderConfig:
        """Set 16:9 ``video.width``/``video.height`` from a resolution tier.

        Args:
            name: One of :data:`RESOLUTIONS` (``"720p"``/``"1080p"``/``"1440p"``/
                ``"2160p"``/``"4k"``).

        Returns:
            ``self``. Unknown names are ignored.
        """
        if name in RESOLUTIONS:
            self.video.width, self.video.height = RESOLUTIONS[name]
        return self

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (colors stay as lists for YAML cleanliness)."""
        return {
            "theme": asdict(self.theme),
            "audio": asdict(self.audio),
            "video": asdict(self.video),
            "metadata": asdict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RenderConfig:
        """Build a config from a (possibly partial) dict."""
        theme_data = data.get("theme", {})
        if isinstance(theme_data, str):
            theme = replace(THEMES.get(theme_data, _NOIR))
        else:
            base = THEMES.get(theme_data.get("name", "noir"), _NOIR)
            merged = {**asdict(base), **theme_data}
            theme = Theme.from_dict(merged)
        # Filter unknown keys (like Theme.from_dict) so a config carrying a future
        # or mistyped field degrades gracefully instead of raising TypeError.
        def _sub(klass, key):
            known = {f.name for f in fields(klass)}
            given = {k: v for k, v in (data.get(key) or {}).items() if k in known}
            return klass(**{**asdict(klass()), **given})

        audio = _sub(AudioConfig, "audio")
        video = _sub(VideoConfig, "video")
        meta = _sub(MetadataConfig, "metadata")
        return cls(theme=theme, audio=audio, video=video, metadata=meta)

    @classmethod
    def commented_yaml(cls, theme_name: str = "noir") -> str:
        """Return a fully-commented default config YAML (for ``democreate config``).

        This is the most accessible control surface: every commonly-tuned knob with
        an inline comment, ready to edit and pass to ``--config``.
        """
        cfg = cls.preset(theme_name)
        _presets = " | ".join(THEMES)  # derived so it can't drift from THEMES
        lines = [
            "# DemoCreate render configuration. Pass with: democreate render --config this.yaml",
            "# Every field is optional; omitted fields fall back to the defaults below.",
            "",
            f'theme: {theme_name}            # preset: {_presets}',
            "",
            "video:",
            f"  width: {cfg.video.width}              # frame width in pixels",
            f"  height: {cfg.video.height}             # frame height (everything scales to this)",
            "  # resolution tiers (16:9): 720p 1280x720 · 1080p 1920x1080 · 1440p 2560x1440 · 2160p/4k 3840x2160",
            f"  fps: {cfg.video.fps}                  # demo frame rate",
            f"  animation_fps: {cfg.video.animation_fps}        # animated render frame rate (motion smoothness)",
            f"  crf: {cfg.video.crf}                  # H.264 quality: 18 ~ visually lossless, 23 = default, lower = crisper",
            f"  preset: {cfg.video.preset}           # x264 speed/size tradeoff: ultrafast..veryslow",
            f"  waveform: {str(cfg.video.waveform).lower()}          # draw the speech waveform band",
            f"  progress_bar: {str(cfg.video.progress_bar).lower()}      # draw the top progress bar",
            f"  transitions: {str(cfg.video.transitions).lower()}       # crossfade between scenes",
            f"  ken_burns: {str(cfg.video.ken_burns).lower()}        # slow zoom on slides (OFF: zoom crops content off the edges)",
            f"  typing: {str(cfg.video.typing).lower()}            # type code in character-by-character",
            f"  cursor: {str(cfg.video.cursor).lower()}            # animated cursor + click ripples",
            "",
            "audio:",
            f"  backend: {cfg.audio.backend}        # system (real OS voice) | silent | kokoro | chatterbox",
            f"  voice: {cfg.audio.voice}         # system voice name (macOS: say -v '?')",
            f"  lead_silence_ms: {cfg.audio.lead_silence_ms}     # pause before the first word",
            f"  gap_ms: {cfg.audio.gap_ms}             # pause between chunks",
            f"  trail_silence_ms: {cfg.audio.trail_silence_ms}    # pause after the last word",
            f"  normalize: {str(cfg.audio.normalize).lower()}        # EBU R128 loudness normalization (ffmpeg)",
            "",
            "metadata:",
            '  author: ""             # creator name → footer bar + MP4 artist tag + provenance',
            '  source: ""             # repo / paper / project label → footer',
            '  url: ""                # link shown in the footer',
            '  watermark: ""          # small persistent watermark text',
            f"  header: {str(cfg.metadata.header).lower()}          # top metadata bar (title · section)",
            f"  footer: {str(cfg.metadata.footer).lower()}           # bottom metadata bar (author · source · clock)",
            f"  container_tags: {str(cfg.metadata.container_tags).lower()}   # embed MP4 metadata tags",
            f"  steganography: {str(cfg.metadata.steganography).lower()}    # hide signed provenance in poster/bookend PNGs",
            "",
        ]
        return "\n".join(lines)

    def to_yaml(self) -> str:
        """Serialize the config to YAML."""
        import yaml

        return yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, text: str) -> RenderConfig:
        """Parse a config from YAML text."""
        import yaml

        return cls.from_dict(yaml.safe_load(text) or {})

    @classmethod
    def from_file(cls, path: Path | str) -> RenderConfig:
        """Load a config from a YAML file."""
        return cls.from_yaml(Path(path).read_text(encoding="utf-8"))
