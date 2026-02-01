#!/bin/bash
# ============================================================================
# Hexapode - Script d'installation automatique
# Testé sur Raspberry Pi OS (Bookworm)
# ============================================================================

set -e  # Arrêter en cas d'erreur

echo ""
echo "=============================================="
echo "    HEXAPODE - Installation automatique"
echo "=============================================="
echo ""

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les étapes
step() {
    echo -e "${GREEN}[[OK]]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ============================================================================
# 1. Mise à jour du système
# ============================================================================
echo " Mise à jour du système..."
sudo apt-get update -qq
step "Système mis à jour"

# ============================================================================
# 2. Installation des dépendances système
# ============================================================================
echo ""
echo " Installation des dépendances système..."

# Python et pip
sudo apt-get install -y -qq python3 python3-pip python3-venv

# OpenCV et ses dépendances
sudo apt-get install -y -qq python3-opencv libopencv-dev

# Outils pour port série (Dynamixel)
sudo apt-get install -y -qq libusb-1.0-0-dev

# Caméra Raspberry Pi
sudo apt-get install -y -qq libcamera-apps rpicam-apps

step "Dépendances système installées"

# ============================================================================
# 3. Configuration du port série pour Dynamixel
# ============================================================================
echo ""
echo "  Configuration du port série..."

# Ajouter l'utilisateur au groupe dialout (accès port série)
if ! groups $USER | grep -q dialout; then
    sudo usermod -aG dialout $USER
    warn "Utilisateur ajouté au groupe 'dialout' - Redémarrage requis"
fi

# Règle udev pour Dynamixel U2D2/USB2AX
UDEV_RULE='SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6014", MODE="0666", SYMLINK+="ttyDXL"'
UDEV_FILE="/etc/udev/rules.d/99-dynamixel.rules"

if [ ! -f "$UDEV_FILE" ]; then
    echo "$UDEV_RULE" | sudo tee $UDEV_FILE > /dev/null
    sudo udevadm control --reload-rules
    sudo udevadm trigger
    step "Règle udev Dynamixel créée"
else
    step "Règle udev Dynamixel déjà présente"
fi

step "Port série configuré"

# ============================================================================
# 4. Installation des dépendances Python
# ============================================================================
echo ""
echo "🐍 Installation des dépendances Python..."

# Déterminer le chemin du script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Installer les dépendances Python (avec --break-system-packages pour Bookworm)
if [ -f "requirements.txt" ]; then
    pip3 install --user --break-system-packages -r requirements.txt
    step "Dépendances Python installées"
else
    error "requirements.txt non trouvé!"
    exit 1
fi

# ============================================================================
# 5. Vérification de l'installation
# ============================================================================
echo ""
echo " Vérification de l'installation..."

# Vérifier Python
python3 --version
step "Python OK"

# Vérifier OpenCV
python3 -c "import cv2; print(f'OpenCV {cv2.__version__}')" && step "OpenCV OK" || warn "OpenCV non disponible"

# Vérifier Dynamixel SDK
python3 -c "from dynamixel_sdk import *; print('Dynamixel SDK OK')" && step "Dynamixel SDK OK" || warn "Dynamixel SDK non disponible"

# Vérifier numpy
python3 -c "import numpy; print(f'NumPy {numpy.__version__}')" && step "NumPy OK" || warn "NumPy non disponible"

# ============================================================================
# 6. Vérification du module hexapod
# ============================================================================
echo ""
echo " Vérification du module hexapod..."

if [ -d "hexapod" ]; then
    python3 -c "from hexapod import MotorController, ObstacleDetector; print('Module hexapod OK')" && step "Module hexapod OK" || warn "Module hexapod incomplet"
else
    error "Dossier hexapod/ non trouvé!"
fi

# ============================================================================
# Terminé
# ============================================================================
echo ""
echo "=============================================="
echo -e "   ${GREEN}[OK] Installation terminée !${NC}"
echo "=============================================="
echo ""
echo " Programmes disponibles:"
echo "   • python3 Deplacement_Manuel.py      → Contrôle manuel (ZQSD)"
echo "   • python3 Deplacement_Automatique.py → Navigation autonome"
echo ""
echo "  Notes importantes:"
echo "   • Brancher le U2D2/USB2AX sur /dev/ttyUSB0"
echo "   • Si premier lancement: redémarrer pour appliquer les permissions"
echo "   • Pour le streaming: ssh -L 8080:localhost:8080 user@[IP]"
echo ""
