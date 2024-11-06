# =======================
# Import the necessary libraries
# =======================

import signal
import time
import threading

import zenoh

# =======================
# Import specific libraries for this node
# =======================

import cv2

import graph

import random

random.seed(42)

import numpy as np

import serial

# =======================
# Import the message class
# =======================

from message import ProcessedImageData

import struct


def read_i16(f):
    return struct.unpack("<h", bytearray(f.read(2)))[0]


def read_i32(f):
    return struct.unpack("<l", bytearray(f.read(4)))[0]


def write_i16(f, value):
    f.write(struct.pack("<h", value))


def write_i32(f, value):
    f.write(struct.pack("<l", value))


def envoiCmdi(arduino, cmd, arg1, arg2, arg3, arg4):
    arduino.write(cmd)
    write_i16(arduino, arg1)
    write_i16(arduino, arg2)
    write_i16(arduino, arg3)
    write_i16(arduino, arg4)

    rep = b""
    while rep == b"":  # attend l'acquitement du B2
        rep = arduino.readline()

def resetENC(arduino):
    envoiCmdi(arduino, b"B", 0, 0, 0, 0)

def recupCmdl(arduino, cmd):
    arduino.write(cmd)
    val1 = read_i32(arduino)
    val2 = read_i32(arduino)

    return val1, val2


def carAdvance(arduino, v1, v2):
    envoiCmdi(arduino, b"C", v1, v2, 0, 0)

class Node:
    def __init__(self):
        # =======================
        # Register signal handlers
        # =======================

        signal.signal(signal.SIGINT, self.ctrl_c_signal)
        signal.signal(signal.SIGTERM, self.ctrl_c_signal)

        self.running = True
        self.mutex = threading.Lock()

        # =======================
        # Complete here with your own variables
        # =======================

        self.arduino = serial.Serial(port="/dev/ttyACM0", baudrate=115200, timeout=0.1)
        rep = " "  # on vide la liaison série
        while rep != b"":
            rep = self.arduino.readline()
        print("Connection à l'arduino")

        time.sleep(2)  # on attend 2s pour que la carte soit initialisée

        self.arduino.write(b"A22")  # demande de connection avec acquitement par OK
        rep = self.arduino.readline()
        if rep.split()[0] == b"OK":
            print("Connection ok")

            self.arduino.write(b"I0")
            rep = b""
            while rep == b"":  # attend l'acquitement du B2
                rep = self.arduino.readline()
            print(rep.decode())

        # state will be either "FRONT","LEFT","RIGHT", "90RIGHT", "90LEFT", "STOP"
        self.state = "FRONT"
        self.grace_timer = None

        self.intersections = None

        self.manoeuvre_enc = None
        self.padding_enc = None

        self.tube_x = 20

        self.left_treshold = -self.tube_x - 5
        self.right_treshold = self.tube_x + 5

        self.robot = graph.Robot(1, 1, 0)

        # =======================
        # Create zenoh session
        # =======================

        config = zenoh.Config.from_file("raspberry/zenoh_config.json")
        self.session = zenoh.open(config)

        # =======================
        # Create zenoh stop handler
        # =======================

        self.stop_handler = self.session.declare_subscriber(
            "happywheels/stop", self.zenoh_stop_signal
        )

        # =======================
        # Complete here with your own pub/sub
        # =======================

        self.line_middle_subscriber = self.session.declare_subscriber(
            "happywheels/processed_image_data", self.processed_image_data_callback
        )

    def run(self):
        while True:
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

            # =======================
            # Complete here with your own message
            # =======================

            time.sleep(1)

        # =======================
        # Close the node
        # =======================

        self.close()

    def close(self):
        # =======================
        # Unregister stop handler
        # =======================

        self.stop_handler.undeclare()

        # =======================
        # Complete here with your own cleanup code
        # =======================

        self.line_middle_subscriber.undeclare()

        # =======================
        # Close zenoh session
        # =======================

        self.session.close()

        carAdvance(self.arduino, 0, 0)
        self.arduino.close()

    def get_avaiable_intersections(self, data):
        """
        Return None if no intersection is detected,
        else return the list of possible directions (LEFT, RIGHT, FRONT)
        """

        intersections = None

        if data.max_white > 7500:
            if data.pos_intersection > 128 - 128 // 2: # Check only for NEAR intersections
                if np.max(data.left_histogram) > 2500:
                    intersections = ["90LEFT"]

                if np.max(data.right_histogram) > 2500:
                    if intersections is None:
                        intersections = ["90RIGHT"]
                    else:
                        intersections.append("90RIGHT")

                if np.max(data.top_histogram) > 2500:
                    if intersections is not None:
                        intersections.append("FRONT")

        # print (intersections, data.max_white, data.pos_intersection, data.left_histogram, data.right_histogram, data.top_histogram)

        return intersections

    def update_line_following_state(self, data: ProcessedImageData):
        if self.state == "FRONT":
            if 8000 > data.distance_to_middle > self.right_treshold:
                self.state = "RIGHT"
            elif data.distance_to_middle < self.left_treshold:
                self.state = "LEFT"
        elif self.state == "RIGHT":
            if data.distance_to_middle < self.tube_x:
                self.state = "FRONT"
        elif self.state == "LEFT":
            if 8000 > data.distance_to_middle > -self.tube_x:
                self.state = "FRONT"

    def update_turning_state(self, intersections):
        self.state = "FRONT"
        self.padding_enc = recupCmdl(self.arduino, b"N")
        print("Intersection detected : padding started")

    def update_state(self, data):
        self.intersections = self.get_avaiable_intersections(data)

        if self.intersections is None:
            self.update_line_following_state(data)
        else:
            self.update_turning_state(self.intersections)

    def move(self):
        if self.state == "FRONT":
            carAdvance(self.arduino, 200, 200)
        elif self.state == "LEFT":
            carAdvance(self.arduino, 255, 100)
        elif self.state == "RIGHT":
            carAdvance(self.arduino, 100, 255)
        elif self.state == "90LEFT":
            carAdvance(self.arduino, 255, -255)
        elif self.state == "90RIGHT":
            carAdvance(self.arduino, -255, 255)
        elif self.state == "STOP":
            carAdvance(self.arduino, 0, 0)

    def processed_image_data_callback(self, sample):
        data = ProcessedImageData.deserialize(sample.payload.to_bytes())

        encoder = recupCmdl(self.arduino, b"N")

        if self.manoeuvre_enc is not None:
            turn_terminated = False

            if self.state == "90RIGHT":
                if encoder[0] - self.manoeuvre_enc[0] < -189 and encoder[1] - self.manoeuvre_enc[1] > 264:
                    turn_terminated = True
            elif self.state == "90LEFT":
                if encoder[1] - self.manoeuvre_enc[1] < -189 and encoder[0] - self.manoeuvre_enc[0] > 264:
                    turn_terminated = True

            if turn_terminated == True:
                self.manoeuvre_enc = None

                if self.state == "90RIGHT":
                    self.robot.droite()
                elif self.state == "90LEFT":
                    self.robot.gauche()

                self.state = "FRONT"
                self.grace_timer = time.time()
                print("Manoeuver ended : grace period started")

        if self.grace_timer is not None:
            if time.time() - self.grace_timer > 0.5:
                self.grace_timer = None
                print("Grace period ended")

        if self.padding_enc is not None:
            if encoder[0] - self.padding_enc[0] > 70 and encoder[1] - self.padding_enc[1] > 70:
                self.padding_enc = None
                self.robot.avance()

                print("Padding ended : ready for manoeuver")
                enc1, enc2 = recupCmdl(self.arduino, b"N")
                print(enc1, enc2)

                itin = self.robot.move_to(4,3)
                self.state = itin

                if self.state != "STOP" and self.state != "FRONT"
                    self.manoeuvre_enc = recupCmdl(self.arduino, b"N")

        if self.state != "STOP":
            if self.state == "FRONT" and self.manoeuvre_enc is not None:
                self.update_line_following_state(data)
            elif self.manoeuvre_enc is None and self.padding_enc is None and self.grace_timer is None:
                self.update_state(data)
            elif self.grace_timer is not None:
                self.update_line_following_state(data)

        print (self.state, self.manoeuvre_enc, self.padding_enc, self.grace_timer)

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
