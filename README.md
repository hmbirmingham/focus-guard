# FocusGuard

A lightweight macOS menu bar app that monitors fatigue and stress in real-time using your camera and keyboard behaviour.

![macOS](https://img.shields.io/badge/macOS-12%2B-black?logo=apple) ![Python](https://img.shields.io/badge/Python-3.9%2B-blue?logo=python)

---

## What it does

FocusGuard sits in your menu bar and quietly watches two signals:

| Signal | What it measures |
|---|---|
| **Camera** | Blink rate and eye openness (EAR) via MediaPipe face mesh |
| **Keyboard** | Typing speed, error rate (backspaces), and pause length |

It combines these into a **Fatigue** score and a **Stress** score, shows them in the menu bar, and sends a native macOS notification when it's time to take a break.

---

## Features

- **Menu bar icon** — `🟢/🟡/🔴 XX%` combined score, updates every 10 seconds
- **Quick dropdown** — camera status, all three scores, and any active signals at a glance
- **Full dashboard** — click *Open Dashboard* for a live web UI with raw parameter gauges
- **Native notifications** — macOS system notification when score ≥ 60 (10-min cooldown)
- No cloud, no accounts — everything runs locally

---

## How scores are calculated

### Fatigue (camera + keyboard)
| Condition | Points |
|---|---|
| Blink rate < 12/min | up to +40 |
| Blink rate > 20/min (irritation) | up to +20 |
| Eye openness (EAR) < 0.22 | up to +50 |
| Avg typing pause > 8s | up to +30 |

### Stress (keyboard)
| Condition | Points |
|---|---|
| Error rate (backspaces) > 15% | up to +60 |
| Typing speed > 400 kpm (frantic) | up to +30 |

**Combined** = Fatigue × 0.6 + Stress × 0.4 — break recommended at ≥ 60.

---

## Requirements

- macOS 12 or later
- Python 3.9+
- Camera and Accessibility permissions granted to Terminal

---

## Setup

```bash
git clone https://github.com/hmbirmingham/focus-guard.git
cd focus-guard
pip3 install -r requirements.txt
```

### Permissions (first run only)

1. **Camera** → System Settings › Privacy & Security › Camera → enable Terminal
2. **Accessibility** → System Settings › Privacy & Security › Accessibility → add Terminal

---

## Run

```bash
python3 app.py
```

The menu bar icon appears immediately. Click *Open Dashboard* for the full UI at `http://127.0.0.1:5001`.

Stop with `Ctrl+C` in the terminal.

---

## Project structure

```
focus-guard/
├── app.py              # Menu bar app (PyObjC) + Flask dashboard server
├── camera_monitor.py   # MediaPipe face mesh — blink rate & EAR
├── keyboard_monitor.py # pynput — speed, error rate, pauses
├── detector.py         # Scoring logic
├── notifier.py         # macOS notifications via osascript
├── main.py             # Legacy terminal-only runner
└── ui/
    └── index.html      # Apple-style dashboard (auto-refreshes every 5s)
```

---

## Roadmap

- [ ] Package as a `.app` bundle (no Terminal needed)
- [ ] Historical charts (fatigue trend over the day)
- [ ] Configurable thresholds
- [ ] Pomodoro-style break timer
- [ ] Dock-less launch on login
