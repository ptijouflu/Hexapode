#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration constants for SSH GUI Application
"""

# Flux vidéo
DEFAULT_VIDEO_URL = "http://localhost:8081/stream"
DEFAULT_VIDEO_WIDTH = 640
DEFAULT_VIDEO_HEIGHT = 240

# Navigation SSH
DEFAULT_SSH_FOLDER = "Documents/Hexapode"
NAVIGATION_DELAY = 0.5  # Secondes d'attente avant de naviguer

# Fenêtre
DEFAULT_WINDOW_WIDTH = 1200
DEFAULT_WINDOW_HEIGHT = 700

# Programmes hexapode
AUTO_PROGRAM = "python3 ./navigation_autonome.py"
MANUAL_PROGRAM = "python3 ./deplacement.py"
PROGRAM_STOP_DELAY = 0.5  # Délai d'attente après Ctrl+C

# Commandes hexapode
HEXAPOD_COMMANDS = {
    'z': 'Avancer',
    'q': 'Gauche',
    's': 'Reculer',
    'd': 'Droite',
    'a': 'Action A',
    'e': 'Action E',
    ' ': 'Pause/Stop'
}
