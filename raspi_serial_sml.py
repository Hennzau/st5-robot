#########################################################################
# CENTRALESUPELEC : ST5 53 integration week
#
# Basic human-machine interface to test robots
#
#########################################################################
# Authors : Erwan Libessart
# Modifications by Morgan Roger
# TODO : translate to English where needed
#########################################################################

from __future__ import division, print_function

import logging
import signal
import time
import numpy as np
from time import sleep
from picamera import PiCamera
import struct

import queue

from robust_serial import write_order, Order, write_i8, write_i16, read_i16, read_i32, read_i8
from robust_serial.utils import open_serial_port
from constants import BAUDRATE

emptyException = queue.Empty
fullException = queue.Full
serial_file = None
camera = PiCamera()
motor_speed = 100
step_length = 5


def main():
    test_camera()
    connect_to_arduino()

    print("Welcome to raspi_serial.py")
    print("Press enter to validate your commands")
    print("Enter h to get the list of valid commands")
    cmd_str = ''
    while cmd_str != 'q':
        cmd_str = input("Enter your command: ")
        process_cmd(cmd_str)

    camera.close()


def test_camera():
    global camera
    camera.start_preview()
    sleep(2)
    my_file = open('test_photo.jpg', 'wb')
    camera.capture(my_file)
    # At this point my_file.flush() has been called, but the file has
    # not yet been closed
    my_file.close()
    camera.stop_preview()


def connect_to_arduino():
    global serial_file
    try:
        # Open serial port (for communication with Arduino)
        serial_file = open_serial_port(
            serial_port="/dev/ttyACM0",
            baudrate=BAUDRATE)
    except Exception as e:
        print('exception')
        raise e

    is_connected = False
    # Initialize communication with Arduino
    while not is_connected:
        print("Trying connection to Arduino...")
        write_order(serial_file, Order.HELLO)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        bytes_array = bytearray(serial_file.read(1))
        if not bytes_array:
            time.sleep(2)
            continue
        byte = bytes_array[0]
        if byte == Order.HELLO.value:
            is_connected = True

    time.sleep(2)
    c = 1
    while (c!=b''):
        c = serial_file.read(1)


def process_cmd(cmd):
    global motor_speed
    global step_length
    cmd_type = {
      "[q]uit": (cmd == 'q'),
      "[h]elp": (cmd == 'h'),
      "[e]ncoder values": (cmd == 'e'),
      "[z]ero setting encoders": (cmd == 'z'),
      "(%) set motor speed percentage": (cmd.isdigit()),
      "[f]orward step": (cmd == 'f'),
      "[l] left step": (cmd == 'l'),
      "[r] right step": (cmd == 'r'),
      "[b]ackward step": (cmd == 'b'),
      "[lb] left step back": (cmd == 'lb'),
      "[rb] right step back": (cmd == 'rb'),
      "[ff]orward": (cmd == 'ff'),
      "[bb]ackward": (cmd == 'bb'),
      "[tl] turn left": (cmd == 'tl'),
      "[tr] turn right": (cmd == 'tr'),
      "[p]ause motors": (cmd == 'p'),
      "[s]ervo move": (cmd == 's'),
               }

    if cmd_type["[q]uit"]:
        print("Goodbye...")
    elif cmd_type["[h]elp"]:
        for key in cmd_type.keys():
            print(key)
    elif cmd_type["[e]ncoder values"]:
        print('left encoder : ', lectureCodeurGauche())
        print('right encoder : ', lectureCodeurDroit())
    elif cmd_type["[z]ero setting encoders"]:
        print("Resetting encoders...")
        write_order(serial_file, Order.RESETENC)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
        print('left encoder : ', lectureCodeurGauche())
        print('right encoder : ', lectureCodeurDroit())
    elif cmd_type["(%) set motor speed percentage"]:
        motor_speed = int(cmd)
        print("Speed set to " + cmd + "%")
    elif cmd_type["[f]orward step"]:
        print("Moving forward at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, motor_speed) #valeur moteur droit
        write_i8(serial_file, motor_speed) #valeur moteur gauche
        read_i16(serial_file)
        time.sleep(step_length)
        print('stop motors')
        write_order(serial_file, Order.STOP)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
    elif cmd_type["[l] left step"]:
        print("Forward left at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, 0) #valeur moteur droit
        write_i8(serial_file, motor_speed) #valeur moteur gauche
        read_i16(serial_file)
        time.sleep(step_length)
        print('stop motors')
        write_order(serial_file, Order.STOP)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
    elif cmd_type["[r] right step"]:
        print("Forward right at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, motor_speed) #valeur moteur droit
        write_i8(serial_file, 0) #valeur moteur gauche
        read_i16(serial_file)
        time.sleep(step_length)
        print('stop motors')
        write_order(serial_file, Order.STOP)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
    elif cmd_type["[b]ackward step"]:
        print("Moving backward at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, -motor_speed) #valeur moteur droit
        write_i8(serial_file, -motor_speed) #valeur moteur gauche
        read_i16(serial_file)
        time.sleep(step_length)
        print('stop motors')
        write_order(serial_file, Order.STOP)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
    elif cmd_type["[lb] left step back"]:
        print("Backward left at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, 0) #valeur moteur droit
        write_i8(serial_file, -motor_speed) #valeur moteur gauche
        read_i16(serial_file)
        time.sleep(step_length)
        print('stop motors')
        write_order(serial_file, Order.STOP)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
    elif cmd_type["[rb] right step back"]:
        print("Backward right at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, -motor_speed) #valeur moteur droit
        write_i8(serial_file, 0) #valeur moteur gauche
        read_i16(serial_file)
        time.sleep(step_length)
        print('stop motors')
        write_order(serial_file, Order.STOP)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
    elif cmd_type["[ff]orward"]:
        print("Moving forward at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, motor_speed) #valeur moteur droit
        write_i8(serial_file, motor_speed) #valeur moteur gauche
        read_i16(serial_file)
    elif cmd_type["[bb]ackward"]:
        print("Moving backward at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, -motor_speed) #valeur moteur droit
        write_i8(serial_file, -motor_speed) #valeur moteur gauche
        read_i16(serial_file)
    elif cmd_type["[tl] turn left"]:
        print("Turn left at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, motor_speed) #valeur moteur droit
        write_i8(serial_file, -motor_speed) #valeur moteur gauche
        read_i16(serial_file)
        time.sleep(step_length)
        print('stop motors')
        write_order(serial_file, Order.STOP)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
    elif cmd_type["[tr] turn right"]:
        print("Turn right at " + str(motor_speed) + "%...")
        write_order(serial_file, Order.MOTOR)
        write_i8(serial_file, -motor_speed) #valeur moteur droit
        write_i8(serial_file, motor_speed) #valeur moteur gauche
        read_i16(serial_file)
        time.sleep(step_length)
        print('stop motors')
        write_order(serial_file, Order.STOP)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
    elif cmd_type["[p]ause motors"]:
        print("Stopping...")
        write_order(serial_file, Order.STOP)
        write_i8(serial_file, 0) #padding
        write_i8(serial_file, 0) #padding
        read_i16(serial_file)
#     elif cmd_type["[s]ervo move"]:
#         print("Moving front servo...")
#         write_order(serial_file, Order.SERVO)
#         write_i16(serial_file, 45) #valeur angle servo
#         time.sleep(2)
#         write_order(serial_file, Order.SERVO)
#         write_i16(serial_file, 90) #valeur angle servo
    else:
        print("Invalid command")


def lectureCodeurGauche():
    write_order(serial_file, Order.READENCODERl)
    write_i8(serial_file, 0) #padding
    write_i8(serial_file, 0) #padding
    g = read_i16(serial_file)
    return g


def lectureCodeurDroit():
    write_order(serial_file, Order.READENCODERr)
    write_i8(serial_file, 0) #padding
    write_i8(serial_file, 0) #padding
    d = read_i16(serial_file)
    return d


if __name__ == "__main__":
    main()
