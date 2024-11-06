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

# =======================
# Import the message class
# =======================

from message import ProcessedData, IRData, EncoderData, MotorControl, NextWaypoint

from graph import Robot

class Node:
    def __init__(self):
        # =======================
        # Register signal handlers
        # =======================

        signal.signal(signal.SIGINT, self.ctrl_c_signal)
        signal.signal(signal.SIGTERM, self.ctrl_c_signal)

        self.running = True
        self.mutex = threading.Lock()
        self.zenoh_mutex = threading.Lock()

        # =======================
        # Complete here with your own variables
        # =======================

        self.current_intersections = None
        self.follow_line_state = "FRONT" # FRONT, LEFT, RIGHT

        self.encoder = [0, 0]
        self.next_waypoint = None

        self.padding_encoder = None
        self.turn_encoder = None

        self.next_step = "STOP"

        self.robot = Robot()

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

        self.processed_data = self.session.declare_subscriber(
            "happywheels/processed_image_data", self.processed_image_data_callback
        )

        self.ir_data = self.session.declare_subscriber(
            "happywheels/ir", self.ir_callback
        )

        self.encoder_data = self.session.declare_subscriber(
            "happywheels/encoder", self.encoder_callback
        )

        self.wait_point = self.session.declare_subscriber(
            "happywheels/next_waypoint", self.next_waypoint_callback
        )

        self.motor_control = self.session.declare_publisher("happywheels/motor_control")

    def run(self):
        while True:
            time.sleep(1/30)
            # =======================
            # Check if the node should stop
            # =======================

            self.mutex.acquire()
            running = self.running
            self.mutex.release()

            if not running:
                break

            self.zenoh_mutex.acquire()

            if self.encoder is None:
                self.zenoh_mutex.release()
                continue

            # if self.next_waypoint is None:
            #     self.zenoh_mutex.release()
            #     continue

            if self.next_step == "STOP":
                self.next_step = self.robot.move_to(2, 2)

            self.do_next_step()

            self.zenoh_mutex.release()

        # =======================
        # Close the node
        # =======================

        self.close()

    def processed_image_data_callback(self, sample):
        processed_data = ProcessedData.deserialize(sample.payload.to_bytes())

        intersections = None

        if processed_data.max_white > 7500:
            if (
                processed_data.pos_intersection > 128 - 128 // 2
            ):  # Check only for NEAR intersections
                if np.max(processed_data.left_histogram) > 2500:
                    intersections = ["90LEFT"]

                if np.max(processed_data.right_histogram) > 2500:
                    if intersections is None:
                        intersections = ["90RIGHT"]
                    else:
                        intersections.append("90RIGHT")

                if np.max(processed_data.top_histogram) > 2500:
                    if intersections is not None:
                        intersections.append("FRONT")

        self.zenoh_mutex.acquire()

        self.current_intersections = intersections

        tube_x = 20

        left_treshold = -tube_x - 5
        right_treshold = tube_x + 5

        if self.follow_line_state == "FRONT":
            if 8000 > processed_data.distance_to_middle > right_treshold:
                self.follow_line_state = "RIGHT"
            elif processed_data.distance_to_middle < left_treshold:
                self.follow_line_state = "LEFT"
        elif self.follow_line_state == "RIGHT":
            if processed_data.distance_to_middle < tube_x:
                self.follow_line_state = "FRONT"
        elif self.follow_line_state == "LEFT":
            if 8000 > processed_data.distance_to_middle > -tube_x:
                self.follow_line_state = "FRONT"

        self.zenoh_mutex.release()

    def ir_callback(self, sample):
        ir_data = IRData.deserialize(sample.payload.to_bytes())

    def encoder_callback(self, sample):
        encoder_data = EncoderData.deserialize(sample.payload.to_bytes())

        self.zenoh_mutex.acquire()
        self.encoder = [encoder_data.left, encoder_data.right]
        self.zenoh_mutex.release()

    def next_waypoint_callback(self, sample):
        wait_point = NextWaypoint.deserialize(sample.payload.to_bytes())

        self.zenoh_mutex.acquire()
        self.next_waypoint = wait_point
        self.zenoh_mutex.release()

    def do_next_step(self):
        if self.next_step == "FRONT":
            self.do_front()
        elif self.next_step == "90LEFT":
            self.do_90_left()
        elif self.next_step == "90RIGHT":
            self.do_90_right()
        elif self.next_step == "180LEFT":
            self.do_180_left()
        elif self.next_step == "STOP":
            self.motor_control.put(MotorControl.serialize(MotorControl(0, 0)))

    def do_front(self):
        # =======================
        # Each iteration of the loop, you send a new motor control command to go forward
        # You also check if you have reached the next intersection
        # =======================

        if self.follow_line_state == "FRONT":
            self.motor_control.put(MotorControl.serialize(MotorControl(200, 200)))
        elif self.follow_line_state == "LEFT":
            self.motor_control.put(MotorControl.serialize(MotorControl(255, 100)))
        elif self.follow_line_state == "RIGHT":
            self.motor_control.put(MotorControl.serialize(MotorControl(100, 255)))

        # If you see an intersection, register the current encoder value
        if self.current_intersections is not None and self.padding_encoder is None:
            self.padding_encoder = self.encoder
            print("Intersection detected, starting padding...")

        if self.padding_encoder is not None:
            if self.encoder[0] - self.padding_encoder[0] > 120 and self.encoder[1] - self.padding_encoder[1] > 120:
                self.next_step = "STOP"
                self.padding_encoder = None
                print("Padding done, stopping...")

                self.robot.avance()

    def do_90_left(self):
        # =======================
        # Each iteration of the loop, you send a new motor control command to turn left
        # You also check if you have turned 90 degrees
        # =======================

        self.motor_control.put(MotorControl.serialize(MotorControl(255, -255)))

        if self.turn_encoder is None:
            self.turn_encoder = self.encoder

        print(self.encoder[1] - self.turn_encoder[1])
        print(self.encoder[0] - self.turn_encoder[0])

        if (
            self.encoder[1] - self.turn_encoder[1] < -189
            and self.encoder[0] - self.turn_encoder[0] > 264
        ):
            self.next_step = "STOP"
            self.turn_encoder = None

            self.robot.gauche()

    def do_90_right(self):
        # =======================
        # Each iteration of the loop, you send a new motor control command to turn right
        # You also check if you have turned 90 degrees
        # =======================

        self.motor_control.put(MotorControl.serialize(MotorControl(-255, 255)))

        if self.turn_encoder is None:
            self.turn_encoder = self.encoder

        if (
            self.encoder[1] - self.turn_encoder[1] < -189
            and self.encoder[0] - self.turn_encoder[0] > 264
        ):
        # sim
        # if (
        #     self.encoder[0] - self.turn_encoder[0] < -255 / 2.5 and
        #     self.encoder[1] - self.turn_encoder[1] > 264 / 2.5
        # ):
            self.next_step = "STOP"
            self.turn_encoder = None

            self.robot.droite()

    def do_180_left(self):
        # =======================
        # Each iteration of the loop, you send a new motor control command to turn right
        # You also check if you have turned 90 degrees
        # =======================

        self.motor_control.put(MotorControl.serialize(MotorControl(255, -255)))

        if self.turn_encoder is None:
            self.turn_encoder = self.encoder

        if (
            self.encoder[1] - self.turn_encoder[1] < -189 * 2
            and self.encoder[0] - self.turn_encoder[0] > 264 * 2
        ):
            self.next_step = "STOP"
            self.turn_encoder = None

            self.robot.gauche()
            self.robot.gauche()

    def close(self):
        # =======================
        # Unregister stop handler
        # =======================

        self.stop_handler.undeclare()

        # =======================
        # Complete here with your own cleanup code
        # =======================

        self.processed_data.undeclare()
        self.ir_data.undeclare()
        self.encoder_data.undeclare()
        self.wait_point.undeclare()
        self.motor_control.undeclare()

        # =======================
        # Close zenoh session
        # =======================

        self.session.close()

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
