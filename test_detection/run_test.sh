#!/bin/bash

# Script de lancement rapide pour le test de détection d'obstacles

echo "=========================================="
echo "Test de Détection d'Obstacles - Hexapode"
echo "=========================================="

# Vérifier que nous sommes dans le bon dossier
if [ ! -f "test_detection_photo.py" ]; then
    echo "Erreur: test_detection_photo.py non trouvé"
    echo "Veuillez exécuter ce script depuis le dossier test_detection"
    exit 1
fi

# Vérifier que Python 3 est disponible
if ! command -v python3 &> /dev/null; then
    echo "Erreur: Python 3 non trouvé"
    echo "Veuillez installer Python 3"
    exit 1
fi

# Vérifier la caméra (optionnel)
echo "Vérification de la caméra..."
if command -v libcamera-vid &> /dev/null; then
    echo "✓ libcamera-vid trouvé"
elif command -v rpicam-jpeg &> /dev/null; then
    echo "✓ rpicam-jpeg trouvé"
else
    echo "⚠ Aucun outil de caméra détecté (libcamera-vid/rpicam-jpeg)"
    echo "  Le programme peut ne pas fonctionner correctement"
fi

echo ""
echo "Lancement du programme de test..."
echo "Appuyez sur Ctrl+C pour interrompre"
echo ""

# Lancer le programme
python3 test_detection_photo.py

echo ""
echo "Programme terminé."