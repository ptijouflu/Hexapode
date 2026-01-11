#!/bin/bash
# Script pour lancer correctement la caméra

# Nettoyer les processus existants
sudo killall -9 rpicam-hello rpicam-jpeg rpicam-vid 2>/dev/null

# Recharger les modules caméra
sudo modprobe -r bcm2835_v4l2 2>/dev/null
sudo modprobe bcm2835_v4l2 2>/dev/null

# Démarrer le script Python pour le streaming
cd /home/user/Documents/Hexapode/Dev/Hexapode-main/Flux_Video
python3 camera_stream_mjpeg_v3.py --no-detection

# Instructions pour l'utilisateur
echo "Streaming démarré. Accédez à http://localhost:8080 pour voir le flux."
echo "Si vous êtes sur un autre PC, utilisez SSH :"
echo "ssh -L 8080:localhost:8080 user@<IP_RASPBERRY>"
