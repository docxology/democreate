"""Tests for the DemoCreate config and theme system.

Real computation only: every test exercises :mod:`democreate.config` directly,
round-tripping plain data through dicts, YAML strings, and temp files. No mocks.
"""

from __future__ import annotations

from pathlib import Path

from democreate.config import (
    THEMES,
    AudioConfig,
    RenderConfig,
    Theme,
    VideoConfig,
)


def test_render_config_defaults() -> None:
    """A bare RenderConfig uses the default dark theme and default sub-configs."""
    config = RenderConfig()

    assert isinstance(config.theme, Theme)
    assert isinstance(config.audio, AudioConfig)
    assert isinstance(config.video, VideoConfig)
    assert config.theme.name == "noir"


def test_preset_selects_theme() -> None:
    """RenderConfig.preset selects the theme whose name matches the preset key."""
    for name in ("noir", "paper", "light", "midnight", "dark"):
        config = RenderConfig.preset(name)
        assert config.theme.name == name


def test_preset_unknown_falls_back_to_default_theme() -> None:
    """An unknown preset name falls back to the default noir Theme."""
    config = RenderConfig.preset("does-not-exist")

    assert config.theme.name == "noir"


def test_to_dict_from_dict_round_trip() -> None:
    """to_dict -> from_dict reproduces theme, audio, and video data."""
    original = RenderConfig.preset("midnight")
    data = original.to_dict()

    assert isinstance(data, dict)
    assert set(data) == {"theme", "audio", "video", "metadata"}

    restored = RenderConfig.from_dict(data)

    assert restored.theme == original.theme
    assert restored.audio == original.audio
    assert restored.video == original.video
    assert restored.theme.name == "midnight"


def test_to_yaml_from_yaml_round_trip() -> None:
    """to_yaml -> from_yaml preserves theme name, audio.voice, and video.fps."""
    original = RenderConfig.preset("paper")
    original.audio.voice = "Alex"
    original.video.fps = 24

    text = original.to_yaml()
    assert isinstance(text, str)

    restored = RenderConfig.from_yaml(text)

    assert restored.theme.name == "paper"
    assert restored.audio.voice == "Alex"
    assert restored.video.fps == 24


def test_yaml_round_trip_preserves_color_tuples() -> None:
    """Colors survive a YAML round-trip and come back as tuples, not lists."""
    original = RenderConfig.preset("light")
    restored = RenderConfig.from_yaml(original.to_yaml())

    assert restored.theme.accent == original.theme.accent
    assert isinstance(restored.theme.accent, tuple)


def test_from_dict_partial_theme_merges_onto_base() -> None:
    """A partial theme dict merges onto the named base and coerces lists to tuples."""
    base = THEMES["dark"]
    config = RenderConfig.from_dict(
        {"theme": {"name": "dark", "accent": [1, 2, 3]}}
    )

    # Overridden field is coerced to a tuple.
    assert config.theme.accent == (1, 2, 3)
    assert isinstance(config.theme.accent, tuple)
    # Non-overridden fields are inherited from the base theme.
    assert config.theme.bg_editor == base.bg_editor
    assert config.theme.text == base.text
    assert config.theme.name == "dark"


def test_from_dict_theme_as_bare_string_selects_preset() -> None:
    """A theme given as a bare string selects the matching preset theme."""
    config = RenderConfig.from_dict({"theme": "paper"})

    assert config.theme == THEMES["paper"]
    assert config.theme.name == "paper"


def test_from_dict_theme_bare_string_unknown_falls_back() -> None:
    """An unknown bare-string theme falls back to the default noir Theme."""
    config = RenderConfig.from_dict({"theme": "nonexistent"})

    assert config.theme.name == "noir"


def test_theme_from_dict_ignores_unknown_keys() -> None:
    """Theme.from_dict drops keys that are not real Theme fields."""
    theme = Theme.from_dict(
        {"name": "custom", "accent": [10, 20, 30], "bogus_key": "ignored"}
    )

    assert theme.name == "custom"
    assert theme.accent == (10, 20, 30)
    assert not hasattr(theme, "bogus_key")


def test_themes_contains_the_named_presets() -> None:
    """THEMES holds exactly the named presets, each with a matching name."""
    assert set(THEMES) == {"noir", "dark", "light", "midnight", "paper"}
    for name, theme in THEMES.items():
        assert isinstance(theme, Theme)
        assert theme.name == name


def test_audio_config_defaults_are_sane() -> None:
    """AudioConfig defaults match the documented out-of-the-box voice settings."""
    audio = AudioConfig()

    assert audio.backend == "system"
    assert audio.voice == ""
    assert audio.rate_wpm is None
    assert audio.normalize is True
    assert audio.lead_silence_ms == 300
    assert audio.gap_ms == 220


def test_video_config_defaults_are_sane() -> None:
    """VideoConfig defaults match the documented HD geometry and motion settings."""
    video = VideoConfig()

    assert video.width == 1920
    assert video.height == 1080
    assert video.fps == 30
    assert video.animate is True
    assert video.waveform is True


def test_from_file_reads_yaml(tmp_path: Path) -> None:
    """from_file loads and parses a YAML config written to a real temp file."""
    original = RenderConfig.preset("midnight")
    original.audio.voice = "Daniel"
    original.video.fps = 60

    path = tmp_path / "config.yaml"
    path.write_text(original.to_yaml(), encoding="utf-8")

    loaded = RenderConfig.from_file(path)

    assert loaded.theme.name == "midnight"
    assert loaded.audio.voice == "Daniel"
    assert loaded.video.fps == 60


def test_from_file_accepts_str_path(tmp_path: Path) -> None:
    """from_file accepts a string path as well as a Path."""
    path = tmp_path / "cfg.yaml"
    path.write_text(RenderConfig.preset("light").to_yaml(), encoding="utf-8")

    loaded = RenderConfig.from_file(str(path))

    assert loaded.theme.name == "light"


def test_from_yaml_empty_text_uses_defaults() -> None:
    """Empty YAML parses to a default config (safe_load returns None)."""
    config = RenderConfig.from_yaml("")

    assert config.theme.name == "noir"
    assert config.audio.voice == ""
    assert config.video.width == 1920
