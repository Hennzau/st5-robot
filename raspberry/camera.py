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

from picamera import PiCamera
from picamera.array import PiRGBArray

import numpy as np

# =======================
# Import the message class
# =======================

from message import RGBCamera
from message import ProcessedImageData


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

        self.camera = PiCamera(sensor_mode=2)
        self.camera.resolution = (160, 128)
        self.camera.framerate = 32
        self.raw_capture = PiRGBArray(self.camera, size=self.camera.resolution)
        self.frame_source = self.camera.capture_continuous(
            self.raw_capture, format="bgr", use_video_port=True
        )

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

        self.camera_publisher = self.session.declare_publisher("happywheels/camera")
        self.processed_image_data = self.session.declare_publisher(
            "happywheels/processed_image_data"
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

            frame = next(self.frame_source).array
            self.raw_capture.truncate(0)

            # Use the captured frame
            h, w = frame.shape[:2]
            # print(w, h)
            # Convert to HSV color space

            blur = cv2.blur(frame, (5, 5))
            # ret,thresh1 = cv2.threshold(image,127,255,cv2.THRESH_BINARY)
            ret, thresh1 = cv2.threshold(blur, 168, 255, cv2.THRESH_BINARY)
            hsv = cv2.cvtColor(thresh1, cv2.COLOR_RGB2HSV)

            # Define range of white color in HSV
            lower_white = np.array([0, 0, 168])
            upper_white = np.array([172, 111, 255])
            # Threshold the HSV image
            mask = cv2.inRange(hsv, lower_white, upper_white)
            # cv2.imwrite('out_test.png', mask)
            # Remove noise
            kernel_erode = np.ones((6, 6), np.uint8)

            eroded_mask = cv2.erode(mask, kernel_erode, iterations=1)
            kernel_dilate = np.ones((4, 4), np.uint8)
            dilated_mask = cv2.dilate(eroded_mask, kernel_dilate, iterations=1)

            # Find the different contours
            contours, hierarchy = cv2.findContours(
                dilated_mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )

            frame = cv2.drawContours(frame, contours, -1, (0, 255, 0), 3)

            contours = sorted(contours, key=cv2.contourArea, reverse=True)[:1]

            image_data = ProcessedImageData(0, 0, 0, 0, 0, 0)

            if len(contours) > 0:
                M = cv2.moments(contours[0])
                # Centroid
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                # print("Centroid of the biggest area: ({}, {})".format(cx, cy))

                # Location of the centroid
                cv2.circle(frame, (cx, cy), 10, (0, 0, 255), 3)
                # Vertical line in the center
                cv2.line(frame, (w // 2, 0), (w // 2, h), (255, 0, 0), 2)

                # Distance to the center allowing to turn left or right
                distance = cx - w / 2
                cv2.putText(
                    frame,
                    f"{distance}",
                    (cx, cy),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1,
                    (255, 0, 0),
                    2,
                    cv2.LINE_AA,
                )

                image_data.distance_to_middle = distance

            color_frame = cv2.imencode(
                ".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70]
            )[1].tobytes()

            # Compute horizontal histogram of the white pixels in dilated_mask
            histogram = np.sum(dilated_mask, axis=1)

            max_white = np.max(histogram)
            pos_intersection = np.argmax(histogram)

            image_data.pos_intersection = pos_intersection
            image_data.max_white = max_white

            left_histogram = np.max(np.sum(dilated_mask[:, : w // 8], axis=1))
            right_histogram = np.max(np.sum(dilated_mask[:, 7 * w // 8 :], axis=1))
            top_histogram = np.max(np.sum(dilated_mask[: h // 8, :], axis=0))

            image_data.left_histogram = left_histogram
            image_data.right_histogram = right_histogram
            image_data.top_histogram = top_histogram

            # =======================
            # Complete here with your own message
            # =======================
            self.processed_image_data.put(ProcessedImageData.serialize(image_data))

            image = RGBCamera(
                rgb=color_frame,
                width=160,
                height=128,
            )

            self.camera_publisher.put(RGBCamera.serialize(image))

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

        self.camera_publisher.undeclare()
        self.processed_image_data.undeclare()

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
