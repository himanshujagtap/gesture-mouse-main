"""
Custom Gesture Trainer
======================
Record your own hand gestures and map them to actions.

Usage
-----
    python custom_gesture_trainer.py --name thumbs_up --action-type hotkey --action-value "cmd+shift+3"
    python custom_gesture_trainer.py --name wave      --action-type type_text --action-value "Hello!"
    python custom_gesture_trainer.py --name point     --action-type open_app  --action-value "Calculator"

Controls (in the OpenCV window)
--------------------------------
    SPACE  — capture one sample (need 25)
    ENTER  — save & finish (only available after 25+ samples)
    Q/ESC  — cancel without saving

Saved to:  custom_gestures/<name>.json
"""

import os
import sys
import json
import argparse

import cv2
import mediapipe as mp

# ──────────────────────────────────────────────────────────────────────────────
_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(_ROOT, 'custom_gestures')
SAMPLES_NEEDED = 25

mp_hands = mp.solutions.hands
mp_drawing = mp.solutions.drawing_utils


# ──────────────────────────────────────────────────────────────────────────────
def extract_features(hand_landmarks):
    """
    Convert 21 MediaPipe landmarks into 42 scale/translation-invariant floats.
    Centers on wrist (landmark 0) and scales by wrist-to-middle-MCP distance
    (landmark 9), so the features are consistent across hand sizes and positions.
    """
    pts = [(lm.x, lm.y) for lm in hand_landmarks.landmark]
    cx, cy = pts[0]
    pts = [(x - cx, y - cy) for x, y in pts]
    scale = (pts[9][0] ** 2 + pts[9][1] ** 2) ** 0.5
    if scale > 0:
        pts = [(x / scale, y / scale) for x, y in pts]
    return [coord for pt in pts for coord in pt]


# ──────────────────────────────────────────────────────────────────────────────
def train(gesture_name: str, action_type: str, action_value: str, camera_index: int = 0) -> bool:
    """
    Open the training UI, collect samples, then save to JSON.
    Returns True on success, False if cancelled or failed.
    """
    os.makedirs(DATA_DIR, exist_ok=True)

    cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        print(f"[Trainer] Cannot open camera {camera_index}")
        return False

    samples = []
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    with mp_hands.Hands(
        max_num_hands=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.5,
    ) as hands:

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb.flags.writeable = False
            results = hands.process(rgb)
            rgb.flags.writeable = True

            # Draw hand landmarks
            if results.multi_hand_landmarks:
                for lm in results.multi_hand_landmarks:
                    mp_drawing.draw_landmarks(frame, lm, mp_hands.HAND_CONNECTIONS)

            count = len(samples)
            progress = min(count / SAMPLES_NEEDED, 1.0)

            # ── Top bar ──────────────────────────────────────────────────────
            cv2.rectangle(frame, (0, 0), (W, 75), (0, 0, 0), -1)
            cv2.putText(frame, f'Training: "{gesture_name}"', (10, 26),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 120), 2)

            # Progress bar
            bar_x1, bar_y1, bar_y2 = 10, 38, 58
            bar_x2 = W - 10
            filled = int(bar_x1 + (bar_x2 - bar_x1) * progress)
            cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (50, 50, 50), -1)
            cv2.rectangle(frame, (bar_x1, bar_y1), (filled, bar_y2), (0, 200, 80), -1)
            cv2.rectangle(frame, (bar_x1, bar_y1), (bar_x2, bar_y2), (200, 200, 200), 1)
            cv2.putText(frame, f'{count}/{SAMPLES_NEEDED}', (bar_x1, bar_y2 + 12),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

            # ── Bottom instruction bar ───────────────────────────────────────
            cv2.rectangle(frame, (0, H - 30), (W, H), (0, 0, 0), -1)
            if count < SAMPLES_NEEDED:
                hint = 'SPACE: capture sample   |   Q: quit'
                hint_color = (0, 200, 255)
            else:
                hint = 'ENTER: save & finish   |   SPACE: add more   |   Q: quit'
                hint_color = (0, 255, 100)
            cv2.putText(frame, hint, (10, H - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, hint_color, 1)

            # ── Hand-not-detected warning ────────────────────────────────────
            if not results.multi_hand_landmarks:
                cv2.putText(frame, 'No hand detected — show your hand!',
                            (10, H - 45), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 80, 255), 2)

            cv2.imshow(f'Gesture Trainer — {gesture_name}', frame)
            key = cv2.waitKey(5) & 0xFF

            if key in (ord('q'), 27):  # Q or ESC
                print("[Trainer] Cancelled.")
                cap.release()
                cv2.destroyAllWindows()
                return False

            elif key == ord(' '):
                if results.multi_hand_landmarks:
                    feats = extract_features(results.multi_hand_landmarks[0])
                    samples.append(feats)
                    print(f"[Trainer] Captured {len(samples)}/{SAMPLES_NEEDED}")
                else:
                    print("[Trainer] No hand visible — skipped.")

            elif key == 13 and count >= SAMPLES_NEEDED:  # Enter
                break

    cap.release()
    cv2.destroyAllWindows()

    if len(samples) < SAMPLES_NEEDED:
        print(f"[Trainer] Only {len(samples)} samples — need {SAMPLES_NEEDED}. Not saved.")
        return False

    # ── Save JSON ─────────────────────────────────────────────────────────────
    data = {
        'name': gesture_name,
        'action_type': action_type,
        'action_value': action_value,
        'samples': samples,
    }
    path = os.path.join(DATA_DIR, f'{gesture_name}.json')
    with open(path, 'w') as f:
        json.dump(data, f)

    print(f"[Trainer] Saved {len(samples)} samples → {path}")
    return True


# ──────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Custom Gesture Trainer',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--name', required=True,
                        help='Gesture name, e.g. thumbs_up (use underscores)')
    parser.add_argument('--action-type', default='hotkey',
                        choices=['hotkey', 'type_text', 'open_app'],
                        help='Type of action to execute when gesture is detected')
    parser.add_argument('--action-value', default='',
                        help='Action value: hotkey (e.g. cmd+shift+3), text, or app name')
    parser.add_argument('--camera', type=int, default=0,
                        help='Camera index (default 0)')
    args = parser.parse_args()

    # Prompt for action value interactively if not provided
    if not args.action_value:
        prompts = {
            'hotkey':    'Enter hotkey (e.g. cmd+shift+3  or  ctrl+c): ',
            'type_text': 'Enter text to type: ',
            'open_app':  'Enter app name (e.g. Calculator): ',
        }
        args.action_value = input(prompts[args.action_type]).strip()
        if not args.action_value:
            print("Action value is required. Exiting.")
            sys.exit(1)

    # Sanitize name
    gesture_name = args.name.strip().lower().replace(' ', '_')

    ok = train(gesture_name, args.action_type, args.action_value, args.camera)
    if ok:
        print(f"\n✓ Gesture '{gesture_name}' saved!")
        print(f"  Action: {args.action_type} = {args.action_value}")
        print(f"  Launch Gesture Controller to use it.")
    else:
        print("Training failed or cancelled.")
        sys.exit(1)
