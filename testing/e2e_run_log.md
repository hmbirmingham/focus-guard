# End-to-end validation run — 2026-09-16

Run on macOS (Apple M4), against a fresh clone at `feat/validation-cleanup`.

## Environment finding: Python version pins mediapipe

The machine's default `python3` (Anaconda, 3.14) cannot install
`mediapipe==0.10.14` — no wheel is published for cp313/cp314 on any platform,
and every mediapipe release currently on PyPI for cp313+ (0.10.30 through
1.0.1) has dropped the legacy `mediapipe.solutions` API entirely (only the
new Tasks API remains), which is what `camera_monitor.py` depends on
(`mp.solutions.face_mesh.FaceMesh`). So on a newer Python, install "succeeds"
against a bumped version but the app crashes at runtime on
`AttributeError: module 'mediapipe' has no attribute 'solutions'`.

**Workaround used for this run:** macOS ships `/usr/bin/python3` (3.9.6),
which has a matching `mediapipe==0.10.14` wheel and keeps the legacy
`solutions` API. Created a project-local virtualenv with it:

```bash
/usr/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # installs clean, incl. mediapipe==0.10.14
```

This isn't a code bug so much as an undocumented upper bound — see the
README Requirements update in this same branch (Python 3.9–3.12, not just
"3.9+"). No source changes were made to `camera_monitor.py`; the legacy API
still works fine on a supported Python.

## What was run

```bash
source .venv/bin/activate
python3 app.py &
```

## Confirmed programmatically (curl / filesystem / process checks)

- [x] `pip3 install -r requirements.txt` completes cleanly in the `.venv` (Python 3.9.6)
- [x] Process starts and stays up (Flask + camera + keyboard + logger threads, no crash)
- [x] `GET /api/status` → `200`, returns live `camera` / `keyboard` / `assessment` JSON, updates each call
- [x] `GET /api/history` → `200`, returns accumulating rows matching the CSV
- [x] `GET /` → `200`, serves `ui/index.html` (dashboard shell)
- [x] `logs/session_2026-09-16.csv` created and appended once per `poll_interval_s` (10s) — 5 rows confirmed over ~50s, header + fields match `data_logger.FIELDNAMES`
- [x] Process shuts down cleanly on `kill` (SIGTERM)

Sample log output confirming camera/accessibility permission state during this run:

```
OpenCV: not authorized to capture video (status 0), set OPENCV_AVFOUNDATION_SKIP_AUTH=0 to enable authorization request or perform it in your application.
This process is not trusted! Input event monitoring will not be possible until it is added to accessibility clients.
```

This is expected — the automated run's process wasn't granted Camera /
Accessibility permissions (those are per-app, GUI-driven, one-time grants —
see below), so `face_detected` stayed `false` and keyboard stats stayed at
`0` for the whole run. The important thing this run does confirm: the app
degrades safely with no face/no keyboard input (no crash, all-zero scores,
`recommend_break: false`), and every plumbing layer (threads → shared state
→ Flask → CSV) is wired correctly end to end.

## Requires manual confirmation (not observable from a terminal/API)

These need you, at your own keyboard, granting the permissions and watching
the actual screen:

1. **Camera permission grant** — first run prompts, or grant manually at
   System Settings → Privacy & Security → Camera, for whichever process runs
   `python3 app.py` (Terminal, or your terminal app of choice).
2. **Accessibility permission grant** — System Settings → Privacy & Security
   → Accessibility, same process, needed for `pynput` keyboard capture.
3. **Menu bar icon** — confirm `⚪ FG` appears on launch and updates to
   `🟢/🟡/🔴 NN%` every 10s once the camera has real frames.
4. **Dropdown contents** — confirm blink rate / EAR / signals text updates
   live when you click the menu bar item.
5. **Dashboard in a real browser** — open `http://127.0.0.1:5001` from the
   menu's "Open Dashboard" and confirm the trend chart renders and
   auto-refreshes.
6. **Native notification** — get the combined score ≥ 60 (e.g. hold your
   eyes closed / look away for 30+ seconds to drop blink rate and EAR) and
   confirm a native macOS notification fires with sound, and that it
   respects the 10-minute cooldown on a second trigger.

Once you've done these, it's fair to call the system live-validated
end-to-end; this run covers everything except the parts that need a human
in front of the camera and screen.
