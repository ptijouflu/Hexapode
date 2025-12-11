#!/bin/bash
# Script de démarrage du serveur de streaming Hexapode
# Usage: ./start_stream.sh [OPTIONS]
# Options: --port PORT, --model nano|small|medium|large, --no-detection

cd "$(dirname "$0")"

# Vérifier que venv existe
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment non trouvé!"
    echo "Veuillez installer avec: python3 -m venv venv && source venv/bin/activate && pip install opencv-python ultralytics numpy"
    exit 1
fi

# Activer venv
source venv/bin/activate

# Vérifier rpicam-jpeg
if ! command -v rpicam-jpeg &> /dev/null; then
    echo "❌ rpicam-jpeg non trouvé!"
    echo "Installez avec: sudo apt update && sudo apt install rpicam-apps"
    exit 1
fi

# Vérifier dépendances Python
python3 -c "import cv2, ultralytics" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Dépendances Python manquantes!"
    echo "Installez avec: pip install opencv-python ultralytics"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "  🤖 Hexapode Camera Stream MJPEG"
echo "═══════════════════════════════════════════════════════════"
echo ""

# Lancer le serveur
python3 camera_stream.py "$@"

echo ""
echo "Serveur arrêté."
