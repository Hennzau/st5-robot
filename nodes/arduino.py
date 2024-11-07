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

import serial

import numpy as np

import struct

# =======================
# Import the message class
# =======================

from message import MotorControl, IRData, EncoderData


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


def recupCmdi(arduino, cmd):
    arduino.write(cmd)
    val1 = read_i16(arduino)
    val2 = read_i16(arduino)
    val3 = read_i16(arduino)
    val4 = read_i16(arduino)

    return val1, val2, val3, val4


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
        self.serial_mutex = threading.Lock()

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

        # =======================
        # Create zenoh session
        # =======================

        config = zenoh.Config.from_file("rpi_zenoh.json")
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

        self.ir_publisher = self.session.declare_publisher("happywheels/ir")
        self.encoder_publisher = self.session.declare_publisher("happywheels/encoder")
        self.motor_control_subscriber = self.session.declare_subscriber(
            "happywheels/motor_control", self.motor_control_callback
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

            self.serial_mutex.acquire()
            v1, v2 = recupCmdl(self.arduino, b"N")
            tim, tim2, ir, dum1 = recupCmdi(self.arduino, b"R")
            self.serial_mutex.release()

            encoder = EncoderData(
                left=v2,
                right=v1,
            )

            self.encoder_publisher.put(EncoderData.serialize(encoder))

            volts = ir * 5 / 1024

            if volts != 0:
                distcm = 0.0
                if volts < 1:
                    distcm = 28.0 / volts
                else:
                    volts = volts - 0.28
                    distcm = 20.2 / volts

                ir = IRData(distance=distcm)

                self.ir_publisher.put(IRData.serialize(ir))

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

        self.motor_control_subscriber.undeclare()
        self.ir_publisher.undeclare()
        self.encoder_publisher.undeclare()

        # =======================
        # Close zenoh session
        # =======================

        self.session.close()

        carAdvance(self.arduino, 0, 0)
        self.arduino.close()

    def motor_control_callback(self, sample):
        motor_control = MotorControl.deserialize(sample.payload.to_bytes())

        self.serial_mutex.acquire()
        carAdvance(self.arduino, motor_control.speed_left, motor_control.speed_right)
        self.serial_mutex.release()

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
