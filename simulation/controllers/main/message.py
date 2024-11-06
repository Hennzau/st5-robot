from dataclasses import dataclass

import numpy as np
import json

from pycdr2 import IdlStruct
from pycdr2.types import uint32, float32, uint8, int32
from typing import List


@dataclass
class CompressedImage(IdlStruct):
    rgb: bytes
    width: uint32
    height: uint32

@dataclass
class ProcessedData(IdlStruct):
    distance_to_middle: float32
    pos_intersection: float32
    max_white: float32
    left_histogram: float32
    right_histogram: float32
    top_histogram: float32

@dataclass
class MotorControl(IdlStruct):
    speed_left: int32
    speed_right: int32

@dataclass
class IRData(IdlStruct):
    distance: float32

@dataclass
class EncoderData(IdlStruct):
    left: int32
    right: int32

@dataclass
class NextWaypoint(IdlStruct):
    i: uint32
    j: uint32
