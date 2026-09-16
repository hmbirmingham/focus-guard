import sys
from collections import namedtuple
from pathlib import Path
from unittest.mock import patch

import pytest
from pynput import keyboard

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from camera_monitor import eye_aspect_ratio, BLINK_EAR_THRESHOLD
from keyboard_monitor import KeyboardMonitor

FakeLandmark = namedtuple("FakeLandmark", ["x", "y"])


def _landmarks(points):
    """points: 6 (x, y) pairs, normalized 0-1, in the [corner, top1, top2,
    corner, bottom2, bottom1] order eye_aspect_ratio expects."""
    return [FakeLandmark(x, y) for x, y in points]


def test_eye_aspect_ratio_open_eye():
    open_eye = _landmarks([
        (0.00, 0.5), (0.25, 0.3), (0.75, 0.3),
        (1.00, 0.5), (0.75, 0.7), (0.25, 0.7),
    ])
    ear = eye_aspect_ratio(open_eye, range(6), w=100, h=100)
    assert ear == pytest.approx(0.4, abs=1e-4)
    assert ear > BLINK_EAR_THRESHOLD


def test_eye_aspect_ratio_closed_eye():
    closed_eye = _landmarks([
        (0.00, 0.5), (0.25, 0.45), (0.75, 0.45),
        (1.00, 0.5), (0.75, 0.55), (0.25, 0.55),
    ])
    ear = eye_aspect_ratio(closed_eye, range(6), w=100, h=100)
    assert ear == pytest.approx(0.1, abs=1e-4)
    assert ear < BLINK_EAR_THRESHOLD


def test_keyboard_monitor_error_rate():
    km = KeyboardMonitor()
    for _ in range(8):
        km._on_press(keyboard.KeyCode.from_char("a"))
    for _ in range(2):
        km._on_press(keyboard.Key.backspace)

    stats = km.get_stats()
    assert stats["error_rate"] == 20.0


def test_keyboard_monitor_pause_tracking():
    km = KeyboardMonitor()
    # Three keystrokes: a 3s gap (counts as a pause), then a sub-threshold gap.
    fake_times = iter([100.0, 103.0, 103.5])
    with patch("keyboard_monitor.time.time", side_effect=lambda: next(fake_times)):
        km._on_press(keyboard.KeyCode.from_char("a"))
        km._on_press(keyboard.KeyCode.from_char("b"))
        km._on_press(keyboard.KeyCode.from_char("c"))

    stats = km.get_stats()
    assert stats["avg_pause_secs"] == 3.0
