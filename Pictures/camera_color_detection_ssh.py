#!/usr/bin/env python3
"""
Script de détection des couleurs via caméra - Optimisé pour SSH (sans GUI)
Affiche directement dans le terminal les couleurs détectées
"""

import os
import time
import cv2
import numpy as np
from collections import deque
from datetime import datetime


class ColorDetection:
    """Détecte plusieurs couleurs dans une image"""

    # Plages de couleurs en HSV (H: 0-180, S: 0-255, V: 0-255)
    # IMPORTANT: OpenCV utilise H: 0-180 (pas 0-360 comme HSV classique)
    # Calibration personnalisée - Généré le 2025-12-16 15:21:22
    
    # 🔴 ROUGE
    RED_LOWER = np.array([0, 251, 249])
    RED_UPPER = np.array([6, 255, 255])
    
    # 🟣 MAGENTA
    MAGENTA_LOWER = np.array([149, 255, 254])
    MAGENTA_UPPER = np.array([150, 255, 255])
    
    # 🔵 BLEU FONCÉ
    DARKBLUE_LOWER = np.array([120, 255, 254])
    DARKBLUE_UPPER = np.array([120, 255, 254])
    
    # 💙 CYAN
    CYAN_LOWER = np.array([90, 152, 203])
    CYAN_UPPER = np.array([91, 173, 227])
    
    # 🟢 VERT
    GREEN_LOWER = np.array([62, 182, 231])
    GREEN_UPPER = np.array([69, 206, 251])
    
    # 🟡 JAUNE
    YELLOW_LOWER = np.array([31, 250, 224])
    YELLOW_UPPER = np.array([32, 255, 245])
    
    # ⚪ BLANC
    WHITE_LOWER = np.array([91, 28, 195])
    WHITE_UPPER = np.array([94, 41, 220])

    # Surface minimale pour considérer une couleur comme détectée
    MIN_CONTOUR_AREA = 200

    @staticmethod
    def detect_color(image):
        """
        Détecte plusieurs couleurs dans une image et calcule leurs surfaces.

        :param image: Image en format BGR (OpenCV)
        :return: Dictionnaire avec les couleurs, émojis et la surface détectée
        """
        # Conversion BGR -> HSV pour une meilleure détection des couleurs
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        detected_colors = {}  # {nom: emoji}
        color_areas = {}      # {nom: surface totale}

        # Détection du ROUGE
        mask_red = cv2.inRange(hsv, ColorDetection.RED_LOWER, ColorDetection.RED_UPPER)
        contours_red, _ = cv2.findContours(mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        red_area = sum(cv2.contourArea(c) for c in contours_red)
        if red_area > ColorDetection.MIN_CONTOUR_AREA:
            detected_colors['red'] = '🔴 ROUGE'
            color_areas['red'] = red_area

        # Détection du MAGENTA
        mask_magenta = cv2.inRange(hsv, ColorDetection.MAGENTA_LOWER, ColorDetection.MAGENTA_UPPER)
        contours_magenta, _ = cv2.findContours(mask_magenta, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        magenta_area = sum(cv2.contourArea(c) for c in contours_magenta)
        if magenta_area > ColorDetection.MIN_CONTOUR_AREA:
            detected_colors['magenta'] = '🟣 MAGENTA'
            color_areas['magenta'] = magenta_area

        # Détection du BLEU FONCÉ
        mask_darkblue = cv2.inRange(hsv, ColorDetection.DARKBLUE_LOWER, ColorDetection.DARKBLUE_UPPER)
        contours_darkblue, _ = cv2.findContours(mask_darkblue, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        darkblue_area = sum(cv2.contourArea(c) for c in contours_darkblue)
        if darkblue_area > ColorDetection.MIN_CONTOUR_AREA:
            detected_colors['darkblue'] = '🔵 BLEU FONCÉ'
            color_areas['darkblue'] = darkblue_area

        # Détection du CYAN
        mask_cyan = cv2.inRange(hsv, ColorDetection.CYAN_LOWER, ColorDetection.CYAN_UPPER)
        contours_cyan, _ = cv2.findContours(mask_cyan, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cyan_area = sum(cv2.contourArea(c) for c in contours_cyan)
        if cyan_area > ColorDetection.MIN_CONTOUR_AREA:
            detected_colors['cyan'] = '💙 CYAN'
            color_areas['cyan'] = cyan_area

        # Détection du VERT
        mask_green = cv2.inRange(hsv, ColorDetection.GREEN_LOWER, ColorDetection.GREEN_UPPER)
        contours_green, _ = cv2.findContours(mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        green_area = sum(cv2.contourArea(c) for c in contours_green)
        if green_area > ColorDetection.MIN_CONTOUR_AREA:
            detected_colors['green'] = '🟢 VERT'
            color_areas['green'] = green_area

        # Détection du JAUNE
        mask_yellow = cv2.inRange(hsv, ColorDetection.YELLOW_LOWER, ColorDetection.YELLOW_UPPER)
        contours_yellow, _ = cv2.findContours(mask_yellow, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        yellow_area = sum(cv2.contourArea(c) for c in contours_yellow)
        if yellow_area > ColorDetection.MIN_CONTOUR_AREA:
            detected_colors['yellow'] = '🟡 JAUNE'
            color_areas['yellow'] = yellow_area

        # Détection du BLANC
        mask_white = cv2.inRange(hsv, ColorDetection.WHITE_LOWER, ColorDetection.WHITE_UPPER)
        contours_white, _ = cv2.findContours(mask_white, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        white_area = sum(cv2.contourArea(c) for c in contours_white)
        if white_area > ColorDetection.MIN_CONTOUR_AREA:
            detected_colors['white'] = '⚪ BLANC'
            color_areas['white'] = white_area

        return detected_colors, color_areas

    @staticmethod
    def analyze_image(image_path):
        """
        Analyse une image stockée sur le disque.

        :param image_path: Chemin du fichier image
        :return: Tuple (dictionnaire des couleurs, dictionnaire des surfaces)
        """
        image = cv2.imread(image_path)

        if image is None:
            print(f"[ERREUR] Impossible de lire l'image : {image_path}")
            return {}, {}

        return ColorDetection.detect_color(image)


class CameraManager:
    """Gère la capture et l'analyse des photos de la caméra"""

    def __init__(self, photo_dir, buffer_size=5, use_libcamera=True):
        """
        Initialise le gestionnaire de caméra.

        :param photo_dir: Répertoire de stockage des photos
        :param buffer_size: Nombre maximum de photos en mémoire
        :param use_libcamera: Utiliser libcamera (Raspberry Pi) ou OpenCV
        """
        self.photo_dir = photo_dir
        self.photo_buffer = deque(maxlen=buffer_size)
        self.use_libcamera = use_libcamera
        self.ensure_directory_exists()
        self.captured_frames = 0

    def ensure_directory_exists(self):
        """Crée le répertoire s'il n'existe pas"""
        if not os.path.exists(self.photo_dir):
            os.makedirs(self.photo_dir)
            print(f"[INFO] Répertoire créé : {self.photo_dir}")

    def capture_photo_libcamera(self):
        """Capture une photo avec rpicam (Raspberry Pi Camera)"""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        photo_path = os.path.join(self.photo_dir, f"photo_{timestamp}.jpg")

        # Utilise rpicam-jpeg pour capturer une photo
        # --timeout=1000 = 1 seconde, puis capture et ferme
        cmd = f"rpicam-jpeg -o {photo_path} --timeout=1000 --nopreview 2>/dev/null"
        exit_code = os.system(cmd)

        if exit_code == 0 and os.path.exists(photo_path):
            self.photo_buffer.append(photo_path)
            return photo_path
        else:
            print(f"[ERREUR] Capture échouée avec rpicam")
            return None

    def capture_photo_opencv(self):
        """Capture une photo avec OpenCV (caméra USB ou V4L2)"""
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)

        if not cap.isOpened():
            print("[ERREUR] Impossible d'accéder à la caméra via OpenCV")
            return None

        # Configuration de la caméra
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

        ret, frame = cap.read()
        cap.release()

        if not ret:
            print("[ERREUR] Impossible de capturer une image")
            return None

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        photo_path = os.path.join(self.photo_dir, f"photo_{timestamp}.jpg")
        cv2.imwrite(photo_path, frame)
        self.photo_buffer.append(photo_path)
        return photo_path

    def capture_photo(self):
        """Capture une photo avec la méthode appropriée"""
        if self.use_libcamera:
            return self.capture_photo_libcamera()
        else:
            return self.capture_photo_opencv()

    def process_photos(self):
        """
        Analyse les photos du buffer et retourne les couleurs détectées et la couleur majoritaire.

        :return: Tuple (dictionnaire couleurs, dictionnaire surfaces)
        """
        all_detected_colors = {}
        all_color_areas = {}
        
        for photo in list(self.photo_buffer):
            detected_colors, color_areas = ColorDetection.analyze_image(photo)
            # Fusionner les résultats
            all_detected_colors.update(detected_colors)
            # Additionner les surfaces
            for color_name, area in color_areas.items():
                all_color_areas[color_name] = all_color_areas.get(color_name, 0) + area

        return all_detected_colors, all_color_areas
    
    def get_dominant_color(self, color_areas):
        """
        Retourne la couleur avec la plus grande surface détectée.

        :param color_areas: Dictionnaire des surfaces par couleur
        :return: Tuple (couleur_name, emoji, surface) ou None
        """
        if not color_areas:
            return None
        
        # Trouver la couleur avec la surface maximale
        dominant_color = max(color_areas.items(), key=lambda x: x[1])
        color_name = dominant_color[0]
        
        # Récupérer l'emoji correspondant (basé sur le dictionnaire de ColorDetection)
        color_emojis = {
            'red': '🔴 ROUGE',
            'magenta': '🟣 MAGENTA',
            'darkblue': '🔵 BLEU FONCÉ',
            'cyan': '💙 CYAN',
            'green': '🟢 VERT',
            'yellow': '🟡 JAUNE',
            'white': '⚪ BLANC'
        }
        
        emoji = color_emojis.get(color_name, '❓ INCONNU')
        area = dominant_color[1]
        
        return color_name, emoji, area

    def cleanup_old_photos(self):
        """Supprime les anciennes photos si le buffer est plein"""
        while len(self.photo_buffer) > self.photo_buffer.maxlen - 1:
            oldest_photo = self.photo_buffer.popleft()
            if os.path.exists(oldest_photo):
                try:
                    os.remove(oldest_photo)
                except Exception as e:
                    print(f"[ERREUR] Suppression échouée : {e}")


def main():
    """Boucle principale de détection"""
    print("=" * 60)
    print("🎥 DÉTECTION DE COULEUR VIA CAMÉRA - SSH MODE")
    print("=" * 60)
    print(f"[INFO] Démarrage à {datetime.now().strftime('%H:%M:%S')}")
    print("[INFO] Pressez Ctrl+C pour arrêter\n")

    # Configuration
    PHOTO_DIR = "./Pictures/photos"
    BUFFER_SIZE = 5
    CAPTURE_INTERVAL = 0.5  # Secondes entre chaque capture

    # Déterminer la méthode de capture
    use_libcamera = os.path.exists("/usr/bin/rpicam-jpeg") or os.path.exists("/usr/bin/libcamera-still")
    if use_libcamera:
        print("[INFO] ✓ Caméra Raspberry Pi détectée - Mode rpicam\n")
    else:
        print("[INFO] ✓ Utilisation d'OpenCV - Mode USB/V4L2\n")

    # Initialisation du gestionnaire
    camera_manager = CameraManager(PHOTO_DIR, BUFFER_SIZE, use_libcamera)

    try:
        frame_count = 0
        while True:
            frame_count += 1
            timestamp = datetime.now().strftime("%H:%M:%S")

            print(f"[{timestamp}] Frame #{frame_count} - Capture en cours...", end=" ", flush=True)

            # Capture une photo
            photo_path = camera_manager.capture_photo()

            if photo_path is None:
                print("ÉCHOUÉE ❌")
                time.sleep(CAPTURE_INTERVAL)
                continue

            print("OK ✓ | ", end="", flush=True)

            # Analyse la photo
            detected_colors, color_areas = camera_manager.process_photos()

            # Affichage du résultat
            if detected_colors:
                # Trouver la couleur majoritaire
                dominant = camera_manager.get_dominant_color(color_areas)
                if dominant:
                    color_name, emoji, area = dominant
                    print(f"Détectée: {emoji} (surface: {int(area)})")
                else:
                    colors_display = " + ".join(detected_colors.values())
                    print(f"Couleurs: {colors_display}")
            else:
                print("⚪ Aucune couleur")

            # Nettoyage des anciennes photos
            camera_manager.cleanup_old_photos()

            # Pause avant la prochaine capture
            time.sleep(CAPTURE_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n[INFO] Arrêt demandé par l'utilisateur...")
    except Exception as e:
        print(f"\n[ERREUR] Exception : {e}")
    finally:
        print(f"[INFO] Fermeture - {frame_count} frames traitées")
        print(f"[INFO] Arrêt à {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)


if __name__ == "__main__":
    main()
