import threading
import time
from collections import deque
from pynput import keyboard


PAUSE_THRESHOLD = 2.0   # seconds between keystrokes to count as a pause


class KeyboardMonitor:
    def __init__(self, window_seconds=60):
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._listener = None

        self._key_times = deque()       # timestamps of all keystrokes
        self._error_times = deque()     # timestamps of backspace/delete presses
        self._last_key_time = None
        self._pause_durations = deque(maxlen=50)

        self.keys_per_minute = 0.0
        self.error_rate = 0.0           # backspaces as % of total keys
        self.avg_pause = 0.0            # avg seconds between bursts

    def start(self):
        self._listener = keyboard.Listener(on_press=self._on_press)
        self._listener.daemon = True
        self._listener.start()

    def stop(self):
        if self._listener:
            self._listener.stop()

    def _on_press(self, key):
        now = time.time()
        is_error = key in (keyboard.Key.backspace, keyboard.Key.delete)

        with self._lock:
            self._key_times.append(now)
            if is_error:
                self._error_times.append(now)

            if self._last_key_time is not None:
                gap = now - self._last_key_time
                if gap >= PAUSE_THRESHOLD:
                    self._pause_durations.append(gap)
            self._last_key_time = now

            self._prune(now)
            self._recalculate(now)

    def _prune(self, now):
        cutoff = now - self.window_seconds
        while self._key_times   and self._key_times[0]   < cutoff:
            self._key_times.popleft()
        while self._error_times and self._error_times[0] < cutoff:
            self._error_times.popleft()

    def _recalculate(self, now):
        total = len(self._key_times)
        errors = len(self._error_times)
        if self._key_times:
            elapsed = min(now - self._key_times[0], self.window_seconds)
            self.keys_per_minute = (total / max(elapsed, 1)) * 60
        else:
            self.keys_per_minute = 0.0

        self.error_rate = (errors / total * 100) if total > 0 else 0.0
        self.avg_pause = float(sum(self._pause_durations) / len(self._pause_durations)) \
                         if self._pause_durations else 0.0

    def get_stats(self):
        with self._lock:
            return {
                "keys_per_minute": round(self.keys_per_minute, 1),
                "error_rate":      round(self.error_rate, 1),
                "avg_pause_secs":  round(self.avg_pause, 1),
            }
