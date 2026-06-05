"""Capture subsystem — synthetic + real frame, terminal, browser, and input.

This package renders the visual side of a demo. Its guiding rule is the
deterministic-default principle: every heavy capability has a pure-Python default
that works with only the core dependencies, and each real backend is guarded
behind an optional extra.

Modules:
    screen: :class:`SyntheticRenderer` (default) draws editor/terminal/browser/
        slide frames with Pillow; :class:`MssScreenCapture` grabs real pixels
        (extra ``capture``).
    terminal: asciinema asciicast v2 recordings, pure Python.
    browser: :class:`NullBrowserDriver` (default) records calls and renders
        synthetic frames; :class:`PlaywrightBrowserDriver` drives a real browser
        (extra ``browser``).
    replay: a pure input-event model with guarded ``pynput``/``pyautogui``
        record/replay (extra ``replay``).
"""

from __future__ import annotations

from .browser import (
    BrowserDriver,
    NullBrowserDriver,
    PlaywrightBrowserDriver,
    drive_website_scene,
)
from .replay import EventLog, InputEvent, record_session, replay_session
from .screen import (
    FrameSource,
    MssScreenCapture,
    SyntheticRenderer,
    render_demo_thumbnail,
    render_frame,
)
from .terminal import (
    AsciicastEvent,
    AsciicastRecording,
    record_commands,
    recording_to_frame_states,
)

__all__ = [
    # screen
    "FrameSource",
    "SyntheticRenderer",
    "MssScreenCapture",
    "render_frame",
    "render_demo_thumbnail",
    # terminal
    "AsciicastEvent",
    "AsciicastRecording",
    "record_commands",
    "recording_to_frame_states",
    # browser
    "BrowserDriver",
    "NullBrowserDriver",
    "PlaywrightBrowserDriver",
    "drive_website_scene",
    # replay
    "InputEvent",
    "EventLog",
    "record_session",
    "replay_session",
]
