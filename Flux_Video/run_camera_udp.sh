#!/bin/bash

# Script pour lancer le streaming vidéo UDP
# Usage: 
#   ./run_camera_udp.sh <IP_DESTINATION> [PORT]
#   ./run_camera_udp.sh receive [PORT]

# Couleurs pour l'affichage
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CAMERA_SCRIPT="$SCRIPT_DIR/Flux_Video/camera_stream_udp.py"

# Valeurs par défaut
PORT=${2:-5000}

show_help() {
    echo -e "${GREEN}=== Hexapode Camera UDP Streaming ===${NC}"
    echo ""
    echo "Usage:"
    echo -e "  ${YELLOW}Émetteur (sur Raspberry Pi):${NC}"
    echo "    $0 <IP_DESTINATION> [PORT]"
    echo "    Exemple: $0 192.168.1.100 5000"
    echo ""
    echo -e "  ${YELLOW}Récepteur (sur PC):${NC}"
    echo "    $0 receive [PORT]"
    echo "    Exemple: $0 receive 5000"
    echo ""
    echo "Options:"
    echo "  IP_DESTINATION : Adresse IP du PC qui recevra le flux"
    echo "  PORT           : Port UDP (défaut: 5000)"
    echo ""
}

cleanup_camera() {
    echo -e "${YELLOW}Nettoyage des processus caméra...${NC}"
    sudo killall -9 rpicam-hello rpicam-jpeg rpicam-vid 2>/dev/null
    sudo modprobe -r bcm2835_v4l2 2>/dev/null
    sudo modprobe bcm2835_v4l2 2>/dev/null
    sleep 1
    echo -e "${GREEN}✓ Caméra réinitialisée${NC}"
}

# Vérifier les arguments
if [ $# -lt 1 ]; then
    show_help
    exit 1
fi

case "$1" in
    -h|--help|help)
        show_help
        exit 0
        ;;
    receive|recv|r)
        # Mode récepteur
        echo -e "${GREEN}=== Mode Récepteur UDP ===${NC}"
        echo -e "Port: ${YELLOW}$PORT${NC}"
        echo ""
        python3 "$CAMERA_SCRIPT" --receive --port "$PORT"
        ;;
    *)
        # Mode émetteur
        HOST="$1"
        
        # Vérifier si c'est une IP valide
        if ! [[ "$HOST" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo -e "${RED}Erreur: '$HOST' n'est pas une adresse IP valide${NC}"
            echo ""
            show_help
            exit 1
        fi
        
        echo -e "${GREEN}=== Mode Émetteur UDP ===${NC}"
        echo -e "Destination: ${YELLOW}$HOST:$PORT${NC}"
        echo ""
        
        # Nettoyer et réinitialiser la caméra
        cleanup_camera
        
        # Lancer le streaming
        cd "$SCRIPT_DIR/Flux_Video"
        python3 camera_stream_udp.py --host "$HOST" --port "$PORT" --no-detection
        ;;
esac
