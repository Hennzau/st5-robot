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

        self.padding_timer = None
        
        self.intersections = None
        
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
            
        
        # Sensors and variables to save the readings at the start of a manoeuver
        
        self.r_sensor_mem = None
        self.l_sensor_mem = None
        
        self.sensors = []
        self.sensors_names = ['s1', 's2', 's3', 's4']
        for i in range(4):
            self.sensors.append(self.robot.getDevice(self.sensors_names[i]))
            self.sensors[i].enable(self.time_step)
        
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
            else:
                data.distance_to_middle = None # No centroid found, useful when turning
            
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

            # # Print the readings of the sensors
            # for i in range(4):
            #     print(f"Sensor {i+1} : {self.sensors[i].getValue()}")
            
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

    def get_available_intersections(self, data):
        """
        Return None if no intersection is detected,
        else return the list of possible directions (LEFT, RIGHT, FRONT)
        """


        intersections = None

        if data.max_white > 50000:
            if data.pos_intersection > 480 - 480 // 4:

                if np.max(data.left_histogram) > 10000:
                    print(np.max(data.left_histogram))
                    print(np.argmax(data.left_histogram))
                    intersections = ["90LEFT"]

                if np.max(data.right_histogram) > 10000:
                    print(np.max(data.right_histogram))
                    print(np.argmax(data.right_histogram))
                    if intersections is None:
                        intersections = ["90RIGHT"]
                    else:
                        intersections.append("90RIGHT")

                if np.max(data.top_histogram) > 20000:
                    if intersections is not None:
                        intersections.append("FRONT")

        # print (intersections, data.max_white, data.pos_intersection, data.left_histogram, data.right_histogram, data.top_histogram)

        return intersections

    def update_line_following_state(self, data):
        print("Line following")
        
        if data.distance_to_middle is None:
            return
        
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
        self.state = "FRONT"
        self.padding_timer = time.time()
        print("Intersection detected : padding started")

    def update_state(self, data):
        self.intersections = self.get_available_intersections(data)

        if self.intersections is None:
            self.update_line_following_state(data)
        else:
            self.update_turning_state(self.intersections)

    def move(self):
        if self.state == "FRONT":
            self.wheels[0].setVelocity(1 * 3)
            self.wheels[1].setVelocity(1 * 3)
            self.wheels[2].setVelocity(1 * 3)
            self.wheels[3].setVelocity(1 * 3)
        elif self.state == "LEFT":
            self.wheels[0].setVelocity(0 * 3)
            self.wheels[1].setVelocity(1 * 3)
            self.wheels[2].setVelocity(0 * 3)
            self.wheels[3].setVelocity(1 * 3)
        elif self.state == "RIGHT":
            self.wheels[0].setVelocity(1 * 3)
            self.wheels[1].setVelocity(0 * 3)
            self.wheels[2].setVelocity(1 * 3)
            self.wheels[3].setVelocity(0 * 3)
        elif self.state == "90RIGHT":
            self.wheels[0].setVelocity(1 * 3)
            self.wheels[1].setVelocity(-1 * 3)
            self.wheels[2].setVelocity(1 * 3)
            self.wheels[3].setVelocity(-1 * 3)
        elif self.state == "90LEFT":
            self.wheels[0].setVelocity(-1 * 3)
            self.wheels[1].setVelocity(1 * 3)
            self.wheels[2].setVelocity(-1 * 3)
            self.wheels[3].setVelocity(1 * 3)
        elif self.state == "STOP":
            self.wheels[0].setVelocity(0)
            self.wheels[1].setVelocity(0)
            self.wheels[2].setVelocity(0)
            self.wheels[3].setVelocity(0)
    
    def turn(self, data):
        # if self.state == "90RIGHT":
        #     if data.distance_to_middle == None:
        #         self.state = "90RIGHT" # Nothing changes
        #         print("Still turning right")
        #     elif data.distance_to_middle > 50:
        #         print("Line back")
        #         self.state = "FRONT"
        # elif self.state == "90LEFT":
        #     if data.distance_to_middle == None:
        #         self.state = "90LEFT"
        #         print("Still turning left")
        #     elif data.distance_to_middle < -50:
        #         print("Line back")
        #         self.state = "FRONT"
        if self.state == "90RIGHT":
            err = abs(self.sensors[0].getValue() - self.r_sensor_mem)
            print(err)
            if err < 3.8:
                self.state = "90RIGHT" # Nothing changes
                print("Still turning right")
            else:
                print("Turn completed")
                self.state = "FRONT"
        elif self.state == "90LEFT":
            err = abs(self.sensors[1].getValue() - self.l_sensor_mem)
            print(err)
            if err < 3.8:
                self.state = "90LEFT"
                print("Still turning left")
            else:
                print("Turn completed")
                self.state = "FRONT"

    def processed_image_data(self, data):

        if self.padding_timer is not None:
            if time.time() - self.padding_timer > 1.1:
                self.timer = time.time()
                self.padding_timer = None
                print("Padding ended : ready for manoeuver")
                
                self.state = random.choice(self.intersections)
                print(self.state)
                
                # Save the sensors values at the start of the manoeuver
                self.r_sensor_mem = self.sensors[0].getValue()
                self.l_sensor_mem = self.sensors[1].getValue()
                
                self.turn(data)

        if self.padding_timer is None and self.state not in ["90RIGHT", "90LEFT"]:
            self.update_state(data)
        else:
            self.turn(data)
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