#!/bin/bash
# Script pour lancer le détecteur de couleur avec l'environnement virtuel

cd "$(dirname "$0")"
source venv/bin/activate
python3 Pictures/camera_color_detection_ssh.py
