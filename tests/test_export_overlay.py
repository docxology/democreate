"""Tests for the on-screen metadata overlay bars (``democreate.export.overlay``).

These exercise real Pillow drawing against solid images and assert on actual
pixel changes in the expected bands, plus the pure ``format_clock`` formatter
and ``from_metadata_config`` field copying. No mocks; everything is deterministic.
"""

from __future__ import annotations

from PIL import Image

from democreate.config import MetadataConfig
from democreate.export.overlay import (
    OverlayInfo,
    draw_footer,
    draw_header,
    format_clock,
    from_metadata_config,
)


def _solid(size: tuple[int, int] = (640, 360)) -> Image.Image:
    """A solid mid-gray RGB frame to draw onto."""
    return Image.new("RGB", size, (40, 40, 40))


def _band_bytes(image: Image.Image, top_frac: float, bottom_frac: float) -> bytes:
    """Return the raw bytes of a horizontal band of the image, by height fraction."""
    width, height = image.size
    top = int(round(height * top_frac))
    bottom = int(round(height * bottom_frac))
    return image.crop((0, top, width, bottom)).tobytes()


# --- format_clock ---------------------------------------------------------


def test_format_clock_seconds() -> None:
    assert format_clock(0, 296_000) == "0:00 / 4:56"
    assert format_clock(83_000, 296_000) == "1:23 / 4:56"


def test_format_clock_rounds_down_and_clamps() -> None:
    # 1999 ms -> 1 second (floor); negative clamps to zero.
    assert format_clock(1_999, 5_000) == "0:01 / 0:05"
    assert format_clock(-500, 5_000) == "0:00 / 0:05"


def test_format_clock_hour_rollover() -> None:
    # Once either side reaches an hour, both render H:MM:SS with padded minutes.
    one_hour = 3_600_000
    assert format_clock(one_hour, one_hour + 90_000) == "1:00:00 / 1:01:30"
    # Current side under an hour but total over -> both still H:MM:SS.
    assert format_clock(125_000, one_hour) == "0:02:05 / 1:00:00"


# --- from_metadata_config -------------------------------------------------


def test_from_metadata_config_copies_fields() -> None:
    meta = MetadataConfig(
        author="Ada",
        title="My Demo",
        source="repo/x",
        url="https://example.com",
        watermark="(c) Ada",
        header=False,
        footer=True,
    )
    info = from_metadata_config(meta, section="Intro", clock="0:01 / 0:10")
    assert info.title == "My Demo"
    assert info.author == "Ada"
    assert info.source == "repo/x"
    assert info.url == "https://example.com"
    assert info.watermark == "(c) Ada"
    assert info.section == "Intro"
    assert info.clock == "0:01 / 0:10"


def test_from_metadata_config_title_fallback() -> None:
    meta = MetadataConfig(author="Ada")  # no title set
    info = from_metadata_config(meta, title="Fallback Title")
    assert info.title == "Fallback Title"
    # Explicit meta.title wins over passed title.
    meta2 = MetadataConfig(title="Explicit")
    assert from_metadata_config(meta2, title="Fallback").title == "Explicit"


# --- draw_header ----------------------------------------------------------


def test_draw_header_changes_top_band_preserves_size() -> None:
    image = _solid()
    before_hdr = _band_bytes(image, 0.07, 0.10)  # header ribbon band
    before_mid = _band_bytes(image, 0.40, 0.60)

    draw_header(image, OverlayInfo(title="A Tour", section="Intro"))

    assert image.size == (640, 360)
    assert image.mode == "RGB"
    assert _band_bytes(image, 0.07, 0.10) != before_hdr  # header band changed
    assert _band_bytes(image, 0.40, 0.60) == before_mid  # middle untouched


def test_draw_header_empty_is_noop() -> None:
    image = _solid()
    before = image.tobytes()
    draw_header(image, OverlayInfo())
    assert image.tobytes() == before


# --- draw_footer ----------------------------------------------------------


def test_draw_footer_changes_lower_band_preserves_size() -> None:
    image = _solid()
    before_band = _band_bytes(image, 0.96, 1.0)
    before_top = _band_bytes(image, 0.0, 0.05)

    draw_footer(
        image,
        OverlayInfo(
            author="Ada",
            source="repo/x",
            url="https://example.com",
            watermark="(c) Ada",
            clock="0:01 / 0:10",
        ),
    )

    assert image.size == (640, 360)
    assert image.mode == "RGB"
    assert _band_bytes(image, 0.96, 1.0) != before_band  # bottom band changed
    assert _band_bytes(image, 0.0, 0.05) == before_top  # top untouched


def test_draw_footer_empty_is_noop() -> None:
    image = _solid()
    before = image.tobytes()
    draw_footer(image, OverlayInfo())
    assert image.tobytes() == before


def test_draw_footer_clock_only_draws() -> None:
    image = _solid()
    before = image.tobytes()
    draw_footer(image, OverlayInfo(clock="0:05 / 1:00"))
    assert image.tobytes() != before


def test_overlay_round_trip_via_config() -> None:
    image = _solid()
    meta = MetadataConfig(author="Ada", source="repo/x", url="https://x.test")
    info = from_metadata_config(meta, title="Tour", section="Setup")
    before_hdr = _band_bytes(image, 0.07, 0.10)
    before_band = _band_bytes(image, 0.96, 1.0)

    draw_header(image, info)
    draw_footer(image, info)

    assert _band_bytes(image, 0.07, 0.10) != before_hdr
    assert _band_bytes(image, 0.96, 1.0) != before_band
