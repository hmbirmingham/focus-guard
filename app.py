#!/usr/bin/env python3
"""
FocusGuard — macOS menu bar app (PyObjC native status bar).

Run:  python3 app.py
"""

import threading
import webbrowser
import sys

# ── Flask dashboard ─────────────────────────────────────────────────────────
from flask import Flask, jsonify, send_from_directory
from camera_monitor   import CameraMonitor
from keyboard_monitor import KeyboardMonitor
from detector         import assess, BLINK_NORMAL_MIN, BLINK_NORMAL_MAX, \
                             EAR_DROWSY, ERROR_STRESS_PCT, PAUSE_FATIGUE_S, BREAK_THRESHOLD
from notifier         import Notifier

flask_app = Flask(__name__, static_folder="ui", static_url_path="")
_camera   = CameraMonitor()
_kb       = KeyboardMonitor()
_notifier = Notifier()
DASHBOARD_PORT = 5001


@flask_app.route("/")
def index():
    return send_from_directory("ui", "index.html")


@flask_app.route("/api/status")
def api_status():
    cam    = _camera.get_stats()
    kbd    = _kb.get_stats()
    result = assess(cam, kbd)
    return jsonify({
        "camera":   cam,
        "keyboard": kbd,
        "thresholds": {
            "blink_normal_min":  BLINK_NORMAL_MIN,
            "blink_normal_max":  BLINK_NORMAL_MAX,
            "ear_drowsy":        EAR_DROWSY,
            "error_stress_pct":  ERROR_STRESS_PCT,
            "pause_fatigue_s":   PAUSE_FATIGUE_S,
            "break_threshold":   BREAK_THRESHOLD,
        },
        "assessment": {
            "fatigue":        result.fatigue_score,
            "stress":         result.stress_score,
            "combined":       result.combined,
            "reasons":        result.reasons,
            "recommend_break": result.recommend_break,
        },
    })


def _run_flask():
    import logging
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    flask_app.run(host="127.0.0.1", port=DASHBOARD_PORT, debug=False, use_reloader=False)


# ── PyObjC status bar ────────────────────────────────────────────────────────
import objc
from AppKit import (
    NSApplication, NSStatusBar, NSMenu, NSMenuItem,
    NSObject, NSVariableStatusItemLength,
    NSApplicationActivationPolicyAccessory,
)
from Foundation import NSTimer

POLL_INTERVAL = 10.0  # seconds


def _score_icon(v: float) -> str:
    if v < 30: return "🟢"
    if v < 60: return "🟡"
    return "🔴"


class AppDelegate(NSObject):
    def applicationDidFinishLaunching_(self, _notif):
        # Status item
        bar = NSStatusBar.systemStatusBar()
        self._item = bar.statusItemWithLength_(NSVariableStatusItemLength)
        self._item.setTitle_("⚪ FG")
        self._item.setHighlightMode_(True)

        # Build menu
        self._menu         = NSMenu.alloc().init()
        self._cam_item     = self._make_item("Camera: warming up…", None)
        self._fatigue_item = self._make_item("Fatigue:   —",        None)
        self._stress_item  = self._make_item("Stress:    —",        None)
        self._combined_item= self._make_item("Combined:  —",        None)
        self._signal_item  = self._make_item("No signals",          None)
        dash_item          = self._make_item("Open Dashboard",      "openDashboard:")
        quit_item          = self._make_item("Quit FocusGuard",     "quitApp:")

        for it in [
            self._cam_item,
            NSMenuItem.separatorItem(),
            self._fatigue_item,
            self._stress_item,
            self._combined_item,
            NSMenuItem.separatorItem(),
            self._signal_item,
            NSMenuItem.separatorItem(),
            dash_item,
            NSMenuItem.separatorItem(),
            quit_item,
        ]:
            self._menu.addItem_(it)

        self._item.setMenu_(self._menu)

        # Kick off polling timer
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            POLL_INTERVAL, self, "tick:", None, True
        )
        # First assessment immediately
        self.tick_(None)

    def _make_item(self, title, action):
        item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, action, ""
        )
        item.setTarget_(self)
        return item

    @objc.typedSelector(b"v@:@")
    def tick_(self, _timer):
        cam    = _camera.get_stats()
        kbd    = _kb.get_stats()
        result = assess(cam, kbd)

        icon = _score_icon(result.combined)
        self._item.setTitle_(f"{icon} {result.combined:.0f}%")

        self._fatigue_item.setTitle_(f"Fatigue:   {result.fatigue_score:.0f}%")
        self._stress_item.setTitle_( f"Stress:    {result.stress_score:.0f}%")
        self._combined_item.setTitle_(f"Combined:  {result.combined:.0f}%")

        if cam["face_detected"]:
            self._cam_item.setTitle_(
                f"Camera ✓  blink {cam['blink_rate']:.0f}/min · EAR {cam['avg_ear']:.3f}"
            )
        else:
            self._cam_item.setTitle_("Camera ✗  no face detected")

        if result.reasons:
            self._signal_item.setTitle_("⚠ " + "  ·  ".join(result.reasons))
        else:
            self._signal_item.setTitle_("✓ No signals — all clear")

        if result.recommend_break and _notifier.ready():
            _notifier.notify(
                "FocusGuard — Take a Break",
                f"Fatigue {result.fatigue_score:.0f}%  Stress {result.stress_score:.0f}% — "
                "Step away for 5–10 min.",
            )

    @objc.typedSelector(b"v@:@")
    def openDashboard_(self, _sender):
        webbrowser.open(f"http://127.0.0.1:{DASHBOARD_PORT}")

    @objc.typedSelector(b"v@:@")
    def quitApp_(self, _sender):
        NSApplication.sharedApplication().terminate_(None)


# ── entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    _camera.start()
    _kb.start()
    threading.Thread(target=_run_flask, daemon=True).start()

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

    delegate = AppDelegate.alloc().init()
    app.setDelegate_(delegate)

    print("FocusGuard starting… look for the icon in your menu bar.")
    print(f"Dashboard: http://127.0.0.1:{DASHBOARD_PORT}")
    app.run()
