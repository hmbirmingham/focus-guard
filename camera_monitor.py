import os
os.environ.setdefault("OPENCV_AVFOUNDATION_SKIP_AUTH", "1")

import cv2
import mediapipe as mp
import numpy as np
import threading
import time
from collections import deque

# MediaPipe face mesh landmark indices for each eye
LEFT_EYE  = [362, 385, 387, 263, 373, 380]
RIGHT_EYE = [33,  160, 158, 133, 153, 144]

BLINK_EAR_THRESHOLD = 0.25   # below this = eye closed
BLINK_CONSEC_FRAMES = 2       # frames eye must be closed to count as blink


def eye_aspect_ratio(landmarks, eye_indices, w, h):
    pts = [(int(landmarks[i].x * w), int(landmarks[i].y * h)) for i in eye_indices]
    # vertical distances
    v1 = np.linalg.norm(np.array(pts[1]) - np.array(pts[5]))
    v2 = np.linalg.norm(np.array(pts[2]) - np.array(pts[4]))
    # horizontal distance
    hz = np.linalg.norm(np.array(pts[0]) - np.array(pts[3]))
    return (v1 + v2) / (2.0 * hz + 1e-6)


class CameraMonitor:
    def __init__(self, window_seconds=60):
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._running = False

        # rolling window of (timestamp, blink) events
        self._blink_times = deque()
        self._ear_history = deque(maxlen=300)   # ~10s at 30fps

        self.blink_rate = 0.0       # blinks per minute
        self.avg_ear = 0.3          # average eye openness (0=closed, ~0.3=normal)
        self.face_detected = False

    def start(self):
        self._running = True
        t = threading.Thread(target=self._run, daemon=True)
        t.start()

    def stop(self):
        self._running = False

    def _run(self):
        mp_face_mesh = mp.solutions.face_mesh
        face_mesh = mp_face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        cap = cv2.VideoCapture(0, cv2.CAP_AVFOUNDATION)
        blink_counter = 0   # consecutive frames below threshold
        total_blinks = 0

        while self._running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.1)
                continue

            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb)

            now = time.time()

            if results.multi_face_landmarks:
                lm = results.multi_face_landmarks[0].landmark
                left_ear  = eye_aspect_ratio(lm, LEFT_EYE,  w, h)
                right_ear = eye_aspect_ratio(lm, RIGHT_EYE, w, h)
                ear = (left_ear + right_ear) / 2.0

                with self._lock:
                    self.face_detected = True
                    self._ear_history.append(ear)
                    self.avg_ear = float(np.mean(self._ear_history))

                if ear < BLINK_EAR_THRESHOLD:
                    blink_counter += 1
                else:
                    if blink_counter >= BLINK_CONSEC_FRAMES:
                        with self._lock:
                            self._blink_times.append(now)
                    blink_counter = 0

                # drop blinks outside the rolling window
                cutoff = now - self.window_seconds
                with self._lock:
                    while self._blink_times and self._blink_times[0] < cutoff:
                        self._blink_times.popleft()
                    # scale to per-minute
                    elapsed = min(now - (self._blink_times[0] if self._blink_times else now), self.window_seconds)
                    self.blink_rate = (len(self._blink_times) / max(elapsed, 1)) * 60
            else:
                with self._lock:
                    self.face_detected = False

        cap.release()
        face_mesh.close()

    def get_stats(self):
        with self._lock:
            return {
                "blink_rate":    round(self.blink_rate, 1),
                "avg_ear":       round(self.avg_ear, 3),
                "face_detected": self.face_detected,
            }
