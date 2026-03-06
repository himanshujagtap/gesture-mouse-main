<!-- # Imports


print("Gesture_Controller top-level executed", flush=True)

import sys

# Ensure Python version is compatible with Mediapipe
if sys.version_info < (3,9):
    msg = (
        f"Incompatible Python version detected: {sys.version.splitlines()[0]}. "
        "MediaPipe (recent releases) uses modern typing features and requires Python 3.9+.\n"
        "Please upgrade Python (3.9+) or create a new virtual environment with Python 3.9+/3.10+.\n"
        "Example (conda): conda create -n gest39 python=3.10 -y && conda activate gest39 && pip install -r requirements.txt\n"
        "Example (venv): python -m venv .venv && .\.venv\Scripts\activate && pip install -r requirements.txt"
    )
    print(msg, flush=True)
    try:
        with open("gesture_controller_start.log","a",encoding="utf-8") as _f:
            _f.write("Version check failed: " + msg + "\n")
    except Exception:
        pass
    sys.exit(1)

try:
    import cv2
    import mediapipe as mp
    import pyautogui
    import math
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
            "If pip fails on Windows, try: pip install --upgrade pip setuptools wheel and then retry, or use 'pipwin' to install dependencies.\n"
        )
        print(msg, flush=True)
        try:
            with open("gesture_controller_start.log","a",encoding="utf-8") as _f:
                _f.write(msg + "\n")
        except Exception:
            pass
        raise ImportError(msg)    
    from enum import IntEnum
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    from google.protobuf.json_format import MessageToDict
    import screen_brightness_control as sbcontrol

    pyautogui.FAILSAFE = False
    mp_drawing = mp.solutions.drawing_utils
    mp_hands = mp.solutions.hands
except Exception as e:
    msg = f"Import-time error: {e!r}"
    print(msg, flush=True)
    try:
        import traceback
        with open("gesture_controller_start.log","a",encoding="utf-8") as _f:
            _f.write("Import-time error:\n")
            traceback.print_exc(file=_f)
    except Exception:
        pass
    raise

# Gesture Encodings 
class Gest(IntEnum):
    # Binary Encoded
    """
    Enum for mapping all hand gesture to binary number.
    """

    FIST = 0
    PINKY = 1
    RING = 2
    MID = 4
    LAST3 = 7
    INDEX = 8
    FIRST2 = 12
    LAST4 = 15
    THUMB = 16    
    PALM = 31
    
    # Extra Mappings
    V_GEST = 33
    TWO_FINGER_CLOSED = 34
    PINCH_MAJOR = 35
    PINCH_MINOR = 36

# Multi-handedness Labels
class HLabel(IntEnum):
    MINOR = 0
    MAJOR = 1

# Convert Mediapipe Landmarks to recognizable Gestures
class HandRecog:
    """
    Convert Mediapipe Landmarks to recognizable Gestures.
    """
    
    def __init__(self, hand_label):
        """
        Constructs all the necessary attributes for the HandRecog object.

        Parameters
        ----------
            finger : int
                Represent gesture corresponding to Enum 'Gest',
                stores computed gesture for current frame.
            ori_gesture : int
                Represent gesture corresponding to Enum 'Gest',
                stores gesture being used.
            prev_gesture : int
                Represent gesture corresponding to Enum 'Gest',
                stores gesture computed for previous frame.
            frame_count : int
                total no. of frames since 'ori_gesture' is updated.
            hand_result : Object
                Landmarks obtained from mediapipe.
            hand_label : int
                Represents multi-handedness corresponding to Enum 'HLabel'.
        """

        self.finger = 0
        self.ori_gesture = Gest.PALM
        self.prev_gesture = Gest.PALM
        self.frame_count = 0
        self.hand_result = None
        self.hand_label = hand_label
    
    def update_hand_result(self, hand_result):
        self.hand_result = hand_result

    def get_signed_dist(self, point):
        """
        returns signed euclidean distance between 'point'.

        Parameters
        ----------
        point : list contaning two elements of type list/tuple which represents 
            landmark point.
        
        Returns
        -------
        float
        """
        sign = -1
        if self.hand_result.landmark[point[0]].y < self.hand_result.landmark[point[1]].y:
            sign = 1
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        dist = math.sqrt(dist)
        return dist*sign
    
    def get_dist(self, point):
        """
        returns euclidean distance between 'point'.

        Parameters
        ----------
        point : list contaning two elements of type list/tuple which represents 
            landmark point.
        
        Returns
        -------
        float
        """
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        dist = math.sqrt(dist)
        return dist
    
    def get_dz(self,point):
        """
        returns absolute difference on z-axis between 'point'.

        Parameters
        ----------
        point : list contaning two elements of type list/tuple which represents 
            landmark point.
        
        Returns
        -------
        float
        """
        return abs(self.hand_result.landmark[point[0]].z - self.hand_result.landmark[point[1]].z)
    
    # Function to find Gesture Encoding using current finger_state.
    # Finger_state: 1 if finger is open, else 0
    def set_finger_state(self):
        """
        set 'finger' by computing ratio of distance between finger tip 
        , middle knuckle, base knuckle.

        Returns
        -------
        None
        """
        if self.hand_result == None:
            return

        points = [[8,5,0],[12,9,0],[16,13,0],[20,17,0]]
        self.finger = 0
        self.finger = self.finger | 0 #thumb
        for idx,point in enumerate(points):
            
            dist = self.get_signed_dist(point[:2])
            dist2 = self.get_signed_dist(point[1:])
            
            try:
                ratio = round(dist/dist2,1)
            except:
                ratio = 0

            self.finger = self.finger << 1
            if ratio > 0.5 :
                self.finger = self.finger | 1
    

    # Handling Fluctations due to noise
    def get_gesture(self):
        """
        returns int representing gesture corresponding to Enum 'Gest'.
        sets 'frame_count', 'ori_gesture', 'prev_gesture', 
        handles fluctations due to noise.
        
        Returns
        -------
        int
        """
        if self.hand_result == None:
            return Gest.PALM

        current_gesture = Gest.PALM
        if self.finger in [Gest.LAST3,Gest.LAST4] and self.get_dist([8,4]) < 0.05:
            if self.hand_label == HLabel.MINOR :
                current_gesture = Gest.PINCH_MINOR
            else:
                current_gesture = Gest.PINCH_MAJOR

        elif Gest.FIRST2 == self.finger :
            point = [[8,12],[5,9]]
            dist1 = self.get_dist(point[0])
            dist2 = self.get_dist(point[1])
            ratio = dist1/dist2
            if ratio > 1.7:
                current_gesture = Gest.V_GEST
            else:
                if self.get_dz([8,12]) < 0.1:
                    current_gesture =  Gest.TWO_FINGER_CLOSED
                else:
                    current_gesture =  Gest.MID
            
        else:
            current_gesture =  self.finger
        
        if current_gesture == self.prev_gesture:
            self.frame_count += 1
        else:
            self.frame_count = 0

        self.prev_gesture = current_gesture

        if self.frame_count > 4 :
            self.ori_gesture = current_gesture
        return self.ori_gesture

# Executes commands according to detected gestures
class Controller:
    """
    Executes commands according to detected gestures.

    Attributes
    ----------
    tx_old : int
        previous mouse location x coordinate
    ty_old : int
        previous mouse location y coordinate
    flag : bool
        true if V gesture is detected
    grabflag : bool
        true if FIST gesture is detected
    pinchmajorflag : bool
        true if PINCH gesture is detected through MAJOR hand,
        on x-axis 'Controller.changesystembrightness', 
        on y-axis 'Controller.changesystemvolume'.
    pinchminorflag : bool
        true if PINCH gesture is detected through MINOR hand,
        on x-axis 'Controller.scrollHorizontal', 
        on y-axis 'Controller.scrollVertical'.
    pinchstartxcoord : int
        x coordinate of hand landmark when pinch gesture is started.
    pinchstartycoord : int
        y coordinate of hand landmark when pinch gesture is started.
    pinchdirectionflag : bool
        true if pinch gesture movment is along x-axis,
        otherwise false
    prevpinchlv : int
        stores quantized magnitued of prev pinch gesture displacment, from 
        starting position
    pinchlv : int
        stores quantized magnitued of pinch gesture displacment, from 
        starting position
    framecount : int
        stores no. of frames since 'pinchlv' is updated.
    prev_hand : tuple
        stores (x, y) coordinates of hand in previous frame.
    pinch_threshold : float
        step size for quantization of 'pinchlv'.
    """

    tx_old = 0
    ty_old = 0
    trial = True
    flag = False
    grabflag = False
    pinchmajorflag = False
    pinchminorflag = False
    pinchstartxcoord = None
    pinchstartycoord = None
    pinchdirectionflag = None
    prevpinchlv = 0
    pinchlv = 0
    framecount = 0
    prev_hand = None
    pinch_threshold = 0.3
    
    def getpinchylv(hand_result):
        """returns distance beween starting pinch y coord and current hand position y coord."""
        dist = round((Controller.pinchstartycoord - hand_result.landmark[8].y)*10,1)
        return dist

    def getpinchxlv(hand_result):
        """returns distance beween starting pinch x coord and current hand position x coord."""
        dist = round((hand_result.landmark[8].x - Controller.pinchstartxcoord)*10,1)
        return dist
    
    def changesystembrightness():
        """sets system brightness based on 'Controller.pinchlv'."""
        currentBrightnessLv = sbcontrol.get_brightness(display=0)/100.0
        currentBrightnessLv += Controller.pinchlv/50.0
        if currentBrightnessLv > 1.0:
            currentBrightnessLv = 1.0
        elif currentBrightnessLv < 0.0:
            currentBrightnessLv = 0.0       
        sbcontrol.fade_brightness(int(100*currentBrightnessLv) , start = sbcontrol.get_brightness(display=0))
    
    def changesystemvolume():
        """sets system volume based on 'Controller.pinchlv'."""
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        currentVolumeLv = volume.GetMasterVolumeLevelScalar()
        currentVolumeLv += Controller.pinchlv/50.0
        if currentVolumeLv > 1.0:
            currentVolumeLv = 1.0
        elif currentVolumeLv < 0.0:
            currentVolumeLv = 0.0
        volume.SetMasterVolumeLevelScalar(currentVolumeLv, None)
    
    def scrollVertical():
        """scrolls on screen vertically."""
        pyautogui.scroll(120 if Controller.pinchlv>0.0 else -120)
        
    
    def scrollHorizontal():
        """scrolls on screen horizontally."""
        pyautogui.keyDown('shift')
        pyautogui.keyDown('ctrl')
        pyautogui.scroll(-120 if Controller.pinchlv>0.0 else 120)
        pyautogui.keyUp('ctrl')
        pyautogui.keyUp('shift')

    # Locate Hand to get Cursor Position
    # Stabilize cursor by Dampening
    def get_position(hand_result):
        """
        returns coordinates of current hand position.

        Locates hand to get cursor position also stabilize cursor by 
        dampening jerky motion of hand.

        Returns
        -------
        tuple(float, float)
        """
        point = 9
        position = [hand_result.landmark[point].x ,hand_result.landmark[point].y]
        sx,sy = pyautogui.size()
        x_old,y_old = pyautogui.position()
        x = int(position[0]*sx)
        y = int(position[1]*sy)
        if Controller.prev_hand is None:
            Controller.prev_hand = x,y
        delta_x = x - Controller.prev_hand[0]
        delta_y = y - Controller.prev_hand[1]

        distsq = delta_x**2 + delta_y**2
        ratio = 1
        Controller.prev_hand = [x,y]

        if distsq <= 25:
            ratio = 0
        elif distsq <= 900:
            ratio = 0.07 * (distsq ** (1/2))
        else:
            ratio = 2.1
        x , y = x_old + delta_x*ratio , y_old + delta_y*ratio
        return (x,y)

    def pinch_control_init(hand_result):
        """Initializes attributes for pinch gesture."""
        Controller.pinchstartxcoord = hand_result.landmark[8].x
        Controller.pinchstartycoord = hand_result.landmark[8].y
        Controller.pinchlv = 0
        Controller.prevpinchlv = 0
        Controller.framecount = 0

    # Hold final position for 5 frames to change status
    def pinch_control(hand_result, controlHorizontal, controlVertical):
        """
        calls 'controlHorizontal' or 'controlVertical' based on pinch flags, 
        'framecount' and sets 'pinchlv'.

        Parameters
        ----------
        hand_result : Object
            Landmarks obtained from mediapipe.
        controlHorizontal : callback function assosiated with horizontal
            pinch gesture.
        controlVertical : callback function assosiated with vertical
            pinch gesture. 
        
        Returns
        -------
        None
        """
        if Controller.framecount == 5:
            Controller.framecount = 0
            Controller.pinchlv = Controller.prevpinchlv

            if Controller.pinchdirectionflag == True:
                controlHorizontal() #x

            elif Controller.pinchdirectionflag == False:
                controlVertical() #y

        lvx =  Controller.getpinchxlv(hand_result)
        lvy =  Controller.getpinchylv(hand_result)
            
        if abs(lvy) > abs(lvx) and abs(lvy) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = False
            if abs(Controller.prevpinchlv - lvy) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv = lvy
                Controller.framecount = 0

        elif abs(lvx) > Controller.pinch_threshold:
            Controller.pinchdirectionflag = True
            if abs(Controller.prevpinchlv - lvx) < Controller.pinch_threshold:
                Controller.framecount += 1
            else:
                Controller.prevpinchlv = lvx
                Controller.framecount = 0

    def handle_controls(gesture, hand_result):  
        """Impliments all gesture functionality."""      
        x,y = None,None
        if gesture != Gest.PALM :
            x,y = Controller.get_position(hand_result)
        
        # flag reset
        if gesture != Gest.FIST and Controller.grabflag:
            Controller.grabflag = False
            pyautogui.mouseUp(button = "left")

        if gesture != Gest.PINCH_MAJOR and Controller.pinchmajorflag:
            Controller.pinchmajorflag = False

        if gesture != Gest.PINCH_MINOR and Controller.pinchminorflag:
            Controller.pinchminorflag = False

        # implementation
        if gesture == Gest.V_GEST:
            Controller.flag = True
            pyautogui.moveTo(x, y, duration = 0.1)

        elif gesture == Gest.FIST:
            if not Controller.grabflag : 
                Controller.grabflag = True
                pyautogui.mouseDown(button = "left")
            pyautogui.moveTo(x, y, duration = 0.1)

        elif gesture == Gest.MID and Controller.flag:
            pyautogui.click()
            Controller.flag = False

        elif gesture == Gest.INDEX and Controller.flag:
            pyautogui.click(button='right')
            Controller.flag = False

        elif gesture == Gest.TWO_FINGER_CLOSED and Controller.flag:
            pyautogui.doubleClick()
            Controller.flag = False

        elif gesture == Gest.PINCH_MINOR:
            if Controller.pinchminorflag == False:
                Controller.pinch_control_init(hand_result)
                Controller.pinchminorflag = True
            Controller.pinch_control(hand_result,Controller.scrollHorizontal, Controller.scrollVertical)
        
        elif gesture == Gest.PINCH_MAJOR:
            if Controller.pinchmajorflag == False:
                Controller.pinch_control_init(hand_result)
                Controller.pinchmajorflag = True
            Controller.pinch_control(hand_result,Controller.changesystembrightness, Controller.changesystemvolume)
        
def list_cameras(max_index=5):
    """Probe camera indices from 0 to max_index-1 and print availability."""
    print(f"Probing camera indices 0..{max_index-1} ...", flush=True)
    for i in range(max_index):
        # On Windows DirectShow backend may improve detection
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        opened = cap.isOpened()
        print(f"  index {i}: {'AVAILABLE' if opened else 'not available'}", flush=True)
        if opened:
            cap.release()

'''
----------------------------------------  Main Class  ----------------------------------------
    Entry point of Gesture Controller
''' 


class GestureController:
    """
    Handles camera, obtain landmarks from mediapipe, entry point
    for whole program.

    Attributes
    ----------
    gc_mode : int
        indicates weather gesture controller is running or not,
        1 if running, otherwise 0.
    cap : Object
        object obtained from cv2, for capturing video frame.
    CAM_HEIGHT : int
        highet in pixels of obtained frame from camera.
    CAM_WIDTH : int
        width in pixels of obtained frame from camera.
    hr_major : Object of 'HandRecog'
        object representing major hand.
    hr_minor : Object of 'HandRecog'
        object representing minor hand.
    dom_hand : bool
        True if right hand is domaniant hand, otherwise False.
        default True.
    """
    gc_mode = 0
    cap = None
    CAM_HEIGHT = None
    CAM_WIDTH = None
    hr_major = None # Right Hand by default
    hr_minor = None # Left hand by default
    dom_hand = True

    def __init__(self, camera_index=0, verbose=False):
        """Initilaizes attributes."""
        GestureController.gc_mode = 1
        GestureController.cap = cv2.VideoCapture(camera_index)
        if not GestureController.cap.isOpened():
            msg = f"Unable to open camera index {camera_index}. Please check camera availability or pass a different index using --camera."
            logging.error(msg)
            print(msg, flush=True)
            print(f"Python: {sys.version.splitlines()[0]}; Platform: {platform.platform()}", flush=True)
            # Provide quick probe of available indices to help debugging
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
        sets 'hr_major', 'hr_minor' based on classification(left, right) of 
        hand obtained from mediapipe, uses 'dom_hand' to decide major and
        minor hand.
        """
        left , right = None,None
        try:
            handedness_dict = MessageToDict(results.multi_handedness[0])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[0]
            else :
                left = results.multi_hand_landmarks[0]
        except:
            pass

        try:
            handedness_dict = MessageToDict(results.multi_handedness[1])
            if handedness_dict['classification'][0]['label'] == 'Right':
                right = results.multi_hand_landmarks[1]
            else :
                left = results.multi_hand_landmarks[1]
        except:
            pass
        
        if GestureController.dom_hand == True:
            GestureController.hr_major = right
            GestureController.hr_minor = left
        else :
            GestureController.hr_major = left
            GestureController.hr_minor = right

    def start(self):
        """
        Entry point of whole programm, caputres video frame and passes, obtains
        landmark from mediapipe and passes it to 'handmajor' and 'handminor' for
        controlling.
        """
        
        handmajor = HandRecog(HLabel.MAJOR)
        handminor = HandRecog(HLabel.MINOR)

        if GestureController.cap is None or not GestureController.cap.isOpened():
            logging.error("Camera is not available. Exiting.")
            return

        try:
            with mp_hands.Hands(max_num_hands = 2,min_detection_confidence=0.5, min_tracking_confidence=0.5) as hands:
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
                        
                        for hand_landmarks in results.multi_hand_landmarks:
                            mp_drawing.draw_landmarks(image, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                    else:
                        Controller.prev_hand = None
                    cv2.imshow('Gesture Controller', image)
                    if cv2.waitKey(5) & 0xFF in (13, 27, ord('q')):
                        logging.info("Exit key pressed.")
                        break
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
    # Route logging to stdout so outputs show up in consoles reliably
    logging.basicConfig(stream=sys.stdout, level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s: %(message)s")

    if args.list_cameras:
        try:
            with open("gesture_controller_start.log","a",encoding="utf-8") as _f:
                _f.write(f"list-cameras requested (max probe 8)\n")
        except Exception:
            pass
        list_cameras(8)
        try:
            with open("gesture_controller_start.log","a",encoding="utf-8") as _f:
                _f.write("list-cameras completed\n")
        except Exception:
            pass
        sys.exit(0)

    try:
        with open("gesture_controller_start.log","a",encoding="utf-8") as _f:
            _f.write(f"Starting Gesture Controller (camera={args.camera}, verbose={args.verbose})\n")
    except Exception:
        pass
    print(f"Starting Gesture Controller (camera={args.camera}, verbose={args.verbose})")
    gc1 = GestureController(camera_index=args.camera, verbose=args.verbose)
    if GestureController.gc_mode:
        gc1.start()
    else:
        logging.error("Exiting due to camera initialization failure.")

-------------------------------------------------------------------------------

Recommended fixes (pick one)
Option A — Using conda (recommended)

Create env and activate:
conda create -n gest39 python=3.10 -y
conda activate gest39
Install deps:
pip install --upgrade pip
pip install -r requirements.txt
Run:
python Gesture_Controller.py --camera 0 --verbose



Create new env with Python 3.10 (recommended)

conda create -n gest39 python=3.10 -y
conda activate gest39
Upgrade pip and install requirements

python -m pip install --upgrade pip
pip install -r requirements.txt
Install PyAudio & pywin32 (Windows)

Option A (conda):
conda install -c anaconda pyaudio -y
conda install pywin32 -y
Option B (if pip install pyaudio fails):
pip install pipwin
pipwin install pyaudio
(Optional) Test camera probe and run app

python Gesture_Controller.py --list-cameras --verbose
python Gesture_Controller.py --camera 0 --verbose
Notes: You can also upgrade your existing env (conda install python=3.10 -n gest) but creating a fresh env is safer.

If you cannot upgrade Python
I can suggest an older mediapipe version that may work on Python 3.8, but it’s fragile and may lack features. Say so if you want that fallback.
Want me to:

generate exact conda/pip commands for your current environment, or
add a short checklist to README.md for setup and common troubleshooting? ✅




Quick note ✅
Thanks — the pip install started. Two small fixes before we proceed:

The earlier python check used mp.file (typo). Use mp.__file__ instead to see the install location.
After the install finishes, run the verification command below and paste the output.
Next actions (run these now) 🧪
If pip install is still running, let it finish. If it finished, show the end of its output (paste it here).
Run this diagnostic command:
python -c "import mediapipe as mp; print('mediapipe', mp.version); print('file=', getattr(mp,'file','N/A')); print('has_solutions=', hasattr(mp,'solutions'))"
If step 2 reports has_solutions = True, run the camera probe:
python Gesture_Controller.py --list-cameras --verbose
If step 2 reports has_solutions = False, try reinstalling a known-compatible combo and paste the install output:
python -m pip uninstall mediapipe -y
python -m pip install mediapipe==0.10.5 protobuf==4.23.4
If you paste the results of step 2 (and any pip output), I’ll give the exact next command and, if needed, the fix for Windows install errors. 🔧

Working commands summary
Say	Does
proton hello	Greeting
proton what is your name	Name
proton date	Today's date
proton time	Current time
proton search [query]	Google search
proton location	Google Maps
proton launch gesture recognition	Starts gesture camera
proton stop gesture recognition	Stops gesture camera
proton list	Lists C:/ files
proton copy	Ctrl+C
proton paste	Ctrl+V
proton bye	Sleep mode
proton exit	Quit

unctionality you could add
Here are some practical additions that fit naturally into the existing structure:

Command idea	What it would do
jarvis open notepad / jarvis open calculator	os.startfile() or subprocess to launch apps
jarvis screenshot	pyautogui.screenshot() — already have pyautogui
jarvis scroll up/down	pyautogui.scroll()
jarvis volume up/down/mute	pycaw — already imported in Gesture_Controller
jarvis wikipedia [topic]	wikipedia.summary() — already imported but unused
jarvis type [text]	pyautogui.typewrite() to dictate text
jarvis minimize / jarvis maximize	pyautogui.hotkey('win', 'd') etc.
jarvis lock	os.system('rundll32.exe user32.dll,LockWorkStation')

mac:
cd "/Users/himanshu/Desktop/final project/gesture-mouse"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-mac.txt
python Gesture_Controller.py
python Quantum.py -->

# Gesture Mouse + Quantum Voice Assistant

A Python desktop assistant that combines:

- **Hand gesture mouse control** (cursor, clicks, drag, scroll, volume, brightness)
- **Voice + text commands** through a lightweight **Eel web UI**
- **System, browser, app, utility, and fun commands**

Built with **MediaPipe**, **OpenCV**, **PyAutoGUI**, **SpeechRecognition**, and **Eel**.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Requirements](#requirements)
- [Installation](#installation)
  - [Option A: Conda (Recommended)](#option-a-conda-recommended)
  - [Option B: Virtualenv](#option-b-virtualenv)
- [Run the Project](#run-the-project)
- [How It Works](#how-it-works)
- [Gesture Controls](#gesture-controls)
- [Voice Commands (from `cmds.md`)](#voice-commands-from-cmdsmd)
- [Troubleshooting](#troubleshooting)
- [Customization Guide](#customization-guide)
- [Development Notes](#development-notes)
- [Roadmap Ideas](#roadmap-ideas)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Features

### Gesture Mouse Control
- Cursor movement via hand tracking
- Left click / right click / double click
- Click-and-drag using fist gesture
- Scroll control via pinch
- Volume and brightness control via dominant-hand pinch

### Quantum Assistant
- Wake-word + command flow (`quantum ...`) for voice mode
- Text command input in chat UI
- App open/close commands
- Browser shortcuts (new tab, close tab, refresh, incognito)
- System controls (volume, lock, brightness, etc.)
- Search/information commands (Wikipedia, weather, web search)
- Utility/fun commands (timer, joke, coin flip, dice, motivational quote, etc.)
- Assistant rename support (`change name to ...`)

---

## Project Structure

```bash
.
├── Quantum.py                # Main assistant runtime (voice + command logic + UI thread)
├── Gesture_Controller.py     # Gesture recognition and mouse/system control pipeline
├── app.py                    # Eel chat app bridge (backend for web UI)
├── web/
│   ├── index.html            # UI page
│   ├── js/main.js            # Chat message render + input handlers
│   └── css/...               # Styles
├── cmds.md                   # Extracted command reference (source of command list)
├── QUANTUM_COMMANDS.md       # Detailed command reference
├── GESTURE_GUIDE.md          # Human-friendly gesture tutorial
├── requirements.txt          # Main dependencies (includes Windows-specific libs)
└── requirements-mac.txt      # macOS-oriented dependency list

Requirements
Python 3.9+ (recommended: 3.10)

Webcam for gesture tracking

Microphone for voice mode

Desktop OS support:

Best support currently for Windows and macOS

Some controls are platform-specific (audio/brightness/app launching)

Installation
Choose the setup that fits your environment.

Option A: Conda (Recommended)
conda create -n gest39 python=3.10 -y
conda activate gest39
pip install --upgrade pip
pip install -r requirements.txt
Option B: Virtualenv
Windows (PowerShell / CMD)
python -m venv .venv
.\.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-mac.txt
Run the Project
1) Run full assistant (UI + voice/text + commands + gesture launch command)
python Quantum.py
2) Run gesture controller directly (standalone gesture mode)
python Gesture_Controller.py
Optional camera/debug flags (if supported in your current script version):

python Gesture_Controller.py --camera 0 --verbose
python Gesture_Controller.py --list-cameras
Exit keys (gesture window)
ESC or Enter or Q

How It Works
Quantum.py starts the Eel chat interface from app.py.

You can provide input by:

voice (wake-word style), or

text via the chat input box.

Commands are parsed and routed to handlers (system, app, browser, utility, etc.).

Gesture recognition is available via gesture module and related command triggers.

Gesture Controls
Primary gestures
✌️ V gesture → cursor movement mode

✊ Fist → click and drag

🤏 Pinch (dominant hand) → volume/brightness

🤏 Pinch (non-dominant hand) → scrolling

Secondary gestures (after V gesture)
🖕 Middle finger up → left click

☝️ Index finger up → right click

🤞 Two fingers closed → double click

Tips
Use good lighting

Keep hand 1–2 feet from camera

Move steadily for smoother tracking

Voice Commands (from cmds.md)
Default assistant name: quantum
If renamed, use the new name instead.

1) Basic
quantum hello

quantum what is your name

quantum who are you

quantum time

quantum date

quantum search [query]

2) Name Management
quantum change name to [name]

quantum rename to [name]

quantum call yourself [name]

3) System Controls
Window

quantum minimize

quantum maximize

quantum close window

quantum lock

Display / Scroll

quantum scroll up

quantum scroll down

quantum brightness up

quantum brightness down

Audio

quantum volume up

quantum volume down

quantum mute

4) Application Control
Open

quantum open calculator

quantum open notes

quantum open safari

quantum open chrome

quantum open firefox

quantum open mail

quantum open finder

quantum open terminal

quantum open settings

quantum open vscode

quantum open slack

quantum open spotify

quantum open discord

quantum open zoom

quantum open [any app]

Close

quantum close calculator

quantum close chrome

quantum close [app name]

quantum close window

5) Browser
quantum new tab

quantum close tab

quantum incognito

quantum refresh

quantum reload

6) Text/Input
quantum type [text]

quantum copy

quantum paste

7) Information
quantum wikipedia [topic]

quantum weather

quantum weather [city]

8) Music
quantum play music

quantum pause music

quantum next song

quantum next track

quantum previous song

quantum previous track

9) Gesture Recognition Control
quantum launch gesture recognition

quantum stop gesture recognition

10) Fun & Utility
quantum joke

quantum tell me a joke

quantum flip a coin

quantum roll a dice

quantum timer [minutes]

quantum set timer [minutes]

11) System Info
quantum battery

quantum cpu

quantum system info

12) Sleep / Wake / Exit
quantum sleep

quantum go to sleep

quantum wake up

quantum wake

quantum exit

quantum quit

quantum terminate

13) File Navigation
quantum list

quantum open [number]

quantum back

14) Short-form Syntax
open app [name]

close app [name]

list

open [number]

back

time

set timer [minutes]

timer [minutes]

cpu

system info

battery

sleep

go to sleep

wake up

15) Quick Calculations
calculate [expression]

math [expression]

Examples:

calculate 25 * 48

math 50 - 12

16) Unit Conversion
convert [value] [unit] to [unit]

Examples:

convert 5 km to miles

convert 25 celsius to fahrenheit

17) Enhanced Web Search
youtube search [query]

youtube [query]

github search [query]

github [query]

stackoverflow [query]

translate [text] to [language]

define [word]

18) Network
ip address

show ip

wifi name

19) Motivation/Facts
motivational quote

inspire me

motivate me

random fact

tell me a fact

fun fact

20) Magic 8 Ball
magic 8 ball [question]

magic eight ball [question]

21) Social
compliment me

say something nice

insult me

roast me

22) Help
help

commands

what can you do

23) Personality/Easter Eggs
quantum sing

quantum dance

quantum tell me about yourself

quantum what do you think about ai

quantum are you alive

quantum are you real

quantum are you conscious

good job quantum

great job

well done

thank you

Troubleshooting
1) Camera not opening
Try camera list/probe flags if available.

Ensure no other app is locking webcam.

2) Gesture jitter
Improve lighting

Keep steady hand distance

Use smoother movement

3) Mic/voice not recognized
Check microphone permissions

Ensure internet connectivity for online speech recognition backend

Try text mode in chat UI as fallback

4) MediaPipe issues
Reinstall compatible versions:

pip install -U mediapipe protobuf
5) OS-specific command failures
Some app/system commands depend on OS APIs and installed apps.

Windows/macOS behavior may differ.

Customization Guide
Change assistant default name
In Quantum.py, update:

assistant_name = "Quantum"
Add a new command
Add elif block in command handler in Quantum.py

Add command suggestion in app.py (getCommandSuggestions)

Document it in cmds.md and this README

Tune gesture sensitivity
Adjust thresholds/smoothing values in Gesture_Controller.py

Re-test with your camera + lighting setup

Change UI branding
Edit title/text/styles in:

web/index.html

web/css/...

web/js/main.js (behavior only)

Development Notes
Keep command docs centralized in cmds.md and sync README snapshots periodically.

Prefer separating platform-specific actions into helper utilities if command list keeps growing.

If adding LLM features, gate them with clear fallback logic for offline use.

Roadmap Ideas
 Add unit tests for command parser/fuzzy matching

 Add command permission/safety layer (dangerous actions confirmation)

 Add plugin architecture for commands

 Add Linux-focused compatibility matrix

 Add packaged installers (Windows/macOS)

License
Choose one and add it here (MIT / Apache-2.0 / GPL / Proprietary).

Example:

MIT License
Acknowledgements
MediaPipe

OpenCV

PyAutoGUI

Eel

SpeechRecognition

