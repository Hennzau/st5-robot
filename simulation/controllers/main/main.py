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

from message import CompressedImage, ProcessedData, EncoderData, IRData, MotorControl

from controller import Robot
from controller import Camera

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

        self.sensors = []
        self.sensors_names = ['s1', 's2', 's3', 's4']
        for i in range(4):
            self.sensors.append(self.robot.getDevice(self.sensors_names[i]))
            self.sensors[i].enable(self.time_step)

        # =======================
        # Create zenoh session
        # =======================

        config = zenoh.Config.from_file("zenoh_config.json")
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

        self.camera_publisher = self.session.declare_publisher("happywheels/camera")
        self.processed_image_data = self.session.declare_publisher(
            "happywheels/processed_image_data"
        )
        self.ir_publisher = self.session.declare_publisher("happywheels/ir")
        self.encoder_publisher = self.session.declare_publisher("happywheels/encoder")
        self.motor_control_subscriber = self.session.declare_subscriber("happywheels/motor_control", self.motor_control_callback)

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

            # =======================
            # Complete here with your own message
            # =======================

            data = ProcessedData(0, 0, 0, 0, 0, 0)

            cameraData = self.camera.getImage()
            image = np.frombuffer(cameraData, np.uint8).reshape((self.camera.getHeight(), self.camera.getWidth(), 4))

            # Read/Write issue
            image = cv2.resize(image, (160, 128))
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
                data.distance_to_middle = 9000 # No centroid found, useful when turning

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

            self.processed_image_data.put(ProcessedData.serialize(data))

            color_frame = cv2.imencode(
                ".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            )[1].tobytes()

            image = CompressedImage(
                rgb=color_frame,
                width=160,
                height=128,
            )

            self.camera_publisher.put(CompressedImage.serialize(image))

            r_sensor_mem = self.sensors[0].getValue()
            l_sensor_mem = self.sensors[1].getValue()

            r_sensor_mem = 0 if r_sensor_mem < 0 else r_sensor_mem
            l_sensor_mem = 0 if l_sensor_mem < 0 else l_sensor_mem

            r_sensor_mem = int(r_sensor_mem * 128 * 264 / 492 / 2.1)
            l_sensor_mem = int(l_sensor_mem * 128 * 264 / 492 / 2.1)

            self.encoder_publisher.put(EncoderData.serialize(EncoderData(l_sensor_mem, r_sensor_mem)))

        # =======================
        # Close the node
        # =======================

        self.close()

    def motor_control_callback(self, sample):
        motor_control = MotorControl.deserialize(sample.payload.to_bytes())

        self.wheels[0].setVelocity(motor_control.speed_right / 255 * 3)
        self.wheels[1].setVelocity(motor_control.speed_left / 255 * 3)
        self.wheels[2].setVelocity(motor_control.speed_right / 255 * 3)
        self.wheels[3].setVelocity(motor_control.speed_left / 255 * 3)

    def close(self):
        # =======================
        # Unregister stop handler
        # =======================

        self.stop_handler.undeclare()

        # =======================
        # Complete here with your own cleanup code
        # =======================

        self.camera_publisher.undeclare()

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
