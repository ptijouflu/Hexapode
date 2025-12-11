#!/bin/bash
# Script de capture vidéo continue en JPEG
# Captures frames dans /tmp/frame_*.jpg

OUTPUT_DIR="/tmp/camera_stream"
mkdir -p "$OUTPUT_DIR"

# Nettoyage ancien dossier
rm -f "$OUTPUT_DIR/frame_*.jpg"

# Boucle infinie de capture
COUNTER=0
while true; do
    FILENAME=$(printf "$OUTPUT_DIR/frame_%05d.jpg" $COUNTER)
    
    # Capture une frame
    rpicam-jpeg --width 640 --height 480 --quality 85 --timeout 100 --nopreview -o "$FILENAME" 2>/dev/null
    
    # Si succès, incrémenter et continuer
    if [ -f "$FILENAME" ]; then
        COUNTER=$((COUNTER + 1))
        
        # Garder seulement les 5 derniers fichiers
        find "$OUTPUT_DIR" -name "frame_*.jpg" -type f | sort -r | tail -n +6 | xargs -r rm
    else
        sleep 0.05
    fi
done
