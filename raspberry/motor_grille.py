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
    AttAcquit(arduino)


def envoiCmdl(arduino, cmd, arg1, arg2):
    arduino.write(cmd)
    write_i32(arduino, arg1)
    write_i32(arduino, arg2)
    AttAcquit(arduino)


def recupCmdi(arduino, cmd):
    arduino.write(cmd)
    val1 = read_i16(arduino)
    val2 = read_i16(arduino)
    val3 = read_i16(arduino)
    val4 = read_i16(arduino)
    return val1, val2, val3, val4
    AttAcquit(arduino)


def recupCmdl(arduino, cmd):
    arduino.write(cmd)
    val1 = read_i32(arduino)
    val2 = read_i32(arduino)
    return val1, val2
    AttAcquit(arduino)


def AttAcquit(arduino):
    rep = b""
    while rep == b"":  # attend l'acquitement du B2
        rep = arduino.readline()


def resetENC(arduino):
    envoiCmdi(arduino, b"B", 0, 0, 0, 0)


def carStop(arduino):
    envoiCmdi(arduino, b"C", 0, 0, 0, 0)


def carStopS(arduino):
    envoiCmdi(arduino, b"D", 0, 0, 20, 0)


def carAdvance(arduino, v1, v2):
    envoiCmdi(arduino, b"C", v1, v2, 0, 0)


def carAdvanceS(arduino, v1, v2, v3):
    envoiCmdi(arduino, b"D", v1, v2, v3, 0)


def carBack(arduino, v1, v2):
    envoiCmdi(arduino, b"C", -v1, -v2, 0, 0)


def carBackS(arduino, v1, v2, v3):
    envoiCmdi(arduino, b"D", -v1, -v2, v3, 0)


def carTurnLeft(arduino, v1, v2):
    envoiCmdi(arduino, b"C", v1, -v2, 0, 0)


def carTurnRight(arduino, v1, v2):
    envoiCmdi(arduino, b"C", -v1, v2, 0, 0)


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
            AttAcquit(self.arduino)
            print(rep.decode())

        self.current_state = {'pos':'CENTER','intersection':'NONE', 'intersection_noted' : False, 'stop': False, 'possibilities' : []}
        self.speed_constant = 500  # Speed constant to control the speed of the robot
        self.tube_x = 20

        self.left_treshold = -self.tube_x - 5
        self.right_treshold = self.tube_x + 5
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
            "happywheels/line_middle", self.line_middle_callback
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
        self.arduino.close()

    def update_turn(self, distance):
        if self.current_state['pos'] == "CENTER":
            if distance > self.right_treshold:
                self.current_state['pos'] = "RIGHT"
            elif distance < self.left_treshold:
                self.current_state['pos'] = "LEFT"
        elif self.current_state['pos'] == "RIGHT":
            if distance < self.tube_x:
                self.current_state['pos'] = "CENTER"
        elif self.current_state['pos'] == "LEFT":
            if distance > -self.tube_x:
                self.current_state['pos'] = "CENTER"

    def update_intersection(self, max_white, pos_intersection):
        # Check if the max value is above a certain threshold
        if max_white > 10000: # Value to be adjusted
            self.current_state['intersection'] = True
            if pos_intersection > 128 - 128//4:
                self.current_state['intersection'] = 'NEAR'
            else:
                self.current_state['intersection'] = 'DETECTED'

        else:
            self.current_state['intersection'] = 'NONE'

    def set_wheel_velocities(self):
        if not self.current_state['stop']:
            if self.current_state['intersection'] == 'NEAR' and  self.current_state['possibilities'] != []:
                order = random.choice(self.current_state['possibilities'])

                if order == 'LEFT':
                    carAdvance(self.arduino, 255, 100)
                    time.sleep(0.5)
                elif order == 'RIGHT':
                    carAdvance(self.arduino, 100, 255)
                    time.sleep(0.5)

            else:
                if self.current_state['pos'] == "RIGHT":
                    carAdvance(self.arduino, 100, 255)
                elif self.current_state['pos'] == "LEFT":
                    carAdvance(self.arduino, 255, 100)
                else:
                    carAdvance(self.arduino, 200, 200)
        else:
            carAdvance(self.arduino, 0, 0)

    def line_middle_callback(self, sample):
        line_middle = ProcessedImageData.deserialize(sample.payload.to_bytes())

        print(line_middle.max_white, line_middle.left_histogram, line_middle.right_histogram, line_middle.top_histogram)
        print (self.current_state)

        self.update_turn(line_middle.distance_to_middle)
        self.update_intersection(line_middle.max_white, line_middle.pos_intersection)

        if self.current_state['intersection'] in ['DETECTED','NEAR']:
            if np.max(line_middle.left_histogram) > 2500:
                self.current_state['possibilities'].append('LEFT') if 'LEFT' not in self.current_state['possibilities'] else None
            if np.max(line_middle.right_histogram) > 2500:
                self.current_state['possibilities'].append('RIGHT') if 'RIGHT' not in self.current_state['possibilities'] else None
            if np.max(line_middle.top_histogram) > 2500:
                self.current_state['possibilities'].append('STRAIGHT') if 'STRAIGHT' not in self.current_state['possibilities'] else None
            elif 'STRAIGHT' in self.current_state['possibilities']: # This condition should be useless for left and right
                self.current_state['possibilities'].remove('STRAIGHT')
        else:
            self.current_state['possibilities'] = []

        self.set_wheel_velocities()


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
