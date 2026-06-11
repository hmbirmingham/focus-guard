"""
Combines camera and keyboard signals into fatigue/stress scores (0-100).

Fatigue signals (camera):
  - Low blink rate  (<10/min)  → eyes drying out, losing focus
  - Low avg EAR     (<0.22)    → heavy eyelids
  - High avg pause  (keyboard) → brain slowing down

Stress signals (keyboard):
  - High error rate (>15%)     → losing precision under pressure
  - Typing speed drop          → compared against a rolling baseline
"""

from dataclasses import dataclass


BLINK_NORMAL_MIN = 12   # blinks/min healthy range low
BLINK_NORMAL_MAX = 20
EAR_DROWSY       = 0.22
ERROR_STRESS_PCT = 15   # % backspaces that indicates stress
PAUSE_FATIGUE_S  = 8    # avg pause >8s = brain stalling

BREAK_THRESHOLD  = 60   # combined score to recommend a break


@dataclass
class Assessment:
    fatigue_score: float   # 0-100
    stress_score:  float   # 0-100
    combined:      float   # 0-100
    reasons:       list
    recommend_break: bool


def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def assess(camera_stats: dict, keyboard_stats: dict) -> Assessment:
    fatigue = 0.0
    stress  = 0.0
    reasons = []

    # --- fatigue from blink rate ---
    blink = camera_stats.get("blink_rate", BLINK_NORMAL_MIN)
    if camera_stats.get("face_detected", False):
        if blink < BLINK_NORMAL_MIN:
            # 0 blinks/min → +40 fatigue; 12 → 0
            pts = _clamp((BLINK_NORMAL_MIN - blink) / BLINK_NORMAL_MIN * 40)
            fatigue += pts
            if pts > 10:
                reasons.append(f"Low blink rate ({blink:.0f}/min) — eyes drying out")
        elif blink > BLINK_NORMAL_MAX:
            # rapid blinking also signals irritation/fatigue
            pts = _clamp((blink - BLINK_NORMAL_MAX) / BLINK_NORMAL_MAX * 20)
            fatigue += pts
            if pts > 5:
                reasons.append(f"High blink rate ({blink:.0f}/min) — eye irritation")

    # --- fatigue from eye openness ---
    ear = camera_stats.get("avg_ear", 0.3)
    if camera_stats.get("face_detected", False) and ear < EAR_DROWSY:
        pts = _clamp((EAR_DROWSY - ear) / EAR_DROWSY * 50)
        fatigue += pts
        reasons.append("Heavy eyelids detected")

    # --- fatigue from long pauses ---
    pause = keyboard_stats.get("avg_pause_secs", 0)
    if pause > PAUSE_FATIGUE_S:
        pts = _clamp((pause - PAUSE_FATIGUE_S) / PAUSE_FATIGUE_S * 30)
        fatigue += pts
        if pts > 8:
            reasons.append(f"Long pauses between typing ({pause:.0f}s avg) — mental fatigue")

    # --- stress from error rate ---
    error_pct = keyboard_stats.get("error_rate", 0)
    if error_pct > ERROR_STRESS_PCT:
        pts = _clamp((error_pct - ERROR_STRESS_PCT) / ERROR_STRESS_PCT * 60)
        stress += pts
        reasons.append(f"High error rate ({error_pct:.0f}%) — loss of precision")

    # --- stress from very high typing speed (frantic) ---
    kpm = keyboard_stats.get("keys_per_minute", 0)
    if kpm > 400:
        pts = _clamp((kpm - 400) / 200 * 30)
        stress += pts
        reasons.append(f"Frantic typing speed ({kpm:.0f} kpm)")

    fatigue  = _clamp(fatigue)
    stress   = _clamp(stress)
    combined = _clamp(fatigue * 0.6 + stress * 0.4)

    return Assessment(
        fatigue_score=round(fatigue, 1),
        stress_score=round(stress, 1),
        combined=round(combined, 1),
        reasons=reasons,
        recommend_break=combined >= BREAK_THRESHOLD,
    )
