#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSH Signals - PyQt signals for SSH communication
"""

from PyQt6.QtCore import pyqtSignal, QObject


class SSHSignals(QObject):
    """Signaux pour la communication entre les threads"""
    output_received = pyqtSignal(str)
    connection_status = pyqtSignal(bool, str)
