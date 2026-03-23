"""
Custom Gesture Recognizer
=========================
Loads trained gesture JSON files from custom_gestures/ and runs
k-Nearest Neighbors inference on live MediaPipe hand landmarks.

No external ML library required — pure Python + stdlib math only.

Tuning constants (top of file):
    K                  — neighbours to consider (default 5)
    DISTANCE_THRESHOLD — max avg k-NN distance for a valid match (default 1.5)
    FRAMES_TO_CONFIRM  — consecutive frames gesture must be seen before firing (default 10)
    COOLDOWN_SECONDS   — minimum time between repeated executions (default 2.0)
"""

import os
import json
import math
import time
import platform

# ── Tunable constants ─────────────────────────────────────────────────────────
K = 5
DISTANCE_THRESHOLD = 1.5
FRAMES_TO_CONFIRM = 10
COOLDOWN_SECONDS = 2.0

# ──────────────────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_ROOT, 'custom_gestures')
_IS_MAC = platform.system() == 'Darwin'


def _extract_features(hand_landmarks):
    """
    42 scale/translation-invariant floats from 21 MediaPipe landmarks.
    Centers on wrist (lm[0]), scales by wrist-to-middle-MCP (lm[9]) distance.
    Must match the identical function in custom_gesture_trainer.py.
    """
    pts = [(lm.x, lm.y) for lm in hand_landmarks.landmark]
    cx, cy = pts[0]
    pts = [(x - cx, y - cy) for x, y in pts]
    scale = (pts[9][0] ** 2 + pts[9][1] ** 2) ** 0.5
    if scale > 0:
        pts = [(x / scale, y / scale) for x, y in pts]
    return [coord for pt in pts for coord in pt]


def _euclidean(a, b):
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _mirror_features(features):
    """
    Negate the x-component of each normalized landmark.
    Right-hand thumbs-up and left-hand thumbs-up are mirror images;
    this maps one to the other so a single training session covers both hands.
    """
    mirrored = []
    for i in range(0, len(features), 2):
        mirrored.append(-features[i])   # flip x
        mirrored.append(features[i + 1])  # keep y
    return mirrored


# ──────────────────────────────────────────────────────────────────────────────
class CustomGestureRecognizer:
    """
    Usage
    -----
        rec = CustomGestureRecognizer()

        # In your camera loop:
        fired_name = rec.check_and_execute(hand_landmarks)   # None or gesture name
    """

    def __init__(self):
        self._gestures = {}       # name → {action_type, action_value, samples}
        self._last_gesture = None
        self._frame_count = 0
        self._last_exec_time = 0.0
        self.load_gestures()

    # ── Public API ────────────────────────────────────────────────────────────

    def load_gestures(self):
        """(Re)load all *.json files from custom_gestures/."""
        self._gestures.clear()
        if not os.path.isdir(DATA_DIR):
            return
        for fname in sorted(os.listdir(DATA_DIR)):
            if not fname.endswith('.json'):
                continue
            path = os.path.join(DATA_DIR, fname)
            try:
                with open(path) as f:
                    data = json.load(f)
                self._gestures[data['name']] = data
            except Exception as e:
                print(f"[CustomGesture] Failed to load {fname}: {e}")
        if self._gestures:
            print(f"[CustomGesture] Loaded {len(self._gestures)} gesture(s): "
                  f"{list(self._gestures.keys())}")

    def predict(self, hand_landmarks):
        """
        Returns (gesture_name, avg_dist) or (None, inf) if no confident match.
        No mirroring — left and right hand gestures are treated as distinct,
        allowing each hand to independently trigger different commands.
        Does NOT apply cooldown or debounce — use check_and_execute() for that.
        """
        if not self._gestures:
            return None, float('inf')

        query = _extract_features(hand_landmarks)
        best_name, best_dist = None, float('inf')

        for name, gdata in self._gestures.items():
            samples = gdata['samples']
            dists = sorted(_euclidean(query, s) for s in samples)
            k_dists = dists[:min(K, len(dists))]
            avg = sum(k_dists) / len(k_dists)
            if avg < best_dist:
                best_dist = avg
                best_name = name

        if best_dist > DISTANCE_THRESHOLD:
            return None, best_dist
        return best_name, best_dist

    def check_and_execute(self, major_landmarks, minor_landmarks=None):
        """
        Check both major (dominant) and minor hand independently.
        Each hand only matches gestures it was trained for — left and right
        hand versions of the same pose are treated as separate gestures.
        The more confident match (lower distance) across both hands wins.

        To train a gesture for a specific hand:
            python custom_gesture_trainer.py --name thumbs_up_right ...   (right hand)
            python custom_gesture_trainer.py --name thumbs_up_left  ...   (left hand)
        """
        name_maj, dist_maj = (self.predict(major_landmarks)
                              if major_landmarks else (None, float('inf')))
        name_min, dist_min = (self.predict(minor_landmarks)
                              if minor_landmarks else (None, float('inf')))

        # Best confident match across both hands
        name = name_maj if dist_maj <= dist_min else name_min

        if name is None:
            self._last_gesture = None
            self._frame_count = 0
            return None

        # Debounce: same gesture must persist for FRAMES_TO_CONFIRM frames
        if name != self._last_gesture:
            self._last_gesture = name
            self._frame_count = 1
            return None

        self._frame_count += 1
        if self._frame_count < FRAMES_TO_CONFIRM:
            return name  # recognised but not yet committed

        # Cooldown
        now = time.time()
        if now - self._last_exec_time < COOLDOWN_SECONDS:
            return name  # recognised but throttled

        # Fire!
        self._last_exec_time = now
        self._frame_count = 0
        self._execute(name, self._gestures[name])
        return name

    def list_gestures(self):
        """Return sorted list of gesture names."""
        return sorted(self._gestures.keys())

    def delete_gesture(self, name: str) -> bool:
        """Delete gesture JSON file and remove from memory. Returns True on success."""
        path = os.path.join(DATA_DIR, f'{name}.json')
        if os.path.exists(path):
            os.remove(path)
            self._gestures.pop(name, None)
            return True
        return False

    # ── Private ───────────────────────────────────────────────────────────────

    def _execute(self, name, gdata):
        action_type = gdata.get('action_type', 'hotkey')
        action_value = gdata.get('action_value', '')
        print(f"[CustomGesture] '{name}' → {action_type}: {action_value}")
        try:
            import pyautogui
            if action_type == 'hotkey':
                # Support both "cmd+shift+3" and "cmd shift 3" formats
                keys = [k.strip() for k in action_value.replace('+', ' ').split() if k.strip()]
                pyautogui.hotkey(*keys)
            elif action_type == 'type_text':
                pyautogui.typewrite(action_value, interval=0.05)
            elif action_type == 'open_app':
                import subprocess as _sp
                if _IS_MAC:
                    _sp.Popen(['open', '-a', action_value])
                else:
                    os.startfile(action_value)
        except Exception as e:
            print(f"[CustomGesture] Action failed: {e}")
