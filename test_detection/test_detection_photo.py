#!/usr/bin/env python3
"""
Version avancée du test de détection d'obstacles avec configuration personnalisée
Utilise les paramètres du fichier config.py
"""

import os
import sys
import cv2
import time
import logging
from datetime import datetime

# Ajouter le dossier parent au path pour importer les modules hexapod
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hexapod.camera import FastCamera
from hexapod.obstacle_detector import ObstacleDetector
from hexapod.keyboard_handler import KeyboardHandler

# Importer la configuration personnalisée
try:
    from config import (get_camera_config, get_detection_config, get_save_config, 
                       get_display_config, get_colors, get_messages)
except ImportError:
    print("Attention: config.py non trouvé, utilisation des paramètres par défaut")
    # Valeurs par défaut si config.py n'existe pas
    def get_camera_config(): return {'width': 640, 'height': 480, 'fps': 15}
    def get_detection_config(): return {'min_area': 800, 'roi_top': 0.3, 'roi_bottom': 0.9, 'edge_thresh': 50}
    def get_save_config(): return {'photos_dir': 'photos_obstacles', 'save_original': False, 'jpeg_quality': 90}
    def get_display_config(): return {'show_roi_lines': True, 'show_thirds': True, 'show_obstacle_numbers': True, 'danger_frame_thickness': 3, 'obstacle_frame_thickness': 2}
    def get_colors(): return {'danger': {'OK': (0, 255, 0), 'OBS': (0, 255, 255), 'WARN': (0, 165, 255), 'STOP': (0, 0, 255), 'INIT': (128, 128, 128)}, 'position': {'G': (255, 0, 0), 'C': (0, 0, 255), 'D': (0, 255, 0)}, 'roi_lines': (255, 255, 0), 'text_bg': (0, 0, 0), 'text_fg': (255, 255, 255)}
    def get_messages(): return {'ready': "Prêt! Appuyez sur ESPACE pour prendre une photo...", 'capturing': "Prise de photo en cours...", 'success': "Photo avec détection sauvegardée!", 'error': "Erreur lors de la prise de photo", 'quit': "Au revoir!"}

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AdvancedPhotoDetectionTester:
    """
    Version avancée du testeur de détection d'obstacles avec configuration personnalisable.
    """
    
    def __init__(self):
        # Charger les configurations
        self.camera_config = get_camera_config()
        self.detection_config = get_detection_config()
        self.save_config = get_save_config()
        self.display_config = get_display_config()
        self.colors = get_colors()
        self.messages = get_messages()
        
        # Initialiser les composants
        self.camera = None
        self.detector = None
        self.keyboard = None
        
        # Créer le dossier de sauvegarde
        photos_dir = self.save_config['photos_dir']
        if not os.path.exists(photos_dir):
            os.makedirs(photos_dir)
            logger.info(f"Dossier créé: {photos_dir}")
    
    def setup(self):
        """Initialise tous les composants avec la configuration"""
        try:
            logger.info("Initialisation de la caméra...")
            self.camera = FastCamera(
                width=self.camera_config['width'],
                height=self.camera_config['height'],
                fps=self.camera_config['fps']
            )
            
            logger.info("Initialisation du détecteur d'obstacles...")
            self.detector = ObstacleDetector(
                min_area=self.detection_config['min_area'],
                roi_top=self.detection_config['roi_top'],
                roi_bottom=self.detection_config['roi_bottom'],
                edge_thresh=self.detection_config['edge_thresh']
            )
            
            logger.info("Initialisation du gestionnaire clavier...")
            self.keyboard = KeyboardHandler()
            
            # Attendre que la caméra soit prête
            time.sleep(2)
            logger.info("Système prêt!")
            return True
            
        except Exception as e:
            logger.error(f"Erreur d'initialisation: {e}")
            return False
    
    def take_photo_with_detection(self):
        """Prend une photo et détecte les obstacles avec configuration avancée"""
        try:
            # Capturer une frame
            frame = self.camera.get_frame()
            if frame is None:
                logger.warning("Impossible de capturer une frame")
                return False
            
            logger.info("Photo capturée, analyse en cours...")
            
            # Sauvegarder l'image originale si demandé
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if self.save_config['save_original']:
                original_filename = f"original_{timestamp}.jpg"
                original_filepath = os.path.join(self.save_config['photos_dir'], original_filename)
                cv2.imwrite(original_filepath, frame, [cv2.IMWRITE_JPEG_QUALITY, self.save_config['jpeg_quality']])
                logger.info(f"Image originale sauvegardée: {original_filepath}")
            
            # Détecter les obstacles
            obstacles, danger, position = self.detector.detect(frame)
            
            # Dessiner les obstacles détectés sur l'image
            annotated_frame = frame.copy()
            self.draw_obstacles_advanced(annotated_frame, obstacles, danger, position)
            
            # Sauvegarder l'image annotée
            detected_filename = f"obstacle_detection_{timestamp}.jpg"
            detected_filepath = os.path.join(self.save_config['photos_dir'], detected_filename)
            
            success = cv2.imwrite(detected_filepath, annotated_frame, 
                                [cv2.IMWRITE_JPEG_QUALITY, self.save_config['jpeg_quality']])
            
            if success:
                logger.info(f"Photo avec détection sauvegardée: {detected_filepath}")
                self.log_detection_results(obstacles, danger, position)
            else:
                logger.error(f"Impossible de sauvegarder: {detected_filepath}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la capture: {e}")
            return False
    
    def log_detection_results(self, obstacles, danger, position):
        """Log les résultats de détection de manière détaillée"""
        logger.info(f"=== RÉSULTATS DE DÉTECTION ===")
        logger.info(f"Obstacles détectés: {len(obstacles)}")
        logger.info(f"Niveau de danger: {danger}")
        if position:
            logger.info(f"Position des obstacles: {position}")
        
        if obstacles:
            logger.info("Détails des obstacles:")
            for i, obs in enumerate(obstacles, 1):
                x, y, w, h = obs['bbox']
                area = w * h
                logger.info(f"  Obstacle {i}: "
                          f"Position={obs['pos']}, "
                          f"Distance={obs['dist']:.3f}, "
                          f"Taille={obs['size']}, "
                          f"Aire={area}px², "
                          f"Bbox=({x},{y},{w},{h})")
        logger.info("=" * 30)
    
    def draw_obstacles_advanced(self, frame, obstacles, danger, position):
        """Version avancée du dessin avec configuration personnalisée"""
        h, w = frame.shape[:2]
        colors = self.colors
        display = self.display_config
        
        # Couleur selon le niveau de danger
        danger_color = colors['danger'].get(danger, colors['text_fg'])
        
        # Dessiner un cadre global avec la couleur du danger
        if display.get('danger_frame_thickness', 3) > 0:
            thickness = display['danger_frame_thickness']
            cv2.rectangle(frame, (5, 5), (w-5, h-5), danger_color, thickness)
        
        # Texte d'information principal
        info_lines = []
        info_lines.append(f"Danger: {danger}")
        if position:
            info_lines.append(f"Position: {position}")
        info_lines.append(f"Obstacles: {len(obstacles)}")
        
        # Affichage du texte avec fond
        y_offset = 25
        for line in info_lines:
            text_size = cv2.getTextSize(line, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
            # Fond du texte
            cv2.rectangle(frame, (8, y_offset - 20), (15 + text_size[0], y_offset + 5), 
                         colors['text_bg'], -1)
            # Texte
            cv2.putText(frame, line, (10, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, danger_color, 2)
            y_offset += 30
        
        # Dessiner les zones ROI si activé
        if display.get('show_roi_lines', True):
            roi_top = int(h * self.detection_config['roi_top'])
            roi_bottom = int(h * self.detection_config['roi_bottom'])
            roi_color = colors.get('roi_lines', (255, 255, 0))
            
            cv2.line(frame, (0, roi_top), (w, roi_top), roi_color, 1)
            cv2.line(frame, (0, roi_bottom), (w, roi_bottom), roi_color, 1)
            
            # Labels ROI
            cv2.putText(frame, "ROI START", (w - 100, roi_top - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, roi_color, 1)
            cv2.putText(frame, "ROI END", (w - 80, roi_bottom + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, roi_color, 1)
        
        # Divisions tiers si activé
        if display.get('show_thirds', True):
            third_w = w // 3
            roi_top = int(h * self.detection_config['roi_top'])
            roi_bottom = int(h * self.detection_config['roi_bottom'])
            roi_color = colors.get('roi_lines', (255, 255, 0))
            
            cv2.line(frame, (third_w, roi_top), (third_w, roi_bottom), roi_color, 1)
            cv2.line(frame, (2 * third_w, roi_top), (2 * third_w, roi_bottom), roi_color, 1)
            
            # Labels des zones
            cv2.putText(frame, "G", (third_w//2 - 10, roi_top + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, roi_color, 2)
            cv2.putText(frame, "C", (third_w + (third_w//2) - 10, roi_top + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, roi_color, 2)
            cv2.putText(frame, "D", (2*third_w + (third_w//2) - 10, roi_top + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, roi_color, 2)
        
        # Dessiner chaque obstacle
        for i, obs in enumerate(obstacles):
            x, y, w_obs, h_obs = obs['bbox']
            pos = obs['pos']
            dist = obs['dist']
            size = obs['size']
            area = w_obs * h_obs
            
            # Couleur selon la position
            color = colors['position'].get(pos, colors['text_fg'])
            thickness = display.get('obstacle_frame_thickness', 2)
            
            # Rectangle autour de l'obstacle
            cv2.rectangle(frame, (x, y), (x + w_obs, y + h_obs), color, thickness)
            
            # Labels détaillés
            label = f"{pos}:{size}:D{dist:.2f}:A{area}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
            
            # Fond pour le texte
            cv2.rectangle(frame, (x, y - 22), (x + label_size[0] + 4, y), color, -1)
            cv2.putText(frame, label, (x + 2, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colors['text_bg'], 1)
            
            # Numéro de l'obstacle si activé
            if display.get('show_obstacle_numbers', True):
                cv2.putText(frame, str(i + 1), (x + w_obs - 20, y + 20), 
                          cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
        
        # Timestamp dans le coin
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, h - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, colors['text_fg'], 1)
    
    def show_config_info(self):
        """Affiche les informations de configuration"""
        print("\n" + "="*60)
        print("CONFIGURATION ACTUELLE")
        print("="*60)
        print(f"Caméra: {self.camera_config['width']}x{self.camera_config['height']} @ {self.camera_config['fps']}fps")
        print(f"ROI: {self.detection_config['roi_top']:.1%} - {self.detection_config['roi_bottom']:.1%}")
        print(f"Aire minimale obstacles: {self.detection_config['min_area']} pixels²")
        print(f"Seuil contours: {self.detection_config['edge_thresh']}")
        print(f"Dossier photos: {self.save_config['photos_dir']}")
        print(f"Qualité JPEG: {self.save_config['jpeg_quality']}%")
        print(f"Sauver original: {'Oui' if self.save_config['save_original'] else 'Non'}")
        print("="*60)
    
    def run(self):
        """Boucle principale avec interface avancée"""
        if not self.setup():
            return False
        
        try:
            print("\n" + "="*70)
            print("TEST AVANCÉ DE DÉTECTION D'OBSTACLES AVEC PHOTO")
            print("="*70)
            print("Commandes:")
            print("  [ESPACE] - Prendre une photo et détecter les obstacles")
            print("  [c] - Afficher la configuration actuelle")
            print("  [s] - Statistiques de session")
            print("  [q] - Quitter")
            print("  [h] - Afficher cette aide")
            print("="*70)
            print(self.messages.get('ready', "Prêt!"))
            
            photo_count = 0
            obstacle_count_total = 0
            start_time = time.time()
            
            while True:
                key = self.keyboard.get_key()
                
                if key == ' ':  # ESPACE
                    print(f"\n{self.messages.get('capturing', 'Capture...')}")
                    if self.take_photo_with_detection():
                        photo_count += 1
                        print(f"{self.messages.get('success', 'Succès!')} (Photo #{photo_count})")
                    else:
                        print(self.messages.get('error', 'Erreur!'))
                    print(f"Appuyez sur ESPACE pour photo #{photo_count + 1}...")
                
                elif key == 'c' or key == 'C':
                    self.show_config_info()
                
                elif key == 's' or key == 'S':
                    runtime = time.time() - start_time
                    print(f"\nSTATISTIQUES DE SESSION:")
                    print(f"  Photos prises: {photo_count}")
                    print(f"  Durée: {runtime:.1f}s")
                    if photo_count > 0:
                        print(f"  Moyenne: {runtime/photo_count:.1f}s par photo")
                
                elif key == 'q' or key == 'Q':
                    print(f"\n{self.messages.get('quit', 'Au revoir!')}")
                    break
                
                elif key == 'h' or key == 'H':
                    print("\nAIDE:")
                    print("  [ESPACE] - Prendre une photo et détecter les obstacles")
                    print("  [c] - Afficher la configuration actuelle")
                    print("  [s] - Statistiques de session")
                    print("  [q] - Quitter")
                    print("  [h] - Afficher cette aide")
                
                # Petite pause pour éviter la surcharge CPU
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            print(f"\n{self.messages.get('quit', 'Au revoir!')}")
        
        finally:
            self.cleanup()
        
        return True
    
    def cleanup(self):
        """Nettoie les ressources"""
        try:
            if self.camera:
                self.camera.stop()
                logger.info("Caméra arrêtée")
            
            if self.keyboard:
                # Restaurer les paramètres du terminal
                import termios
                termios.tcsetattr(self.keyboard.fd, termios.TCSADRAIN, self.keyboard.old_settings)
                logger.info("Terminal restauré")
                
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage: {e}")


def main():
    """Point d'entrée principal"""
    try:
        tester = AdvancedPhotoDetectionTester()
        return tester.run()
    
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)