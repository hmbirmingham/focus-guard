import subprocess
import time


COOLDOWN_SECONDS = 600   # default: don't re-notify within 10 minutes


class Notifier:
    def __init__(self, cooldown_seconds: float = COOLDOWN_SECONDS):
        self._cooldown = cooldown_seconds
        self._last_notified = 0.0

    def notify(self, title: str, message: str):
        now = time.time()
        if now - self._last_notified < self._cooldown:
            return
        self._last_notified = now
        script = f'display notification "{message}" with title "{title}" sound name "Blow"'
        subprocess.run(["osascript", "-e", script], check=False)

    def ready(self) -> bool:
        return time.time() - self._last_notified >= self._cooldown
