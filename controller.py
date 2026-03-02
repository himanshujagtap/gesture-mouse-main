"""
System Controller Module

Executes system commands based on detected gestures.
Handles mouse control, clicking, scrolling, volume, and brightness.
"""

import pyautogui
from gesture_enums import Gest

# Windows-specific imports (optional on macOS/Linux)
WINDOWS_FEATURES_AVAILABLE = False
try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    import screen_brightness_control as sbcontrol
    WINDOWS_FEATURES_AVAILABLE = True
except ImportError:
    pass  # Gracefully skip Windows-specific features on other platforms

# Disable PyAutoGUI fail-safe (moving mouse to corner won't stop program)
pyautogui.FAILSAFE = False


class Controller:
    """
    Executes commands according to detected gestures.

    This class manages all system interactions including mouse movement,
    clicking, dragging, scrolling, volume control, and brightness control.

    Attributes
    ----------
    tx_old : int
        Previous mouse location x coordinate
    ty_old : int
        Previous mouse location y coordinate
    flag : bool
        True if V gesture is detected
    grabflag : bool
        True if FIST gesture is detected
    pinchmajorflag : bool
        True if PINCH gesture is detected through MAJOR hand
    pinchminorflag : bool
        True if PINCH gesture is detected through MINOR hand
    pinchstartxcoord : float
        X coordinate of hand landmark when pinch gesture is started
    pinchstartycoord : float
        Y coordinate of hand landmark when pinch gesture is started
    pinchdirectionflag : bool
        True if pinch gesture movement is along x-axis, False for y-axis, None if not determined
    prevpinchlv : float
        Stores quantized magnitude of prev pinch gesture displacement
    pinchlv : float
        Stores quantized magnitude of pinch gesture displacement
    framecount : int
        Stores no. of frames since 'pinchlv' is updated
    prev_hand : tuple
        Stores (x, y) coordinates of hand in previous frame
    pinch_threshold : float
        Step size for quantization of 'pinchlv'
    prev_pinch_x : float
        Previous pinch x coordinate for incremental control
    prev_pinch_y : float
        Previous pinch y coordinate for incremental control
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
    # For incremental pinch control
    prev_pinch_x = None
    prev_pinch_y = None

    @staticmethod
    def getpinchylv(hand_result):
        """Returns distance between starting pinch y coord and current hand position y coord."""
        dist = round((Controller.pinchstartycoord - hand_result.landmark[8].y) * 10, 1)
        return dist

    @staticmethod
    def getpinchxlv(hand_result):
        """Returns distance between starting pinch x coord and current hand position x coord."""
        dist = round((hand_result.landmark[8].x - Controller.pinchstartxcoord) * 10, 1)
        return dist

    @staticmethod
    def changesystembrightness():
        """Incrementally adjusts system brightness based on pinch movement delta."""
        if not WINDOWS_FEATURES_AVAILABLE:
            return  # Gracefully skip on macOS/Linux
        currentBrightnessLv = sbcontrol.get_brightness(display=0) / 100.0
        # Use smaller increment for smoother control
        currentBrightnessLv += Controller.pinchlv * 0.02
        if currentBrightnessLv > 1.0:
            currentBrightnessLv = 1.0
        elif currentBrightnessLv < 0.0:
            currentBrightnessLv = 0.0
        sbcontrol.set_brightness(int(100 * currentBrightnessLv), display=0)

    @staticmethod
    def changesystemvolume():
        """Incrementally adjusts system volume based on pinch movement delta."""
        if not WINDOWS_FEATURES_AVAILABLE:
            return  # Gracefully skip on macOS/Linux
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        currentVolumeLv = volume.GetMasterVolumeLevelScalar()
        # Use smaller increment for smoother control
        currentVolumeLv += Controller.pinchlv * 0.02
        if currentVolumeLv > 1.0:
            currentVolumeLv = 1.0
        elif currentVolumeLv < 0.0:
            currentVolumeLv = 0.0
        volume.SetMasterVolumeLevelScalar(currentVolumeLv, None)

    @staticmethod
    def scrollVertical():
        """Scrolls on screen vertically."""
        pyautogui.scroll(120 if Controller.pinchlv > 0.0 else -120)

    @staticmethod
    def scrollHorizontal():
        """Scrolls on screen horizontally."""
        pyautogui.keyDown('shift')
        pyautogui.keyDown('ctrl')
        pyautogui.scroll(-120 if Controller.pinchlv > 0.0 else 120)
        pyautogui.keyUp('ctrl')
        pyautogui.keyUp('shift')

    @staticmethod
    def get_position(hand_result):
        """
        Returns coordinates of current hand position.

        Locates hand to get cursor position and stabilizes cursor by
        dampening jerky motion of hand.

        Parameters
        ----------
        hand_result : Object
            Landmarks obtained from mediapipe.

        Returns
        -------
        tuple(float, float)
            (x, y) coordinates for cursor position.
        """
        point = 9
        position = [hand_result.landmark[point].x, hand_result.landmark[point].y]
        sx, sy = pyautogui.size()
        x_old, y_old = pyautogui.position()
        x = int(position[0] * sx)
        y = int(position[1] * sy)

        if Controller.prev_hand is None:
            Controller.prev_hand = x, y

        delta_x = x - Controller.prev_hand[0]
        delta_y = y - Controller.prev_hand[1]

        distsq = delta_x**2 + delta_y**2
        ratio = 1
        Controller.prev_hand = [x, y]

        # Dampening algorithm to stabilize cursor
        if distsq <= 25:
            ratio = 0
        elif distsq <= 900:
            ratio = 0.07 * (distsq ** (1/2))
        else:
            ratio = 2.1

        x, y = x_old + delta_x * ratio, y_old + delta_y * ratio
        return (x, y)

    @staticmethod
    def pinch_control_init(hand_result):
        """Initializes attributes for pinch gesture."""
        Controller.pinchstartxcoord = hand_result.landmark[8].x
        Controller.pinchstartycoord = hand_result.landmark[8].y
        Controller.pinchlv = 0
        Controller.prevpinchlv = 0
        Controller.framecount = 0
        # Initialize previous position for incremental control
        Controller.prev_pinch_x = hand_result.landmark[8].x
        Controller.prev_pinch_y = hand_result.landmark[8].y
        Controller.pinchdirectionflag = None

    @staticmethod
    def pinch_control(hand_result, controlHorizontal, controlVertical):
        """
        Calls 'controlHorizontal' or 'controlVertical' based on pinch movement delta.
        Uses incremental control - changes are applied based on how much you move.

        Parameters
        ----------
        hand_result : Object
            Landmarks obtained from mediapipe.
        controlHorizontal : callback function
            Function associated with horizontal pinch gesture.
        controlVertical : callback function
            Function associated with vertical pinch gesture.

        Returns
        -------
        None
        """
        current_x = hand_result.landmark[8].x
        current_y = hand_result.landmark[8].y

        # Calculate delta from previous position
        delta_x = (current_x - Controller.prev_pinch_x) * 10  # Scale for sensitivity
        delta_y = (Controller.prev_pinch_y - current_y) * 10  # Inverted for natural control

        # Determine direction if not set yet (first significant movement)
        if Controller.pinchdirectionflag is None:
            if abs(delta_x) > 0.15 or abs(delta_y) > 0.15:
                Controller.pinchdirectionflag = abs(delta_x) > abs(delta_y)

        # Apply control based on direction
        if Controller.pinchdirectionflag is not None:
            if Controller.pinchdirectionflag:  # Horizontal
                if abs(delta_x) > 0.05:  # Minimum threshold to avoid jitter
                    Controller.pinchlv = delta_x
                    controlHorizontal()
                    Controller.prev_pinch_x = current_x
            else:  # Vertical
                if abs(delta_y) > 0.05:  # Minimum threshold to avoid jitter
                    Controller.pinchlv = delta_y
                    controlVertical()
                    Controller.prev_pinch_y = current_y

    @staticmethod
    def handle_controls(gesture, hand_result):
        """
        Implements all gesture functionality.

        Routes detected gestures to appropriate control functions.

        Parameters
        ----------
        gesture : int
            Gesture code from Gest enum.
        hand_result : Object
            Landmarks obtained from mediapipe.

        Returns
        -------
        None
        """
        x, y = None, None
        if gesture != Gest.PALM:
            x, y = Controller.get_position(hand_result)

        # Flag reset
        if gesture != Gest.FIST and Controller.grabflag:
            Controller.grabflag = False
            pyautogui.mouseUp(button="left")

        if gesture != Gest.PINCH_MAJOR and Controller.pinchmajorflag:
            Controller.pinchmajorflag = False

        if gesture != Gest.PINCH_MINOR and Controller.pinchminorflag:
            Controller.pinchminorflag = False

        # Gesture implementation
        if gesture == Gest.V_GEST:
            Controller.flag = True
            pyautogui.moveTo(x, y, _pause=False)

        elif gesture == Gest.FIST:
            if not Controller.grabflag:
                Controller.grabflag = True
                pyautogui.mouseDown(button="left")
            pyautogui.moveTo(x, y, _pause=False)

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
            Controller.pinch_control(hand_result, Controller.scrollHorizontal, Controller.scrollVertical)

        elif gesture == Gest.PINCH_MAJOR:
            if Controller.pinchmajorflag == False:
                Controller.pinch_control_init(hand_result)
                Controller.pinchmajorflag = True
            Controller.pinch_control(hand_result, Controller.changesystembrightness, Controller.changesystemvolume)
