import signal
import time
import threading

import cv2

import random

random.seed(42)

import numpy as np

from controller import Robot
from controller import Camera

from dataclasses import dataclass

from pycdr2 import IdlStruct
from pycdr2.types import uint32, float32, uint8
from typing import List

@dataclass
class ProcessedImageData(IdlStruct):
    distance_to_middle: float32
    pos_intersection: float32
    max_white: float32
    left_histogram: float32
    right_histogram: float32
    top_histogram: float32

class Node:
    def __init__(self):
        # =======================
        # Register signal handlers
        # =======================

        signal.signal(signal.SIGINT, self.ctrl_c_signal)
        signal.signal(signal.SIGTERM, self.ctrl_c_signal)

        self.running = True
        self.mutex = threading.Lock()

        # state will be either "FRONT","LEFT","RIGHT", "90RIGHT", "90LEFT", "STOP"
        self.state = "FRONT"
        self.timer = None
        self.padding_timer = None

        self.tube_x = 20

        self.left_treshold = -self.tube_x - 5
        self.right_treshold = self.tube_x + 5

        # =======================
        #
        # =======================

        self.robot = Robot()
        self.time_step = 64

        self.camera = self.robot.getDevice('camera')
        self.camera.enable(self.time_step)

        self.wheels = []
        self.wheels_names = ['wheel1', 'wheel2', 'wheel3', 'wheel4']
        for i in range(4):
            self.wheels.append(self.robot.getDevice(self.wheels_names[i]))
            self.wheels[i].setPosition(float('inf'))
            self.wheels[i].setVelocity(0.0)

    def run(self):
        while self.robot.step(self.time_step) != -1:
            # =======================
            # Check if the node should stop
            # =======================

            self.mutex.acquire()
            running = self.running
            self.mutex.release()

            if not running:
                break

            # =======================
            # Do your own code here
            # =======================

            data = ProcessedImageData(0, 0, 0, 0, 0, 0)

            cameraData = self.camera.getImage()
            image = np.frombuffer(cameraData, np.uint8).reshape((self.camera.getHeight(), self.camera.getWidth(), 4))

            # Read/Write issue
            image = np.copy(image)
            h, w = image.shape[:2]

            # Convert to HSV color space
            blur = cv2.blur(image,(5,5))
            ret,thresh1 = cv2.threshold(blur,168,255,cv2.THRESH_BINARY)
            hsv = cv2.cvtColor(thresh1, cv2.COLOR_RGB2HSV)

            # Define range of white color in HSV
            lower_white = np.array([0, 0, 168])
            upper_white = np.array([172, 111, 255])

            # Threshold the HSV image
            mask = cv2.inRange(hsv, lower_white, upper_white)

            # Remove noise
            kernel_erode = np.ones((6,6), np.uint8)
            eroded_mask = cv2.erode(mask, kernel_erode, iterations=1)
            kernel_dilate = np.ones((4,4), np.uint8)
            dilated_mask = cv2.dilate(eroded_mask, kernel_dilate, iterations=1)

            #
            # Line following
            #

            # Find the different contours and draw them
            contours, hierarchy = cv2.findContours(dilated_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            image = cv2.drawContours(image, contours, -1, (0, 255, 0), 3)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]

            # Only proceed if at least one contour was found
            if len(contours) > 0:

                M = cv2.moments(contours[0])
                # Centroid
                cx = int(M['m10']/M['m00'])
                cy = int(M['m01']/M['m00'])

                # Location of the centroid
                cv2.circle(image, (cx, cy), 10, (0, 0, 255), 3)

                # Distance to the center allowing to turn left or right
                data.distance_to_middle = cx - w/2

                cv2.putText(image, f"{data.distance_to_middle}", (cx, cy), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2, cv2.LINE_AA)

            histogram = np.sum(dilated_mask, axis=1)

            max_white = np.max(histogram)
            pos_intersection = np.argmax(histogram)

            data.pos_intersection = int(np.argmax(histogram))
            data.max_white = max_white

            left_histogram = np.max(np.sum(dilated_mask[:, : w // 8], axis=1))
            right_histogram = np.max(np.sum(dilated_mask[:, 7 * w // 8 :], axis=1))
            top_histogram = np.max(np.sum(dilated_mask[: h // 8, :], axis=0))

            data.left_histogram = left_histogram
            data.right_histogram = right_histogram
            data.top_histogram = top_histogram

            self.processed_image_data(data)

            # Vertical line in the center
            cv2.line(image, (w//2, 0), (w//2, h), (0, 255, 0), 2)
            # Two vertical lines, one at 100px from the center, the other at -100px
            cv2.line(image, (w//2 + self.tube_x, 0), (w//2 + self.tube_x, h), (255, 0, 0), 2)
            cv2.line(image, (w//2 - self.tube_x, 0), (w//2 - self.tube_x, h), (255, 0, 0), 2)

            # Two vertical lines indicating the thresholds
            cv2.line(image, (w//2 + self.right_treshold, 0), (w//2 + self.right_treshold, h), (0, 0, 255), 2)
            cv2.line(image, (w//2 + self.left_treshold, 0), (w//2 + self.left_treshold, h), (0, 0, 255), 2)

            # Turn line
            cv2.line(image, (0, h - h//4), (w, h - h//4), (0, 255, 0), 2)

            cv2.imshow("Image traitée", image)
            cv2.waitKey(1)

        # =======================
        # Close the node
        # =======================

        self.close()

    def close(self):
        pass

    def get_avaiable_intersections(self, data):
        """
        Return None if no intersection is detected,
        else return the list of possible directions (LEFT, RIGHT, FRONT)
        """


        intersections = None

        if data.max_white > 30000:
            if data.pos_intersection > 480 - 480 // 3:

                if np.max(data.left_histogram) > 10000:
                    intersections = ["LEFT"]

                if np.max(data.right_histogram) > 10000:
                    if intersections is None:
                        intersections = ["RIGHT"]
                    else:
                        intersections.append("RIGHT")

                if np.max(data.top_histogram) > 10000:
                    if intersections is not None:
                        intersections.append("FRONT")

        print (intersections, data.max_white, data.pos_intersection, data.left_histogram, data.right_histogram, data.top_histogram)

        return intersections

    def update_line_following_state(self, data):
        if self.state == "FRONT":
            if data.distance_to_middle > self.right_treshold:
                self.state = "RIGHT"
            elif data.distance_to_middle < self.left_treshold:
                self.state = "LEFT"
        elif self.state == "RIGHT":
            if data.distance_to_middle < self.tube_x:
                self.state = "FRONT"
        elif self.state == "LEFT":
            if data.distance_to_middle > -self.tube_x:
                self.state = "FRONT"

    def update_turning_state(self, intersections):
        if self.padding_timer is None:
            self.padding_timer = time.time()
            self.state = "FRONT"

        elif time.time() - self.padding_timer > 1.0:
            self.padding_timer = None
            self.state = "STOP"
            self.timer = time.time()

    def update_state(self, data):
        intersections = self.get_avaiable_intersections(data)

        if intersections is None:
            self.update_line_following_state(data)
        else:
            self.update_turning_state(intersections)

    def move(self):
        if self.state == "FRONT":
            self.wheels[0].setVelocity(1 * 10)
            self.wheels[1].setVelocity(1 * 10)
            self.wheels[2].setVelocity(1 * 10)
            self.wheels[3].setVelocity(1 * 10)
        elif self.state == "LEFT":
            self.wheels[0].setVelocity(0 * 10)
            self.wheels[1].setVelocity(1 * 10)
            self.wheels[2].setVelocity(0 * 10)
            self.wheels[3].setVelocity(1 * 10)
        elif self.state == "RIGHT":
            self.wheels[0].setVelocity(1 * 10)
            self.wheels[1].setVelocity(0 * 10)
            self.wheels[2].setVelocity(1 * 10)
            self.wheels[3].setVelocity(0 * 10)
        elif self.state == "90RIGHT":
            self.wheels[0].setVelocity(1 * 10)
            self.wheels[1].setVelocity(-1 * 10)
            self.wheels[2].setVelocity(1 * 10)
            self.wheels[3].setVelocity(-1 * 10)
        elif self.state == "90LEFT":
            self.wheels[0].setVelocity(-1 * 10)
            self.wheels[1].setVelocity(1 * 10)
            self.wheels[2].setVelocity(-1 * 10)
            self.wheels[3].setVelocity(1 * 10)
        elif self.state == "STOP":
            self.wheels[0].setVelocity(0)
            self.wheels[1].setVelocity(0)
            self.wheels[2].setVelocity(0)
            self.wheels[3].setVelocity(0)

    def processed_image_data(self, data):
        if self.timer is not None:
            if time.time() - self.timer > 1.0:
                self.timer = None
                self.state = "FRONT"

        if self.timer is None:
            self.update_state(data)

        self.move()

    def ctrl_c_signal(self, signum, frame):
        # Stop the node

        self.mutex.acquire()
        self.running = False
        self.mutex.release()

        # Put your cleanup code here

    def zenoh_stop_signal(self, sample):
        # Stop the node

        self.mutex.acquire()
        self.running = False
        self.mutex.release()


if __name__ == "__main__":
    node = Node()
    node.run()
