import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import detector


def normal_camera():
    return {"blink_rate": 16.0, "avg_ear": 0.30, "face_detected": True}


def normal_keyboard():
    return {"keys_per_minute": 100.0, "error_rate": 0.0, "avg_pause_secs": 0.0}


def test_fatigue_score_zero():
    result = detector.assess(normal_camera(), normal_keyboard())
    assert result.fatigue_score == 0.0
    assert result.combined == 0.0
    assert result.recommend_break is False


def test_fatigue_score_max():
    camera = {"blink_rate": 0.0, "avg_ear": 0.0, "face_detected": True}
    keyboard = {"keys_per_minute": 0.0, "error_rate": 0.0, "avg_pause_secs": 1000.0}
    result = detector.assess(camera, keyboard)
    assert result.fatigue_score == 100.0


def test_stress_score_high_error_rate():
    camera = normal_camera()
    keyboard = {"keys_per_minute": 100.0, "error_rate": 50.0, "avg_pause_secs": 0.0}
    result = detector.assess(camera, keyboard)
    assert result.stress_score > 0
    assert any("error rate" in r.lower() for r in result.reasons)


def test_combined_score_weighting():
    # Chosen so neither term clamps and the numbers stay exact under rounding.
    camera = {"blink_rate": 6.0, "avg_ear": 0.30, "face_detected": True}
    keyboard = {"keys_per_minute": 100.0, "error_rate": 30.0, "avg_pause_secs": 0.0}
    result = detector.assess(camera, keyboard)
    assert result.fatigue_score == 20.0
    assert result.stress_score == 60.0
    expected_combined = round(result.fatigue_score * 0.6 + result.stress_score * 0.4, 1)
    assert result.combined == expected_combined


def test_config_fallback(monkeypatch, tmp_path):
    missing_path = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(detector, "_CONFIG_PATH", str(missing_path))
    assert detector.load_config() == detector._DEFAULTS


def test_ear_threshold():
    drowsy_camera = {"blink_rate": 16.0, "avg_ear": 0.10, "face_detected": True}
    result = detector.assess(drowsy_camera, normal_keyboard())
    assert result.fatigue_score > 0
    assert "Heavy eyelids detected" in result.reasons

    alert_camera = {"blink_rate": 16.0, "avg_ear": 0.25, "face_detected": True}
    result = detector.assess(alert_camera, normal_keyboard())
    assert result.fatigue_score == 0.0
