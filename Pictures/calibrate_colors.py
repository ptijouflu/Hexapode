#!/usr/bin/env python3
"""
Script pour calibrer les couleurs HSV depuis la caméra
Affiche les valeurs HSV détectées en direct
"""

import cv2
import numpy as np
import os

def display_hsv_values():
    """Affiche les valeurs HSV des pixels à l'écran"""
    
    # Utilise rpicam pour capturer une image
    timestamp_temp = "temp_calibration"
    photo_path = f"./temp_calibration.jpg"
    
    # Capture une photo
    print("[INFO] Capture d'une photo pour calibration...")
    cmd = f"rpicam-jpeg -o {photo_path} --timeout=1000 --nopreview 2>/dev/null"
    os.system(cmd)
    
    if not os.path.exists(photo_path):
        print("[ERREUR] Impossible de capturer l'image")
        return
    
    # Charger l'image
    image = cv2.imread(photo_path)
    if image is None:
        print("[ERREUR] Impossible de lire l'image")
        return
    
    # Convertir en HSV
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    
    print("\n" + "="*60)
    print("CALIBRATION HSV - Analyse de l'image capturée")
    print("="*60)
    
    # Afficher les statistiques HSV de l'image
    h, s, v = cv2.split(hsv)
    
    print(f"\n📊 STATISTIQUES GLOBALES:")
    print(f"Teinte (H)     - Min: {h.min()}, Max: {h.max()}, Moyenne: {h.mean():.1f}")
    print(f"Saturation (S) - Min: {s.min()}, Max: {s.max()}, Moyenne: {s.mean():.1f}")
    print(f"Valeur (V)     - Min: {v.min()}, Max: {v.max()}, Moyenne: {v.mean():.1f}")
    
    # Analyser les plages de teinte dominantes
    print(f"\n🎨 PLAGES DE TEINTE DÉTECTÉES:")
    
    # Compter les pixels par plage
    ranges = {
        'Rouge': ([0, 5], [175, 180]),
        'Orange': ([5, 15], None),
        'Jaune': ([15, 30], None),
        'Vert': ([30, 90], None),
        'Cyan': ([90, 110], None),
        'Bleu': ([110, 130], None),
        'Violet': ([130, 175], None),
    }
    
    for color_name, (range1, range2) in ranges.items():
        if range2:
            mask1 = cv2.inRange(hsv, np.array([range1[0], 50, 50]), np.array([range1[1], 255, 255]))
            mask2 = cv2.inRange(hsv, np.array([range2[0], 50, 50]), np.array([range2[1], 255, 255]))
            mask = cv2.bitwise_or(mask1, mask2)
        else:
            mask = cv2.inRange(hsv, np.array([range1[0], 50, 50]), np.array([range1[1], 255, 255]))
        
        pixel_count = cv2.countNonZero(mask)
        percentage = (pixel_count / (image.shape[0] * image.shape[1])) * 100
        
        print(f"  {color_name:10} - {pixel_count:7} pixels ({percentage:5.2f}%)")
    
    print(f"\n💡 RECOMMENDATION:")
    print(f"Si vous voyez du VIOLET mais que c'est du ROUGE:")
    print(f"  → Réduisez VIOLET_LOWER à [160, 80, 80]")
    print(f"  → Augmentez RED_LOWER2 à [160, 80, 80]")
    print(f"\nSi vous voyez du VERT mais que c'est du JAUNE:")
    print(f"  → Réduisez GREEN_LOWER à [40, 50, 50]")
    print(f"  → Réduisez YELLOW_UPPER à [35, 255, 255]")
    
    # Nettoyer
    os.remove(photo_path)
    print(f"\n[INFO] Image temporaire supprimée")

if __name__ == "__main__":
    display_hsv_values()
