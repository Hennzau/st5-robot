"""
File containing all the constants used in the different files
"""
from __future__ import print_function, division, absolute_import

import numpy as np

# Camera Constants
CAMERA_RESOLUTION = (640 // 2, 480 // 2)
# https://picamera.readthedocs.io/en/release-1.13/fov.html#sensor-modes
# mode 4, larger FoV but FPS <= 40
CAMERA_MODE = 4
# Regions of interest
MAX_WIDTH = CAMERA_RESOLUTION[0]
MAX_HEIGHT = CAMERA_RESOLUTION[1]



BAUDRATE = 115200  # Communication with the Arduino

