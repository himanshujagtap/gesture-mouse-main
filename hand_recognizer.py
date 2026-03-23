"""
Hand Recognition Module

Converts MediaPipe hand landmarks to recognizable gestures.
"""

import math
from gesture_enums import Gest, HLabel


class HandRecog:
    """
    Convert MediaPipe Landmarks to recognizable Gestures.

    This class processes hand landmarks from MediaPipe and identifies
    gestures based on finger positions and distances.
    """

    def __init__(self, hand_label):
        """
        Constructs all the necessary attributes for the HandRecog object.

        Parameters
        ----------
        hand_label : int
            Represents multi-handedness corresponding to Enum 'HLabel'.

        Attributes
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
        """
        self.finger = 0
        self.ori_gesture = Gest.PALM
        self.prev_gesture = Gest.PALM
        self.frame_count = 0
        self.hand_result = None
        self.hand_label = hand_label

    def update_hand_result(self, hand_result):
        """Update the hand landmarks from MediaPipe."""
        self.hand_result = hand_result

    def get_signed_dist(self, point):
        """
        Returns signed euclidean distance between landmark points.

        Parameters
        ----------
        point : list
            List containing two elements representing landmark point indices.

        Returns
        -------
        float
            Signed distance between the two points.
        """
        sign = -1
        if self.hand_result.landmark[point[0]].y < self.hand_result.landmark[point[1]].y:
            sign = 1
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        dist = math.sqrt(dist)
        return dist * sign

    def get_dist(self, point):
        """
        Returns euclidean distance between landmark points.

        Parameters
        ----------
        point : list
            List containing two elements representing landmark point indices.

        Returns
        -------
        float
            Distance between the two points.
        """
        dist = (self.hand_result.landmark[point[0]].x - self.hand_result.landmark[point[1]].x)**2
        dist += (self.hand_result.landmark[point[0]].y - self.hand_result.landmark[point[1]].y)**2
        dist = math.sqrt(dist)
        return dist

    def get_dz(self, point):
        """
        Returns absolute difference on z-axis between landmark points.

        Parameters
        ----------
        point : list
            List containing two elements representing landmark point indices.

        Returns
        -------
        float
            Absolute z-axis difference between the two points.
        """
        return abs(self.hand_result.landmark[point[0]].z - self.hand_result.landmark[point[1]].z)

    def set_finger_state(self):
        """
        Set 'finger' by computing ratio of distance between finger tip,
        middle knuckle, and base knuckle.

        Determines which fingers are extended based on landmark distances.
        Finger_state: 1 if finger is open, else 0
        """
        if self.hand_result is None:
            return

        points = [[8, 5, 0], [12, 9, 0], [16, 13, 0], [20, 17, 0]]
        self.finger = 0
        self.finger = self.finger | 0  # thumb

        for idx, point in enumerate(points):
            dist = self.get_signed_dist(point[:2])
            dist2 = self.get_signed_dist(point[1:])

            try:
                ratio = round(dist / dist2, 1)
            except:
                ratio = 0

            self.finger = self.finger << 1
            if ratio > 0.5:
                self.finger = self.finger | 1

    def get_gesture(self):
        """
        Returns int representing gesture corresponding to Enum 'Gest'.

        Sets 'frame_count', 'ori_gesture', 'prev_gesture'.
        Handles fluctuations due to noise by requiring consistent
        gesture detection for multiple frames.

        Returns
        -------
        int
            Gesture code from Gest enum.
        """
        if self.hand_result is None:
            return Gest.PALM

        current_gesture = Gest.PALM

        # Check for pinch gestures
        if self.finger in [Gest.LAST3, Gest.LAST4] and self.get_dist([8, 4]) < 0.08:
            if self.hand_label == HLabel.MINOR:
                current_gesture = Gest.PINCH_MINOR
            else:
                current_gesture = Gest.PINCH_MAJOR

        # Check for two-finger gestures (V, two-finger-closed, or middle finger)
        elif Gest.FIRST2 == self.finger:
            point = [[8, 12], [5, 9]]
            dist1 = self.get_dist(point[0])
            dist2 = self.get_dist(point[1])
            ratio = dist1 / dist2

            if ratio > 1.7:
                current_gesture = Gest.V_GEST
            else:
                if self.get_dz([8, 12]) < 0.1:
                    current_gesture = Gest.TWO_FINGER_CLOSED
                else:
                    current_gesture = Gest.MID
        else:
            current_gesture = self.finger

        # Noise filtering: require consistent gesture for multiple frames
        if current_gesture == self.prev_gesture:
            self.frame_count += 1
        else:
            self.frame_count = 0

        self.prev_gesture = current_gesture

        # Update gesture only after 4 consistent frames
        if self.frame_count > 4:
            self.ori_gesture = current_gesture

        return self.ori_gesture
