"""
Hexapode - Package principal
Modules partagés pour le contrôle de l'hexapode
"""

from .constants import *
from .movements import *
from .motor_controller import MotorController
from .keyboard_handler import KeyboardHandler
from .obstacle_detector import ObstacleDetector
from .camera import FastCamera
from .http_server import StreamHandler, ThreadedHTTPServer, start_stream_server

__all__ = [
    'MotorController',
    'KeyboardHandler',
    'ObstacleDetector',
    'FastCamera',
    'StreamHandler',
    'ThreadedHTTPServer',
    'start_stream_server',
    'HTTP_PORT',
    'CAMERA_WIDTH',
    'CAMERA_HEIGHT',
    'CAMERA_FPS',
    'INIT_POSE',
    'SEQ_MOVE_F',
    'SEQ_MOVE_B', 
    'SEQ_SLIDE_L',
    'SEQ_SLIDE_R',
    'SEQ_PIVOT_L',
    'SEQ_PIVOT_R',
    'deg2dxl',
    'amplify_sequence',
]
