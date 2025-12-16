#!/usr/bin/env python3
"""
Programme de calibration des couleurs pour la détection par caméra
Permet d'enregistrer les plages HSV de différentes couleurs en les montrant à la caméra
"""

import os
import cv2
import numpy as np
from datetime import datetime
import json


class ColorCalibrator:
    """Calibre les plages de couleurs en HSV pour améliorer la détection"""

    def __init__(self, use_libcamera=True):
        """
        Initialise le calibrateur
        
        :param use_libcamera: Utiliser libcamera (Raspberry Pi) ou OpenCV
        """
        self.use_libcamera = use_libcamera
        self.color_ranges = {}
        self.temp_photo_path = "./temp_calibration.jpg"
        
    def capture_frame(self):
        """Capture une image avec la caméra"""
        if self.use_libcamera:
            return self._capture_libcamera()
        else:
            return self._capture_opencv()
    
    def _capture_libcamera(self):
        """Capture avec rpicam (Raspberry Pi)"""
        cmd = f"rpicam-jpeg -o {self.temp_photo_path} --timeout=1000 --nopreview 2>/dev/null"
        exit_code = os.system(cmd)
        
        if exit_code == 0 and os.path.exists(self.temp_photo_path):
            image = cv2.imread(self.temp_photo_path)
            return image
        return None
    
    def _capture_opencv(self):
        """Capture avec OpenCV (USB/V4L2)"""
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        
        if not cap.isOpened():
            print("[ERREUR] Impossible d'accéder à la caméra")
            return None
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        # Lire plusieurs frames pour stabiliser l'exposition
        for _ in range(5):
            cap.read()
        
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            cv2.imwrite(self.temp_photo_path, frame)
            return frame
        return None
    
    def analyze_color_region(self, image, region_percent=30):
        """
        Analyse la région centrale de l'image pour extraire les valeurs HSV
        
        :param image: Image BGR
        :param region_percent: Pourcentage de l'image à analyser au centre (30% = 30x30% du centre)
        :return: Tuple (H_min, S_min, V_min, H_max, S_max, V_max)
        """
        h, w = image.shape[:2]
        
        # Définir la région centrale (30% du centre de l'image)
        margin_h = int(h * (100 - region_percent) / 200)
        margin_w = int(w * (100 - region_percent) / 200)
        
        center_region = image[margin_h:h-margin_h, margin_w:w-margin_w]
        
        # Conversion en HSV
        hsv = cv2.cvtColor(center_region, cv2.COLOR_BGR2HSV)
        
        # Calcul des statistiques (min, max, moyenne, écart-type)
        h_channel = hsv[:, :, 0]
        s_channel = hsv[:, :, 1]
        v_channel = hsv[:, :, 2]
        
        # Pour la teinte (H), gérer le cas du rouge qui entoure 0
        h_mean = np.mean(h_channel)
        
        # Calculer les plages avec une marge (±15 pour H, ±30 pour S/V)
        h_min = max(0, int(np.percentile(h_channel, 5)))
        h_max = min(180, int(np.percentile(h_channel, 95)))
        s_min = max(0, int(np.percentile(s_channel, 5)))
        s_max = min(255, int(np.percentile(s_channel, 95)))
        v_min = max(0, int(np.percentile(v_channel, 5)))
        v_max = min(255, int(np.percentile(v_channel, 95)))
        
        # Afficher les valeurs moyennes pour debug
        print(f"    Teinte moyenne: {int(h_mean)}° | Saturation: {int(np.mean(s_channel))} | Valeur: {int(np.mean(v_channel))}")
        
        return h_min, s_min, v_min, h_max, s_max, v_max
    
    def calibrate_color(self, color_name, color_emoji):
        """
        Calibre une couleur en capturant l'image et analysant la région centrale
        
        :param color_name: Nom de la couleur (ex: "red", "green")
        :param color_emoji: Emoji pour l'affichage (ex: "🔴", "🟢")
        :return: True si succès, False sinon
        """
        print(f"\n{'='*60}")
        print(f"{color_emoji} CALIBRATION: {color_name.upper()}")
        print(f"{'='*60}")
        print("➤ Placez un objet de cette couleur au centre de la caméra")
        print("➤ Appuyez sur [ENTRÉE] pour capturer et calibrer...")
        
        input()  # Attendre l'appui sur Entrée
        
        print("📸 Capture en cours...", end=" ", flush=True)
        image = self.capture_frame()
        
        if image is None:
            print("ÉCHOUÉE ❌")
            return False
        
        print("OK ✓")
        print("🔍 Analyse de la couleur...", end=" ", flush=True)
        
        h_min, s_min, v_min, h_max, s_max, v_max = self.analyze_color_region(image)
        
        print("OK ✓")
        
        # Stocker les valeurs
        self.color_ranges[color_name] = {
            "emoji": color_emoji,
            "lower": [h_min, s_min, v_min],
            "upper": [h_max, s_max, v_max]
        }
        
        print(f"✅ Plage enregistrée:")
        print(f"    LOWER: H={h_min:3d}° S={s_min:3d} V={v_min:3d}")
        print(f"    UPPER: H={h_max:3d}° S={s_max:3d} V={v_max:3d}")
        
        return True
    
    def save_calibration(self, output_file="color_calibration.json"):
        """
        Sauvegarde la calibration dans un fichier JSON
        
        :param output_file: Nom du fichier de sortie
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        calibration_data = {
            "timestamp": timestamp,
            "colors": self.color_ranges
        }
        
        output_path = os.path.join("./Pictures", output_file)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(calibration_data, f, indent=4, ensure_ascii=False)
        
        print(f"\n💾 Calibration sauvegardée: {output_path}")
    
    def generate_python_code(self):
        """
        Génère le code Python pour intégrer dans camera_color_detection_ssh.py
        """
        print("\n" + "="*60)
        print("📝 CODE À INTÉGRER DANS camera_color_detection_ssh.py")
        print("="*60)
        print("\n# Plages de couleurs calibrées - Généré le", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print()
        
        for color_name, data in self.color_ranges.items():
            lower = data["lower"]
            upper = data["upper"]
            emoji = data["emoji"]
            
            var_name = color_name.upper()
            
            # Gestion du rouge qui peut avoir deux plages
            if color_name == "red" and lower[0] > 160:
                print(f"# {emoji} {color_name.upper()}")
                print(f"{var_name}_LOWER1 = np.array([0, {lower[1]}, {lower[2]}])")
                print(f"{var_name}_UPPER1 = np.array([10, {upper[1]}, {upper[2]}])")
                print(f"{var_name}_LOWER2 = np.array([{lower[0]}, {lower[1]}, {lower[2]}])")
                print(f"{var_name}_UPPER2 = np.array([180, {upper[1]}, {upper[2]}])")
            else:
                print(f"# {emoji} {color_name.upper()}")
                print(f"{var_name}_LOWER = np.array([{lower[0]}, {lower[1]}, {lower[2]}])")
                print(f"{var_name}_UPPER = np.array([{upper[0]}, {upper[1]}, {upper[2]}])")
            print()
    
    def cleanup(self):
        """Nettoie les fichiers temporaires"""
        if os.path.exists(self.temp_photo_path):
            try:
                os.remove(self.temp_photo_path)
            except:
                pass


def main():
    """Programme principal de calibration"""
    print("="*60)
    print("🎨 CALIBRATION DES COULEURS POUR DÉTECTION CAMÉRA")
    print("="*60)
    print()
    
    # Détection du type de caméra
    use_libcamera = os.path.exists("/usr/bin/rpicam-jpeg") or os.path.exists("/usr/bin/libcamera-still")
    
    if use_libcamera:
        print("[INFO] ✓ Caméra Raspberry Pi détectée - Mode rpicam")
    else:
        print("[INFO] ✓ Utilisation d'OpenCV - Mode USB/V4L2")
    
    print()
    print("📋 Vous allez calibrer les couleurs suivantes dans cet ordre:")
    print("   1. 🔴 ROUGE")
    print("   2. 🟣 MAGENTA")
    print("   3. 🔵 BLEU FONCÉ")
    print("   4. 💙 CYAN")
    print("   5. 🟢 VERT")
    print("   6. 🟡 JAUNE")
    print("   7. ⚪ BLANC")
    print()
    print("💡 Conseil: Utilisez des objets de couleur unie et bien éclairés")
    print()
    input("Appuyez sur [ENTRÉE] pour commencer...")
    
    # Initialisation du calibrateur
    calibrator = ColorCalibrator(use_libcamera)
    
    # Liste des couleurs à calibrer
    colors_to_calibrate = [
        ("red", "🔴"),
        ("magenta", "🟣"),
        ("darkblue", "🔵"),
        ("cyan", "💙"),
        ("green", "🟢"),
        ("yellow", "🟡"),
        ("white", "⚪")
    ]
    
    try:
        # Calibration de chaque couleur
        for color_name, emoji in colors_to_calibrate:
            success = calibrator.calibrate_color(color_name, emoji)
            if not success:
                print(f"⚠️  Échec de calibration pour {color_name}")
                retry = input("Voulez-vous réessayer? (o/n): ")
                if retry.lower() == 'o':
                    calibrator.calibrate_color(color_name, emoji)
        
        # Sauvegarde des résultats
        print("\n" + "="*60)
        print("✅ CALIBRATION TERMINÉE")
        print("="*60)
        
        calibrator.save_calibration()
        calibrator.generate_python_code()
        
        print("\n💡 Vous pouvez maintenant copier le code ci-dessus dans")
        print("   la classe ColorDetection de camera_color_detection_ssh.py")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Calibration interrompue par l'utilisateur")
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
    finally:
        calibrator.cleanup()
        print("\n🔚 Programme terminé")


if __name__ == "__main__":
    main()
