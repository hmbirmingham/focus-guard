"""
Synchronized multi-modal data logging.

Runs on its own daemon thread. Every poll interval it samples BOTH monitors
at the same instant, scores them, and appends one row to a daily CSV. Because
camera and keyboard stats are read in the same tick, each row is a
timestamp-aligned snapshot across modalities — the same pattern used in
embedded sensor-fusion systems where independent acquisition threads feed a
single synchronized log.

CSV files land in logs/session_YYYY-MM-DD.csv (one file per day; appended
across app restarts).
"""

import csv
import os
import threading
import time
from datetime import datetime, timedelta

from detector import assess

LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")

FIELDNAMES = [
    "timestamp",
    "blink_rate", "avg_ear", "face_detected",
    "keys_per_minute", "error_rate", "avg_pause_secs",
    "fatigue_score", "stress_score", "combined_score",
]


class DataLogger:
    """Producer thread that snapshots camera + keyboard state on a fixed
    interval and appends synchronized rows to a daily CSV."""

    def __init__(self, camera, keyboard, interval_s: float = 10.0):
        self._camera   = camera
        self._keyboard = keyboard
        self._interval = interval_s
        self._running  = False
        # _lock guards file reads (history queries) against concurrent row
        # appends from the logger thread.
        self._lock = threading.Lock()

    # ── lifecycle ───────────────────────────────────────────────────────────

    def start(self):
        """Spawn the logging thread. Daemon so it dies with the app."""
        os.makedirs(LOG_DIR, exist_ok=True)
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()

    def stop(self):
        self._running = False

    # ── internals ───────────────────────────────────────────────────────────

    @staticmethod
    def _path_for(day: datetime) -> str:
        return os.path.join(LOG_DIR, f"session_{day.strftime('%Y-%m-%d')}.csv")

    def _run(self):
        while self._running:
            self._log_row()
            time.sleep(self._interval)

    def _log_row(self):
        """Sample both monitors in the same instant and append one CSV row.
        Sampling together (not from separate timers) is what keeps the
        modalities synchronized."""
        cam    = self._camera.get_stats()
        kbd    = self._keyboard.get_stats()
        result = assess(cam, kbd)

        row = {
            "timestamp":       datetime.now().isoformat(timespec="seconds"),
            "blink_rate":      cam["blink_rate"],
            "avg_ear":         cam["avg_ear"],
            "face_detected":   int(cam["face_detected"]),
            "keys_per_minute": kbd["keys_per_minute"],
            "error_rate":      kbd["error_rate"],
            "avg_pause_secs":  kbd["avg_pause_secs"],
            "fatigue_score":   result.fatigue_score,
            "stress_score":    result.stress_score,
            "combined_score":  result.combined,
        }

        path = self._path_for(datetime.now())
        with self._lock:
            new_file = not os.path.exists(path)
            with open(path, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                if new_file:
                    writer.writeheader()
                writer.writerow(row)

    # ── queries ─────────────────────────────────────────────────────────────

    def history(self, minutes: int = 60) -> list:
        """Return rows from the last `minutes` as a list of dicts (numeric
        fields parsed). Reads today's file — and yesterday's if the window
        spans midnight — under the lock so a concurrent append can't be
        half-read."""
        cutoff = datetime.now() - timedelta(minutes=minutes)
        paths = {self._path_for(cutoff), self._path_for(datetime.now())}

        rows = []
        with self._lock:
            for path in sorted(paths):
                if not os.path.exists(path):
                    continue
                with open(path, newline="") as f:
                    for row in csv.DictReader(f):
                        try:
                            ts = datetime.fromisoformat(row["timestamp"])
                        except (KeyError, ValueError):
                            continue
                        if ts < cutoff:
                            continue
                        rows.append({
                            "timestamp":       row["timestamp"],
                            "blink_rate":      float(row["blink_rate"]),
                            "avg_ear":         float(row["avg_ear"]),
                            "face_detected":   bool(int(row["face_detected"])),
                            "keys_per_minute": float(row["keys_per_minute"]),
                            "error_rate":      float(row["error_rate"]),
                            "avg_pause_secs":  float(row["avg_pause_secs"]),
                            "fatigue_score":   float(row["fatigue_score"]),
                            "stress_score":    float(row["stress_score"]),
                            "combined_score":  float(row["combined_score"]),
                        })
        return rows
