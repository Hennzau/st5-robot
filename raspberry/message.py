from dataclasses import dataclass

import numpy as np
import json

from pycdr2 import IdlStruct
from pycdr2.types import uint32, float32, uint8
from typing import List

@dataclass
class RGBCamera(IdlStruct):
    rgb: bytes
    width: uint32
    height: uint32

@dataclass
class LineMiddle(IdlStruct):
    value: float32

@dataclass
class Motor(IdlStruct):
    speed: float32
    steering: float32
    gear: uint8

@dataclass
class JoyStickController(IdlStruct):
    axis: List[float32]
    buttons: List[uint32]
    balls: List[float32]
