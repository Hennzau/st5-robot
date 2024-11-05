import signal
import time
import threading

import zenoh
import cv2

import numpy as np
import dearpygui.dearpygui as dpg

from message import RGBCamera, Motor


class Monitoring:
    def __init__(self):
        # Register signal handlers
        signal.signal(signal.SIGINT, self.ctrl_c_signal)
        signal.signal(signal.SIGTERM, self.ctrl_c_signal)

        self.running = True
        self.mutex = threading.Lock()

        # Create node variables

        self.width = 1280
        self.height = 960

        dpg.create_context()
        dpg.create_viewport(title="MARCSRover", width=self.width, height=self.height)
        dpg.setup_dearpygui()

        with dpg.texture_registry():
            dpg.add_raw_texture(
                640, 480, [], tag="camera_color", format=dpg.mvFormat_Float_rgb
            )

        with dpg.window(label="camera", width=1280, height=480, pos=(0, 0)):
            dpg.add_image("camera_color", pos=(0, 0))

        with dpg.window(label="Controller", width=640, height=480, pos=(640, 480)):
            dpg.add_slider_float(
                label="Speed",
                tag="Speed",
                width=150,
                min_value=-4000,
                max_value=4000,
                default_value=0,
            )
            dpg.add_slider_float(
                label="Steering",
                tag="Steering",
                width=150,
                min_value=-90,
                max_value=90,
                default_value=0,
            )
            dpg.add_slider_int(
                label="Gear",
                tag="Gear",
                width=150,
                min_value=1,
                max_value=10,
                default_value=5,
            )

        # Create zenoh session
        config = zenoh.Config.from_file("host/zenoh_config.json")
        self.session = zenoh.open(config)

        # Create zenoh pub/subs
        self.stop_handler = self.session.declare_publisher("happywheels/stop")
        self.camera_sub = self.session.declare_subscriber(
            "happywheels/camera", self.camera_callback
        )
        self.motor_sub = self.session.declare_subscriber(
            "happywheels/controller_conversion", self.motor_callback
        )

    def run(self):
        dpg.show_viewport()
        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

            # Check if the node should stop

            self.mutex.acquire()
            running = self.running
            self.mutex.release()

            if not running:
                break

        self.close()

    def close(self):
        # self.stop_handler.put([])
        self.stop_handler.undeclare()
        self.camera_sub.undeclare()
        self.motor_sub.undeclare()
        self.session.close()

        dpg.destroy_context()

    def camera_callback(self, sample):
        image = RGBCamera.deserialize(sample.payload.to_bytes())
        rgb = np.frombuffer(bytes(image.rgb), dtype=np.uint8)
        rgb = cv2.imdecode(rgb, cv2.IMREAD_COLOR)
        rgb = cv2.resize(rgb, (640, 480))

        h, w = rgb.shape[:2]

        # Vertical line in the center
        cv2.line(rgb, (w//2, 0), (w//2, h), (0, 255, 0), 2)

        # Turn line
        cv2.line(rgb, (0, h - h//4), (w, h - h//4), (0, 255, 0), 2)

        data = np.flip(rgb, 2)
        data = data.ravel()
        data = np.asarray(data, dtype="f")

        texture_data = np.true_divide(data, 255.0)
        dpg.set_value("camera_color", texture_data)

    def motor_callback(self, sample):
        motor = Motor.deserialize(sample.payload.to_bytes())

        dpg.set_value("Steering", motor.steering)
        dpg.set_value("Speed", motor.speed)
        dpg.set_value("Gear", motor.gear)

    def ctrl_c_signal(self, signum, frame):
        # Stop the node

        self.mutex.acquire()
        self.running = False
        self.mutex.release()

        # Put your cleanup code here


if __name__ == "__main__":
    monitoring = Monitoring()
    monitoring.run()
