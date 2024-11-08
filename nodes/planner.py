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

from message import (
    ProcessedData,
    IRData,
    EncoderData,
    MotorControl,
    NextWaypoint,
    Urgency,
)

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

        self.grace_timer = None

        # =======================
        # Complete here with your own variables
        # =======================

        self.current_intersections = None
        self.follow_line_state = "FRONT"  # FRONT, LEFT, RIGHT

        self.encoder = [0, 0]
        self.next_waypoint = None

        self.padding_encoder = None
        self.turn_encoder = None

        self.obstacles = []

        self.distance_trigger = 0

        self.next_step = "STOP"

        self.robot = Robot()

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

        self.urgency_subscriber = self.session.declare_subscriber(
            "happywheels/urgency", self.urgency_callback
        )

    def run(self):
        while True:
            time.sleep(1 / 30)
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

            if self.next_waypoint is None:
                self.zenoh_mutex.release()
                continue

            if self.next_step == "STOP":
                self.next_step = self.robot.move_to(
                    self.next_waypoint.i, self.next_waypoint.j, self.obstacles
                )

            self.do_next_step()

            self.zenoh_mutex.release()

            if self.grace_timer is not None and time.time() - self.grace_timer > 0.5:
                self.grace_timer = None

        # =======================
        # Close the node
        # =======================

        self.close()

    def processed_image_data_callback(self, sample):
        buffer = sample.payload.to_bytes()

        if buffer is None:
            return

        processed_data = ProcessedData.deserialize(buffer)

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
            # elif processed_data.distance_to_middle > 8000:
            #     self.next_step = "STOP-ALL"
            #     print("NO LINE, EMERGENCY STOP")
        elif self.follow_line_state == "RIGHT":
            if processed_data.distance_to_middle < tube_x:
                self.follow_line_state = "FRONT"
        elif self.follow_line_state == "LEFT":
            if 8000 > processed_data.distance_to_middle > -tube_x:
                self.follow_line_state = "FRONT"

        self.zenoh_mutex.release()

    def ir_callback(self, sample):
        payload = sample.payload.to_bytes()

        if payload is None:
            return

        ir_data = IRData.deserialize(payload)

        if ir_data.distance < 25:
            self.zenoh_mutex.acquire()

            self.distance_trigger += 1

            if self.distance_trigger < 5:
                self.zenoh_mutex.release()
                return

            if self.turn_encoder is not None or self.next_step == "180LEFT":
                self.zenoh_mutex.release()
                return

            print("Obstacle detected")
            self.next_step = "180LEFT"

            if self.robot.direction == 0:
                self.obstacles.append(
                    ((self.robot.i, self.robot.j), (self.robot.i, self.robot.j + 1))
                )
            if self.robot.direction == 90:
                self.obstacles.append(
                    ((self.robot.i, self.robot.j), (self.robot.i - 1, self.robot.j))
                )
            if self.robot.direction == 180:
                self.obstacles.append(
                    ((self.robot.i, self.robot.j), (self.robot.i, self.robot.j - 1))
                )
            if self.robot.direction == -90:
                self.obstacles.append(
                    ((self.robot.i, self.robot.j), (self.robot.i + 1, self.robot.j))
                )

            self.robot.avance()

            self.zenoh_mutex.release()
        else:
            self.zenoh_mutex.acquire()
            self.distance_trigger = 0
            self.zenoh_mutex.release()

    def encoder_callback(self, sample):
        buffer = sample.payload.to_bytes()

        if buffer is None:
            return

        encoder_data = EncoderData.deserialize(buffer)

        self.zenoh_mutex.acquire()
        self.encoder = [encoder_data.left, encoder_data.right]
        self.zenoh_mutex.release()

    def next_waypoint_callback(self, sample):
        wait_point = NextWaypoint.deserialize(sample.payload.to_bytes())

        self.zenoh_mutex.acquire()
        self.next_waypoint = wait_point
        self.zenoh_mutex.release()

    def urgency_callback(self, sample):
        print("EMERGENCY STOP")
        self.next_step = "STOP-ALL"

    def do_next_step(self):
        if self.next_step == "FRONT":
            self.do_front()
        elif self.next_step == "90LEFT":
            self.do_90_left()
        elif self.next_step == "90RIGHT":
            self.do_90_right()
        elif self.next_step == "180LEFT":
            self.do_180_left()
        elif self.next_step == "STOP" or self.next_step == "STOP-ALL":
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
            if self.grace_timer is None:
                self.padding_encoder = self.encoder
                print("Intersection detected, starting padding...")
                self.grace_timer = time.time()

        if self.padding_encoder is not None:
            # real
            if (
                self.encoder[0] - self.padding_encoder[0] > 120
                and self.encoder[1] - self.padding_encoder[1] > 120
            ):
                # sim
                # if (
                #     self.encoder[0] - self.padding_encoder[0] > 260
                #     and self.encoder[1] - self.padding_encoder[1] > 260
                # ):
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
        # real
        if (
            self.encoder[0] - self.turn_encoder[0] < -189
            and self.encoder[1] - self.turn_encoder[1] > 264
        ):
            # sim
            # if (
            #     self.encoder[0] - self.turn_encoder[0] < -189 * 0.8
            #     and self.encoder[1] - self.turn_encoder[1] > 264 * 0.8
            # ):
            self.next_step = "STOP"
            self.turn_encoder = None

            self.robot.gauche()
            self.grace_timer = time.time()

    def do_90_right(self):
        # =======================
        # Each iteration of the loop, you send a new motor control command to turn right
        # You also check if you have turned 90 degrees
        # =======================

        self.motor_control.put(MotorControl.serialize(MotorControl(-255, 255)))

        if self.turn_encoder is None:
            self.turn_encoder = self.encoder

        # real
        if (
            self.encoder[1] - self.turn_encoder[1] < -189
            and self.encoder[0] - self.turn_encoder[0] > 264
        ):
            # sim
            # if (
            #     self.encoder[1] - self.turn_encoder[1] < -189 * 1
            #     and self.encoder[0] - self.turn_encoder[0] > 264 * 1
            # ):
            self.next_step = "STOP"
            self.turn_encoder = None

            self.robot.droite()
            self.grace_timer = time.time()

    def do_180_left(self):
        # =======================
        # Each iteration of the loop, you send a new motor control command to turn right
        # You also check if you have turned 90 degrees
        # =======================

        self.motor_control.put(MotorControl.serialize(MotorControl(255, -255)))

        if self.turn_encoder is None:
            self.turn_encoder = self.encoder

        # real
        if (
            self.encoder[0] - self.turn_encoder[0] < -189 * 2.2
            and self.encoder[1] - self.turn_encoder[1] > 264 * 2.2
        ):
            # sim
            # if (
            #     self.encoder[0] - self.turn_encoder[0] < -189 * 1.7
            #     and self.encoder[1] - self.turn_encoder[1] > 264 * 1.7
            # ):
            self.next_step = "FRONT"
            self.turn_encoder = None

            self.robot.gauche()
            self.robot.gauche()

            self.grace_timer = time.time()

    def close(self):
        # =======================
        # Unregister stop handler
        # =======================

        self.stop_handler.undeclare()

        # =======================
        # Complete here with your own cleanup code
        # =======================

        self.motor_control.put(MotorControl.serialize(MotorControl(0, 0)))

        self.processed_data.undeclare()
        self.ir_data.undeclare()
        self.encoder_data.undeclare()
        self.wait_point.undeclare()
        self.motor_control.undeclare()
        self.urgency_subscriber.undeclare()

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
