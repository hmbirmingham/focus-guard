#!/usr/bin/env python3
"""
FocusGuard — stress & fatigue detector
Uses camera (blink rate, eye openness) + keyboard (speed, errors, pauses)
to score fatigue and stress, then nudges you to take a break.

Run:  python main.py
Stop: Ctrl+C
"""

import time
import os
from camera_monitor  import CameraMonitor
from keyboard_monitor import KeyboardMonitor
from detector        import assess
from notifier        import Notifier


POLL_INTERVAL = 10   # seconds between assessments


def clear():
    os.system("clear")


def bar(value, width=30):
    filled = int(value / 100 * width)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {value:.0f}%"


def render(camera_stats, keyboard_stats, assessment, notifier):
    clear()
    print("=" * 55)
    print("  FocusGuard — Real-time Stress & Fatigue Monitor")
    print("=" * 55)

    print("\n  CAMERA")
    if camera_stats["face_detected"]:
        print(f"    Blink rate : {camera_stats['blink_rate']:.1f} / min  (healthy: 12-20)")
        print(f"    Eye open   : {camera_stats['avg_ear']:.3f}  (drowsy < 0.22)")
    else:
        print("    No face detected — ensure camera is unobstructed")

    print("\n  KEYBOARD")
    print(f"    Speed      : {keyboard_stats['keys_per_minute']:.0f} keys/min")
    print(f"    Error rate : {keyboard_stats['error_rate']:.1f}%")
    print(f"    Avg pause  : {keyboard_stats['avg_pause_secs']:.1f}s")

    print("\n  SCORES")
    print(f"    Fatigue  {bar(assessment.fatigue_score)}")
    print(f"    Stress   {bar(assessment.stress_score)}")
    print(f"    Combined {bar(assessment.combined)}")

    if assessment.reasons:
        print("\n  SIGNALS DETECTED")
        for r in assessment.reasons:
            print(f"    • {r}")

    if assessment.recommend_break:
        print("\n  *** BREAK RECOMMENDED ***")
        if not notifier.ready():
            print("  (notification already sent — cooldown active)")
    else:
        print("\n  Status: You're good — keep going.")

    print(f"\n  Next check in {POLL_INTERVAL}s  |  Ctrl+C to quit")
    print("=" * 55)


def main():
    print("Starting FocusGuard...")
    print("Requesting camera access — approve the system prompt if it appears.\n")

    camera   = CameraMonitor()
    keyboard = KeyboardMonitor()
    notifier = Notifier()

    camera.start()
    keyboard.start()

    print("Monitoring started. Warming up for 10 seconds...")
    time.sleep(10)

    try:
        while True:
            camera_stats   = camera.get_stats()
            keyboard_stats = keyboard.get_stats()
            assessment     = assess(camera_stats, keyboard_stats)

            render(camera_stats, keyboard_stats, assessment, notifier)

            if assessment.recommend_break:
                notifier.notify(
                    "FocusGuard — Take a Break",
                    f"Fatigue {assessment.fatigue_score:.0f}  Stress {assessment.stress_score:.0f} — "
                    "Step away for 5-10 min.",
                )

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("\nShutting down FocusGuard.")
    finally:
        camera.stop()
        keyboard.stop()


if __name__ == "__main__":
    main()
