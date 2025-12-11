#!/usr/bin/env python3
"""
Script interactif pour calibrer les plages HSV des couleurs
Affiche les pixels détectés et permet d'ajuster les plages
"""

import cv2
import numpy as np
import os

def calibrate_colors_interactive():
    """Calibre les couleurs de manière interactive"""
    
    # Capture une photo
    print("[INFO] Capture d'une photo pour calibration...")
    photo_path = "./temp_calibration.jpg"
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
    
    print("\n" + "="*70)
    print("CALIBRATION INTERACTIVE HSV")
    print("="*70)
    
    # Analyser section par section
    h, s, v = cv2.split(hsv)
    
    print("\n📊 APERÇU DE L'IMAGE:")
    print(f"Hauteur: {image.shape[0]}px | Largeur: {image.shape[1]}px")
    print(f"\n📈 PLAGES DÉTECTÉES:")
    print(f"Teinte (H)     - Min: {h.min():3d}, Max: {h.max():3d}, Moyenne: {h.mean():6.1f}")
    print(f"Saturation (S) - Min: {s.min():3d}, Max: {s.max():3d}, Moyenne: {s.mean():6.1f}")
    print(f"Valeur (V)     - Min: {v.min():3d}, Max: {v.max():3d}, Moyenne: {v.mean():6.1f}")
    
    # Analyser par région (haut, milieu, bas)
    height = image.shape[0]
    regions = {
        'Haut (25%)': (0, height // 4),
        'Milieu (50%)': (height // 4, 3 * height // 4),
        'Bas (25%)': (3 * height // 4, height)
    }
    
    print("\n🔍 ANALYSE PAR RÉGION:")
    for region_name, (start, end) in regions.items():
        region_hsv = hsv[start:end, :]
        h_r, s_r, v_r = cv2.split(region_hsv)
        
        # Ignorer les pixels noirs
        mask = (v_r > 20)
        if mask.sum() > 0:
            h_r = h_r[mask]
            s_r = s_r[mask]
            v_r = v_r[mask]
            
            print(f"\n  {region_name}:")
            print(f"    H: {h_r.min():3d}-{h_r.max():3d} (avg: {h_r.mean():6.1f})")
            print(f"    S: {s_r.min():3d}-{s_r.max():3d} (avg: {s_r.mean():6.1f})")
            print(f"    V: {v_r.min():3d}-{v_r.max():3d} (avg: {v_r.mean():6.1f})")
    
    # Suggestions
    print("\n💡 SUGGESTIONS DE CALIBRATION:")
    h_mean = int(h[h > 0].mean()) if (h > 0).sum() > 0 else 0
    s_mean = int(s.mean())
    v_mean = int(v.mean())
    
    print(f"   Teinte dominante: H ≈ {h_mean}°")
    print(f"   Saturation moyenne: S ≈ {s_mean}")
    print(f"   Valeur moyenne: V ≈ {v_mean}")
    
    # Identifier la couleur
    if h_mean < 10:
        print(f"   → Couleur: ROUGE (régler RED_LOWER1 et RED_UPPER1)")
    elif h_mean < 20:
        print(f"   → Couleur: ORANGE (régler ORANGE_LOWER et ORANGE_UPPER)")
    elif h_mean < 35:
        print(f"   → Couleur: JAUNE (régler YELLOW_LOWER et YELLOW_UPPER)")
    elif h_mean < 85:
        print(f"   → Couleur: VERT (régler GREEN_LOWER et GREEN_UPPER)")
    elif h_mean < 110:
        print(f"   → Couleur: CYAN (régler CYAN_LOWER et CYAN_UPPER)")
    elif h_mean < 130:
        print(f"   → Couleur: BLEU (régler BLUE_LOWER et BLUE_UPPER)")
    else:
        print(f"   → Couleur: VIOLET (régler VIOLET_LOWER et VIOLET_UPPER)")
    
    print(f"\n   Pour cette couleur, utiliser:")
    print(f"   LOWER = np.array([{h_mean-5}, {max(0, s_mean-50)}, {max(0, v_mean-50)}])")
    print(f"   UPPER = np.array([{h_mean+5}, 255, 255])")
    
    # Nettoyer
    os.remove(photo_path)
    print(f"\n✅ Calibration terminée")

if __name__ == "__main__":
    calibrate_colors_interactive()
