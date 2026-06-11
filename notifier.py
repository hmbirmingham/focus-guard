import subprocess
import time


COOLDOWN_SECONDS = 600   # don't re-notify within 10 minutes


class Notifier:
    def __init__(self):
        self._last_notified = 0.0

    def notify(self, title: str, message: str):
        now = time.time()
        if now - self._last_notified < COOLDOWN_SECONDS:
            return
        self._last_notified = now
        script = f'display notification "{message}" with title "{title}" sound name "Blow"'
        subprocess.run(["osascript", "-e", script], check=False)

    def ready(self) -> bool:
        return time.time() - self._last_notified >= COOLDOWN_SECONDS
