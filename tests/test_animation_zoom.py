"""Tests for democreate.animation.zoom (pure math + PIL)."""

from __future__ import annotations

import pytest

from democreate.animation.zoom import (
    ZoomKeyframe,
    apply_zoom,
    compute_zoom_path,
    ease_in_out_cubic,
    ease_in_out_quad,
    interpolate,
    linear,
)

# --- easing -----------------------------------------------------------------


@pytest.mark.parametrize("fn", [linear, ease_in_out_quad, ease_in_out_cubic])
def test_easing_endpoints(fn) -> None:
    assert fn(0.0) == pytest.approx(0.0)
    assert fn(1.0) == pytest.approx(1.0)


@pytest.mark.parametrize("fn", [linear, ease_in_out_quad, ease_in_out_cubic])
def test_easing_clamps(fn) -> None:
    assert fn(-5.0) == pytest.approx(0.0)
    assert fn(5.0) == pytest.approx(1.0)


@pytest.mark.parametrize("fn", [ease_in_out_quad, ease_in_out_cubic])
def test_easing_midpoint(fn) -> None:
    assert fn(0.5) == pytest.approx(0.5)


def test_linear_is_identity() -> None:
    assert linear(0.3) == pytest.approx(0.3)


@pytest.mark.parametrize("fn", [linear, ease_in_out_quad, ease_in_out_cubic])
def test_easing_monotonic(fn) -> None:
    vals = [fn(i / 20) for i in range(21)]
    assert all(b >= a - 1e-9 for a, b in zip(vals, vals[1:], strict=False))


# --- compute_zoom_path ------------------------------------------------------


def test_compute_zoom_path_monotonic_timestamps() -> None:
    pts = [(0, 100, 100), (1000, 200, 200), (500, 150, 150)]
    kfs = compute_zoom_path(pts, (1280, 720))
    times = [k.t_ms for k in kfs]
    assert times == sorted(times)


def test_compute_zoom_path_scale_at_least_one() -> None:
    pts = [(0, 100, 100), (1000, 200, 200)]
    kfs = compute_zoom_path(pts, (1280, 720), zoom=1.6)
    assert all(k.scale >= 1.0 for k in kfs)
    assert any(k.scale == pytest.approx(1.6) for k in kfs)


def test_compute_zoom_path_empty_points() -> None:
    kfs = compute_zoom_path([], (1280, 720))
    assert len(kfs) == 1
    assert kfs[0].scale == pytest.approx(1.0)
    assert kfs[0].center_x == pytest.approx(640.0)
    assert kfs[0].center_y == pytest.approx(360.0)


def test_compute_zoom_path_centers_on_cursor() -> None:
    kfs = compute_zoom_path([(500, 300, 400)], (1280, 720), zoom=2.0)
    zoomed = [k for k in kfs if k.scale > 1.0]
    assert zoomed
    assert all(k.center_x == pytest.approx(300.0) for k in zoomed)
    assert all(k.center_y == pytest.approx(400.0) for k in zoomed)


def test_compute_zoom_path_dedup_timestamps() -> None:
    pts = [(100, 10, 10), (100, 50, 60)]
    kfs = compute_zoom_path(pts, (1280, 720), zoom=1.5)
    zoomed = [k for k in kfs if k.scale > 1.0]
    # Last write wins for a duplicate timestamp.
    assert all(k.center_x == pytest.approx(50.0) for k in zoomed)


def test_compute_zoom_path_starts_and_ends_zoomed_out() -> None:
    kfs = compute_zoom_path([(500, 100, 100)], (1280, 720))
    assert kfs[0].scale == pytest.approx(1.0)
    assert kfs[-1].scale == pytest.approx(1.0)


def test_compute_zoom_path_invalid_zoom() -> None:
    with pytest.raises(ValueError):
        compute_zoom_path([(0, 1, 1)], (100, 100), zoom=0.5)


def test_compute_zoom_path_invalid_hold() -> None:
    with pytest.raises(ValueError):
        compute_zoom_path([(0, 1, 1)], (100, 100), hold_ms=-1)


# --- interpolate ------------------------------------------------------------


def test_interpolate_endpoints_exact() -> None:
    kfs = [
        ZoomKeyframe(0, 0.0, 0.0, 1.0),
        ZoomKeyframe(1000, 100.0, 200.0, 2.0),
    ]
    lo = interpolate(kfs, 0)
    hi = interpolate(kfs, 1000)
    assert lo.scale == pytest.approx(1.0)
    assert lo.center_x == pytest.approx(0.0)
    assert hi.scale == pytest.approx(2.0)
    assert hi.center_x == pytest.approx(100.0)
    assert hi.center_y == pytest.approx(200.0)


def test_interpolate_clamps_before_and_after() -> None:
    kfs = [
        ZoomKeyframe(100, 10.0, 10.0, 1.0),
        ZoomKeyframe(200, 20.0, 20.0, 2.0),
    ]
    before = interpolate(kfs, -50)
    after = interpolate(kfs, 9999)
    assert before.scale == pytest.approx(1.0)
    assert before.center_x == pytest.approx(10.0)
    assert after.scale == pytest.approx(2.0)
    assert after.center_x == pytest.approx(20.0)


def test_interpolate_midpoint_linear() -> None:
    kfs = [
        ZoomKeyframe(0, 0.0, 0.0, 1.0),
        ZoomKeyframe(1000, 100.0, 100.0, 3.0),
    ]
    mid = interpolate(kfs, 500, easing=linear)
    assert mid.scale == pytest.approx(2.0)
    assert mid.center_x == pytest.approx(50.0)


def test_interpolate_uses_easing() -> None:
    kfs = [
        ZoomKeyframe(0, 0.0, 0.0, 1.0),
        ZoomKeyframe(1000, 0.0, 0.0, 3.0),
    ]
    lin = interpolate(kfs, 250, easing=linear).scale
    cub = interpolate(kfs, 250, easing=ease_in_out_cubic).scale
    assert lin != pytest.approx(cub)


def test_interpolate_zero_span_segment() -> None:
    # Two keyframes at the same time should not divide by zero.
    kfs = [
        ZoomKeyframe(0, 0.0, 0.0, 1.0),
        ZoomKeyframe(0, 50.0, 50.0, 2.0),
        ZoomKeyframe(100, 80.0, 80.0, 2.0),
    ]
    out = interpolate(kfs, 0)
    assert out.scale == pytest.approx(1.0)


def test_interpolate_empty_raises() -> None:
    with pytest.raises(ValueError):
        interpolate([], 0)


def test_interpolate_unsorted_input() -> None:
    kfs = [
        ZoomKeyframe(1000, 100.0, 100.0, 2.0),
        ZoomKeyframe(0, 0.0, 0.0, 1.0),
    ]
    mid = interpolate(kfs, 500, easing=linear)
    assert mid.scale == pytest.approx(1.5)


# --- apply_zoom -------------------------------------------------------------


def _solid_image(size=(200, 100)):
    from PIL import Image

    return Image.new("RGB", size, (10, 20, 30))


def test_apply_zoom_preserves_size() -> None:
    img = _solid_image((320, 180))
    out = apply_zoom(img, ZoomKeyframe(0, 160.0, 90.0, 2.0))
    assert out.size == (320, 180)


def test_apply_zoom_scale_one_is_identity_size() -> None:
    img = _solid_image((256, 128))
    out = apply_zoom(img, ZoomKeyframe(0, 128.0, 64.0, 1.0))
    assert out.size == (256, 128)


def test_apply_zoom_scale_below_one_identity() -> None:
    img = _solid_image((100, 100))
    out = apply_zoom(img, ZoomKeyframe(0, 50.0, 50.0, 0.5))
    assert out.size == (100, 100)


def test_apply_zoom_solid_color_preserved() -> None:
    # Zooming into a solid color image yields the same solid color.
    img = _solid_image((200, 200))
    out = apply_zoom(img, ZoomKeyframe(0, 100.0, 100.0, 2.0))
    colors = {c for _, c in (out.getcolors(maxcolors=1 << 20) or [])}
    assert colors == {(10, 20, 30)}


def test_apply_zoom_clamps_center_at_edge() -> None:
    # A center beyond the frame must still produce a valid same-size image.
    img = _solid_image((200, 100))
    out = apply_zoom(img, ZoomKeyframe(0, 9999.0, 9999.0, 2.0))
    assert out.size == (200, 100)


def test_apply_zoom_returns_new_image() -> None:
    img = _solid_image((64, 64))
    out = apply_zoom(img, ZoomKeyframe(0, 32.0, 32.0, 1.0))
    assert out is not img
