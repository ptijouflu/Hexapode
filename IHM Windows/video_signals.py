#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Signals - PyQt signals for video streaming
"""

from PyQt6.QtCore import pyqtSignal, QObject
from PyQt6.QtGui import QPixmap


class VideoSignals(QObject):
    """Signaux pour le stream vidéo"""
    frame_ready = pyqtSignal(QPixmap)
    status_changed = pyqtSignal(str)
