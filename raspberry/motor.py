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

import numpy as np

import serial

# =======================
# Import the message class
# =======================

from message import LineMiddle

import struct

def read_i16(f):
    return struct.unpack('<h', bytearray(f.read(2)))[0]

def read_i32(f):
    return struct.unpack('<l', bytearray(f.read(4)))[0]

def write_i16(f, value):
    f.write(struct.pack('<h', value))

def write_i32(f, value):
    f.write(struct.pack('<l', value))

def envoiCmdi(arduino, cmd,arg1,arg2,arg3,arg4):
    arduino.write(cmd)
    write_i16(arduino, arg1)
    write_i16(arduino, arg2)
    write_i16(arduino, arg3)
    write_i16(arduino, arg4)
    AttAcquit(arduino)

def envoiCmdl(arduino, cmd,arg1,arg2):
    arduino.write(cmd)
    write_i32(arduino, arg1)
    write_i32(arduino, arg2)
    AttAcquit(arduino)

def recupCmdi(arduino,cmd):
    arduino.write(cmd)
    val1=read_i16(arduino)
    val2=read_i16(arduino)
    val3=read_i16(arduino)
    val4=read_i16(arduino)
    return val1,val2,val3,val4
    AttAcquit(arduino)

def recupCmdl(arduino, cmd):
    arduino.write(cmd)
    val1=read_i32(arduino)
    val2=read_i32(arduino)
    return val1,val2
    AttAcquit(arduino)


def AttAcquit(arduino):
    rep=b''
    while rep==b'':					# attend l'acquitement du B2
        rep=arduino.readline()

def    resetENC(arduino):
    envoiCmdi(arduino, b'B',0,0,0,0)

def    carStop(arduino):
    envoiCmdi(arduino, b'C',0,0,0,0)

def    carStopS(arduino):
    envoiCmdi(arduino, b'D',0,0,20,0)

def    carAdvance(arduino, v1,v2):
    envoiCmdi(arduino, b'C',v1,v2,0,0)

def  carAdvanceS(arduino, v1,v2,v3):
    envoiCmdi(arduino, b'D',v1,v2,v3,0)

def  carBack(arduino, v1,v2):
    envoiCmdi(arduino, b'C',-v1,-v2,0,0)

def  carBackS(arduino, v1,v2,v3):
    envoiCmdi(arduino, b'D',-v1,-v2,v3,0)

def  carTurnLeft(arduino, v1,v2):
    envoiCmdi(arduino, b'C',v1,-v2,0,0)

def  carTurnRight(arduino, v1,v2):
    envoiCmdi(arduino, b'C',-v1,v2,0,0)

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

        self.arduino = serial.Serial(port='/dev/ttyACM0', baudrate=115200, timeout=0.1)
        rep=' '   # on vide la liaison série
        while rep!=b'':
          rep = self.arduino.readline()
        print ("Connection à l'arduino")

        time.sleep(2)			# on attend 2s pour que la carte soit initialisée

        self.arduino.write(b'A22')		# demande de connection avec acquitement par OK
        rep = self.arduino.readline()
        if rep.split()[0]==b'OK':
            print("Connection ok")

            self.arduino.write(b'I0')
            AttAcquit(self.arduino)
            print(rep.decode())

        self.current_state = 'CENTER'
        self.speed_constant = 500  # Speed constant to control the speed of the robot
        self.tube_x = 20

        self.left_treshold = -self.tube_x - 10
        self.right_treshold = self.tube_x + 10
        # =======================
        # Create zenoh session
        # =======================

        config = zenoh.Config.from_file("raspberry/zenoh_config.json")
        self.session = zenoh.open(config)

        # =======================
        # Create zenoh stop handler
        # =======================

        self.stop_handler = self.session.declare_subscriber("happywheels/stop", self.zenoh_stop_signal)

        # =======================
        # Complete here with your own pub/sub
        # =======================

        self.line_middle_subscriber = self.session.declare_subscriber("happywheels/line_middle", self.line_middle_callback)

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


    def update_state(self, distance):
        if self.current_state == 'CENTER':
            if distance > self.right_treshold:
                self.current_state = 'RIGHT'
            elif distance < self.left_treshold:
                self.current_state = 'LEFT'
        elif self.current_state == 'RIGHT':
            if distance < self.tube_x:
                self.current_state = 'CENTER'
        elif self.current_state == 'LEFT':
            if distance > -self.tube_x:
                self.current_state = 'CENTER'

    def set_wheel_velocities(self):
        if self.current_state == 'RIGHT':
            carTurnRight(self.arduino, 250, 250)
        elif self.current_state == 'LEFT':
            carTurnLeft(self.arduino, 250, 250)
        else:  # CENTER
            carAdvance(self.arduino, 250, 250)

    def line_middle_callback(self, sample):
        line_middle = LineMiddle.deserialize(sample.payload.to_bytes())
        distance = line_middle.value

        self.update_state(distance)
        # print(self.current_state)
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
