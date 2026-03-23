print("Gesture_Controller top-level executed", flush=True)

import sys

# Ensure Python version is compatible with Mediapipe
if sys.version_info < (3, 9):
    msg = (
        f"Incompatible Python version detected: {sys.version.splitlines()[0]}. "
        "MediaPipe (recent releases) uses modern typing features and requires Python 3.9+.\n"
        "Please upgrade Python (3.9+) or create a new virtual environment with Python 3.9+/3.10+.\n"
        "Example (conda): conda create -n gest39 python=3.10 -y && conda activate gest39 && pip install -r requirements.txt\n"
        "Example (venv): python -m venv .venv && .\.venv\Scripts\\activate && pip install -r requirements.txt"
    )
    print(msg, flush=True)
    try:
        with open("gesture_controller_start.log", "a", encoding="utf-8") as _f:
            _f.write("Version check failed: " + msg + "\n")
    except Exception:
        pass
    sys.exit(1)

try:
    import cv2
    import mediapipe as mp
    import pyautogui
    import argparse
    import logging
    import platform

    # Quick validation: ensure mediapipe provides the expected API
    if not hasattr(mp, 'solutions'):
        msg = (
            "mediapipe appears to be installed but does not expose 'mp.solutions'.\n"
            "This usually indicates a broken or incompatible build. Try:\n"
            "  python -m pip uninstall mediapipe -y\n"
            "  python -m pip install mediapipe==0.10.5 protobuf -U\n"
        )
        print(msg, flush=True)
        try:
            with open("gesture_controller_start.log", "a", encoding="utf-8") as _f:
                _f.write(msg + "\n")
        except Exception:
            pass
        raise ImportError(msg)

    from google.protobuf.json_format import MessageToDict

    # Import from modular files (replaces inline class definitions)
    from gesture_enums import Gest, HLabel
    from hand_recognizer import HandRecog
    from controller import Controller
    from utils import list_cameras

    pyautogui.FAILSAFE = False
    mp_drawing = mp.solutions.drawing_utils
    mp_hands = mp.solutions.hands

except Exception as e:
    msg = f"Import-time error: {e!r}"
    print(msg, flush=True)
    try:
        import traceback
        with open("gesture_controller_start.log", "a", encoding="utf-8") as _f:
            _f.write("Import-time error:\n")
            traceback.print_exc(file=_f)
    except Exception:
        pass
    raise


'''
----------------------------------------  Main Class  ----------------------------------------
    Entry point of Gesture Controller
'''


class GestureController:
    """
    Handles camera, obtains landmarks from mediapipe, entry point
    for the whole program.

    Attributes
    ----------
    gc_mode : int
        indicates whether gesture controller is running or not,
        1 if running, otherwise 0.
    cap : Object
        object obtained from cv2, for capturing video frame.
    CAM_HEIGHT : int
        height in pixels of obtained frame from camera.
    CAM_WIDTH : int
        width in pixels of obtained frame from camera.
    hr_major : Object of 'HandRecog'
        object representing major hand.
    hr_minor : Object of 'HandRecog'
        object representing minor hand.
    dom_hand : bool
        True if right hand is dominant hand, otherwise False.
        default True.
    """
    
    gc_mode = 0
    cap = None
    CAM_HEIGHT = None
    CAM_WIDTH = None
    hr_major = None  # Right Hand by default
    hr_minor = None  # Left hand by default
    dom_hand = True

    def __init__(self, camera_index=0, verbose=False):
        """Initializes attributes."""
        GestureController.gc_mode = 1
        GestureController.cap = cv2.VideoCapture(camera_index)
        if not GestureController.cap.isOpened():
            msg = f"Unable to open camera index {camera_index}. Please check camera availability or pass a different index using --camera."
            logging.error(msg)
            print(msg, flush=True)
            print(f"Python: {sys.version.splitlines()[0]}; Platform: {platform.platform()}", flush=True)
            try:
                list_cameras(6)
            except Exception as e:
                logging.debug("list_cameras probe failed: %s", e)
            GestureController.gc_mode = 0
            return
        GestureController.CAM_HEIGHT = GestureController.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        GestureController.CAM_WIDTH = GestureController.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        if verbose:
            logging.info(f"Camera {camera_index} opened (width={GestureController.CAM_WIDTH}, height={GestureController.CAM_HEIGHT})")

    def classify_hands(results):
        """
        Sets 'hr_major', 'hr_minor' based on classification (left, right) of
        hand obtained from mediapipe. Uses 'dom_hand' to decide major and minor hand.
        """
        left, right = None, None
        try:
            handedness_dict = MessageToDict(results.multi_handedness[0])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[0]
            else:
                left = results.multi_hand_landmarks[0]
        except:
            pass

        try:
            handedness_dict = MessageToDict(results.multi_handedness[1])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[1]
            else:
                left = results.multi_hand_landmarks[1]
        except:
            pass

        if GestureController.dom_hand == True:
            GestureController.hr_major = right
            GestureController.hr_minor = left
        else:
            GestureController.hr_major = left
            GestureController.hr_minor = right

    def start(self):
        """
        Entry point of whole program. Captures video frames, obtains landmarks
        from mediapipe and passes them to handmajor and handminor for controlling.
        """
        handmajor = HandRecog(HLabel.MAJOR)
        handminor = HandRecog(HLabel.MINOR)

        # Load custom gestures (graceful — missing file or import error = disabled)
        try:
            from custom_gesture_recognizer import CustomGestureRecognizer
            custom_recognizer = CustomGestureRecognizer()
        except Exception as _e:
            logging.debug("Custom gesture recognizer not loaded: %s", _e)
            custom_recognizer = None

        if GestureController.cap is None or not GestureController.cap.isOpened():
            logging.error("Camera is not available. Exiting.")
            return

        try:
            window_available = True
            try:
                cv2.namedWindow('Gesture Controller', cv2.WINDOW_NORMAL)
                cv2.resizeWindow('Gesture Controller', 1280, 720)
            except Exception as e:
                logging.warning(f"Could not create OpenCV window: {e}. Running in headless mode.")
                window_available = False

            with mp_hands.Hands(max_num_hands=2, min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
                while GestureController.cap.isOpened() and GestureController.gc_mode:
                    success, image = GestureController.cap.read()

                    if not success:
                        logging.warning("Ignoring empty camera frame.")
                        continue

                    image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
                    image.flags.writeable = False
                    results = hands.process(image)

                    image.flags.writeable = True
                    image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

                    if results.multi_hand_landmarks:
                        GestureController.classify_hands(results)
                        handmajor.update_hand_result(GestureController.hr_major)
                        handminor.update_hand_result(GestureController.hr_minor)

                        handmajor.set_finger_state()
                        handminor.set_finger_state()
                        gest_name = handminor.get_gesture()

                        if gest_name == Gest.PINCH_MINOR:
                            Controller.handle_controls(gest_name, handminor.hand_result)
                        else:
                            gest_name = handmajor.get_gesture()
                            Controller.handle_controls(gest_name, handmajor.hand_result)

                        # Custom gesture check — both hands checked independently
                        # (right-hand and left-hand versions of the same pose are separate gestures)
                        custom_name = None
                        if custom_recognizer:
                            custom_name = custom_recognizer.check_and_execute(
                                GestureController.hr_major, GestureController.hr_minor
                            )

                        for hand_landmarks in results.multi_hand_landmarks:
                            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                        # Gesture confidence overlay
                        _GESTURE_NAMES = {
                            0: 'Fist / Drag', 1: 'Pinky', 2: 'Ring', 4: 'Left Click',
                            7: 'Last 3', 8: 'Right Click', 12: 'Two Fingers',
                            15: 'Last 4', 16: 'Thumb', 31: 'Palm',
                            33: 'V — Cursor Mode', 34: 'Double Click',
                            35: 'Pinch — Vol/Brightness', 36: 'Pinch — Scroll',
                        }
                        minor_g = handminor.get_gesture()
                        major_g = handmajor.get_gesture()
                        active_g = minor_g if int(minor_g) == 36 else major_g
                        label = _GESTURE_NAMES.get(int(active_g), str(active_g))
                        if custom_name:
                            label = f'Custom: {custom_name}'
                        cv2.rectangle(image, (8, 8), (320, 40), (0, 0, 0), -1)
                        cv2.putText(image, f'Gesture: {label}', (12, 30),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 120), 2)
                    else:
                        Controller.prev_hand = None

                    if window_available:
                        try:
                            cv2.imshow('Gesture Controller', image)
                        except:
                            window_available = False
                    try:
                        if cv2.waitKey(5) & 0xFF in (13, 27, ord('q')):
                            logging.info("Exit key pressed.")
                            break
                    except:
                        pass
        except KeyboardInterrupt:
            logging.info("Interrupted by user.")
        except Exception as e:
            logging.exception("Exception in main loop: %s", e)
        finally:
            GestureController.cap.release()
            cv2.destroyAllWindows()
            logging.info("Gesture Controller stopped.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gesture Controller")
    parser.add_argument("--camera", type=int, default=0, help="camera index (default 0)")
    parser.add_argument("--verbose", action="store_true", help="enable verbose logging")
    parser.add_argument("--list-cameras", action="store_true", help="probe camera indices and exit")
    args = parser.parse_args()
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s"
    )

    if args.list_cameras:
        try:
            with open("gesture_controller_start.log", "a", encoding="utf-8") as _f:
                _f.write("list-cameras requested (max probe 8)\n")
        except Exception:
            pass
        list_cameras(8)
        sys.exit(0)

    try:
        with open("gesture_controller_start.log", "a", encoding="utf-8") as _f:
            _f.write(f"Starting Gesture Controller (camera={args.camera}, verbose={args.verbose})\n")
    except Exception:
        pass
    print(f"Starting Gesture Controller (camera={args.camera}, verbose={args.verbose})")
    gc1 = GestureController(camera_index=args.camera, verbose=args.verbose)
    if GestureController.gc_mode:
        gc1.start()
    else:
        logging.error("Exiting due to camera initialization failure.")
