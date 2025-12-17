#!/usr/bin/env python3
"""
Script de Streaming Vidéo MJPEG avec Détection d'Obstacles - V1
Détecte les obstacles au sol devant l'hexapode
Accessible en SSH: ssh -L 8080:localhost:8080 user@rpi_ip
"""

import os
import cv2
import numpy as np
import threading
import time
import logging
import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
from datetime import datetime
import tempfile
import signal
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CameraStreamRPiCAM:
    """Capture vidéo via rpicam-jpeg en continu"""
    
    def __init__(self, width=640, height=480, fps=15):
        self.width = width
        self.height = height
        self.fps = fps
        self.temp_dir = tempfile.mkdtemp()
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.frame_count = 0
        self.capture_thread = None
        
        logger.info(f"Initialisation camera {width}x{height} @ {fps} FPS...")
        logger.info(f"Répertoire temp: {self.temp_dir}")
        self._start_camera_stream()
    
    def _start_camera_stream(self):
        """Lance le thread de capture d'images"""
        try:
            self.running = True
            
            # Thread pour capturer les images en boucle
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            
            logger.info("✓ Camera stream lancé (rpicam-jpeg)")
            
        except Exception as e:
            logger.error(f"✗ Erreur démarrage camera: {e}")
            self.running = False
    
    def _capture_loop(self):
        """Capture des images JPEG en boucle"""
        frame_delay = 1.0 / self.fps
        frame_id = 0
        
        try:
            while self.running:
                start_time = time.time()
                
                # Fichier de sortie temporaire
                frame_file = os.path.join(self.temp_dir, "current_frame.jpg")
                
                # Capturer une image unique avec rpicam-jpeg
                cmd = [
                    'rpicam-jpeg',
                    '--width', str(self.width),
                    '--height', str(self.height),
                    '--timeout', '1000',
                    '--quality', '80',
                    '--output', frame_file,
                    '--nopreview'
                ]
                
                process = None
                try:
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    
                    try:
                        stdout, stderr = process.communicate(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                        raise
                    
                    if os.path.exists(frame_file):
                        frame = cv2.imread(frame_file)
                        
                        if frame is not None:
                            with self.frame_lock:
                                self.current_frame = frame.copy()
                                self.frame_count += 1
                            
                            frame_id += 1
                            
                            if frame_id == 1:
                                logger.info(f"✓ Première frame capturée ({frame.shape})")
                            elif frame_id % 50 == 0:
                                logger.debug(f"Frame {frame_id} capturée")
                        else:
                            logger.warning(f"Frame vide lue depuis {frame_file}")
                    else:
                        logger.warning(f"Fichier {frame_file} non créé")
                
                except subprocess.TimeoutExpired:
                    logger.warning("Timeout lors de la capture (>3s)")
                    if process:
                        try:
                            process.kill()
                            process.wait()
                        except:
                            pass
                except Exception as e:
                    logger.error(f"Erreur capture frame: {e}")
                    if process and process.poll() is None:
                        try:
                            process.kill()
                            process.wait()
                        except:
                            pass
                
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_delay - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        except Exception as e:
            logger.error(f"Erreur dans la boucle de capture: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
            logger.info("Boucle de capture arrêtée")
    
    def get_frame(self):
        """Récupère la frame actuelle"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def stop(self):
        """Arrête la capture"""
        logger.info("Arrêt de la capture caméra...")
        self.running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2)
        
        try:
            import shutil
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.info(f"Répertoire temp nettoyé: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Erreur nettoyage temp: {e}")


class ObstacleDetector:
    """
    Détection d'obstacles au sol pour hexapode
    
    Méthodes utilisées:
    1. Détection de contours (edges)
    2. Analyse de différence de couleur par rapport au sol
    3. Détection de changements de texture
    4. Zone d'intérêt (ROI) focalisée sur le sol devant
    """
    
    def __init__(self, 
                 min_obstacle_area=500,
                 edge_threshold_low=50,
                 edge_threshold_high=150,
                 roi_top_percent=0.4,
                 roi_bottom_percent=0.95,
                 ground_sample_height=30,
                 color_diff_threshold=40,
                 enabled=True):
        """
        Paramètres:
        - min_obstacle_area: Surface minimum pour considérer un obstacle (pixels²)
        - edge_threshold_low/high: Seuils pour Canny edge detection
        - roi_top_percent: Début de la zone d'intérêt (% depuis le haut)
        - roi_bottom_percent: Fin de la zone d'intérêt
        - ground_sample_height: Hauteur de la zone pour échantillonner la couleur du sol
        - color_diff_threshold: Seuil de différence de couleur pour détecter un obstacle
        """
        self.min_obstacle_area = min_obstacle_area
        self.edge_threshold_low = edge_threshold_low
        self.edge_threshold_high = edge_threshold_high
        self.roi_top_percent = roi_top_percent
        self.roi_bottom_percent = roi_bottom_percent
        self.ground_sample_height = ground_sample_height
        self.color_diff_threshold = color_diff_threshold
        self.enabled = enabled
        
        # Couleur de référence du sol (sera mise à jour dynamiquement)
        self.ground_color_hsv = None
        self.ground_color_lab = None
        
        # Historique pour stabilisation
        self.obstacle_history = []
        self.history_size = 5
        
        logger.info("✓ Détecteur d'obstacles initialisé")
        logger.info(f"  - Surface min obstacle: {min_obstacle_area} px²")
        logger.info(f"  - Zone ROI: {roi_top_percent*100:.0f}% - {roi_bottom_percent*100:.0f}%")
    
    def _get_roi(self, frame):
        """Extrait la région d'intérêt (le sol devant l'hexapode)"""
        h, w = frame.shape[:2]
        top = int(h * self.roi_top_percent)
        bottom = int(h * self.roi_bottom_percent)
        return frame[top:bottom, :], top, bottom
    
    def _sample_ground_color(self, frame):
        """
        Échantillonne la couleur du sol en bas de l'image
        (zone supposée être du sol sans obstacle)
        """
        h, w = frame.shape[:2]
        
        # Zone d'échantillonnage: bas de l'image, partie centrale
        sample_top = h - self.ground_sample_height - 10
        sample_bottom = h - 10
        sample_left = w // 4
        sample_right = 3 * w // 4
        
        ground_sample = frame[sample_top:sample_bottom, sample_left:sample_right]
        
        # Convertir en HSV et LAB pour analyse couleur robuste
        hsv = cv2.cvtColor(ground_sample, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(ground_sample, cv2.COLOR_BGR2LAB)
        
        # Calculer la couleur moyenne
        self.ground_color_hsv = np.mean(hsv, axis=(0, 1))
        self.ground_color_lab = np.mean(lab, axis=(0, 1))
        
        return ground_sample
    
    def _detect_by_color_difference(self, roi, roi_hsv, roi_lab):
        """Détecte les zones différentes du sol par couleur"""
        if self.ground_color_lab is None:
            return np.zeros(roi.shape[:2], dtype=np.uint8)
        
        # Calcul de la différence en espace LAB (plus perceptuellement uniforme)
        diff = np.abs(roi_lab.astype(np.float32) - self.ground_color_lab)
        
        # Pondération des canaux L, A, B
        weighted_diff = diff[:, :, 0] * 0.3 + diff[:, :, 1] * 0.4 + diff[:, :, 2] * 0.3
        
        # Seuillage
        mask = (weighted_diff > self.color_diff_threshold).astype(np.uint8) * 255
        
        # Morphologie pour nettoyer
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        
        return mask
    
    def _detect_by_edges(self, roi_gray):
        """Détecte les contours potentiels d'obstacles"""
        # Flou gaussien pour réduire le bruit
        blurred = cv2.GaussianBlur(roi_gray, (5, 5), 0)
        
        # Détection de contours Canny
        edges = cv2.Canny(blurred, self.edge_threshold_low, self.edge_threshold_high)
        
        # Dilatation pour connecter les contours proches
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edges = cv2.dilate(edges, kernel, iterations=2)
        
        return edges
    
    def _detect_by_texture(self, roi_gray):
        """Détecte les changements de texture (obstacles texturés)"""
        # Calcul du Laplacien (variance = mesure de texture)
        laplacian = cv2.Laplacian(roi_gray, cv2.CV_64F)
        
        # Variance locale avec un kernel
        kernel_size = 15
        local_mean = cv2.blur(laplacian, (kernel_size, kernel_size))
        local_sqr_mean = cv2.blur(laplacian**2, (kernel_size, kernel_size))
        local_var = local_sqr_mean - local_mean**2
        
        # Normaliser et seuiller
        local_var = np.abs(local_var)
        local_var = (local_var / local_var.max() * 255).astype(np.uint8) if local_var.max() > 0 else local_var.astype(np.uint8)
        
        # Seuillage adaptatif
        _, texture_mask = cv2.threshold(local_var, 30, 255, cv2.THRESH_BINARY)
        
        return texture_mask
    
    def _find_obstacles(self, combined_mask, roi_top):
        """Trouve les contours et classifie les obstacles"""
        obstacles = []
        
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            
            if area < self.min_obstacle_area:
                continue
            
            # Bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Ajuster Y pour les coordonnées globales
            y_global = y + roi_top
            
            # Calculer le centre
            cx = x + w // 2
            cy = y_global + h // 2
            
            # Estimer la distance (basé sur la position Y - plus bas = plus proche)
            # Normaliser entre 0 (loin) et 1 (proche)
            distance_score = (cy - roi_top) / (combined_mask.shape[0])
            
            # Classifier la taille de l'obstacle
            if area < 1000:
                size_class = "petit"
            elif area < 5000:
                size_class = "moyen"
            else:
                size_class = "grand"
            
            # Classifier la position
            frame_third = combined_mask.shape[1] // 3
            if cx < frame_third:
                position = "gauche"
            elif cx > 2 * frame_third:
                position = "droite"
            else:
                position = "centre"
            
            obstacles.append({
                'bbox': (x, y_global, w, h),
                'center': (cx, cy),
                'area': area,
                'size_class': size_class,
                'position': position,
                'distance_score': distance_score,
                'contour': contour
            })
        
        # Trier par proximité (distance_score décroissant)
        obstacles.sort(key=lambda o: o['distance_score'], reverse=True)
        
        return obstacles
    
    def _get_danger_level(self, obstacles):
        """Évalue le niveau de danger global"""
        if not obstacles:
            return "LIBRE", (0, 255, 0)  # Vert
        
        # Vérifier les obstacles proches au centre
        for obs in obstacles:
            if obs['distance_score'] > 0.7 and obs['position'] == "centre":
                return "DANGER", (0, 0, 255)  # Rouge
            if obs['distance_score'] > 0.5 and obs['size_class'] in ["moyen", "grand"]:
                return "ATTENTION", (0, 165, 255)  # Orange
        
        return "OBSTACLE", (0, 255, 255)  # Jaune
    
    def detect(self, frame):
        """
        Détecte les obstacles dans l'image
        
        Returns:
            frame: Image annotée
            obstacles: Liste des obstacles détectés
            danger_level: Niveau de danger
        """
        if not self.enabled:
            return frame, [], ("DÉSACTIVÉ", (128, 128, 128))
        
        try:
            h, w = frame.shape[:2]
            
            # Échantillonner la couleur du sol
            self._sample_ground_color(frame)
            
            # Extraire la ROI
            roi, roi_top, roi_bottom = self._get_roi(frame)
            
            # Convertir en différents espaces colorimétriques
            roi_gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
            roi_lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB)
            
            # Méthode 1: Différence de couleur
            color_mask = self._detect_by_color_difference(roi, roi_hsv, roi_lab)
            
            # Méthode 2: Détection de contours
            edge_mask = self._detect_by_edges(roi_gray)
            
            # Méthode 3: Analyse de texture (optionnel, peut être désactivé pour performance)
            # texture_mask = self._detect_by_texture(roi_gray)
            
            # Combiner les masques
            combined_mask = cv2.bitwise_or(color_mask, edge_mask)
            # combined_mask = cv2.bitwise_or(combined_mask, texture_mask)
            
            # Nettoyage final
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
            combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_OPEN, kernel)
            
            # Trouver les obstacles
            obstacles = self._find_obstacles(combined_mask, roi_top)
            
            # Évaluer le danger
            danger_level, danger_color = self._get_danger_level(obstacles)
            
            # Dessiner la zone ROI
            cv2.rectangle(frame, (0, roi_top), (w, roi_bottom), (100, 100, 100), 1)
            cv2.putText(frame, "Zone detection", (5, roi_top + 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, (100, 100, 100), 1)
            
            # Dessiner les obstacles détectés
            for i, obs in enumerate(obstacles):
                x, y, bw, bh = obs['bbox']
                color = danger_color
                
                # Rectangle autour de l'obstacle
                cv2.rectangle(frame, (x, y), (x + bw, y + bh), color, 2)
                
                # Label
                label = f"{obs['size_class']} - {obs['position']}"
                cv2.putText(frame, label, (x, y - 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)
                
                # Indicateur de distance
                dist_bar_width = int(obs['distance_score'] * 50)
                cv2.rectangle(frame, (x, y + bh + 2), (x + dist_bar_width, y + bh + 8), color, -1)
            
            # Indicateur de danger global
            cv2.rectangle(frame, (w - 120, 10), (w - 10, 40), danger_color, -1)
            cv2.putText(frame, danger_level, (w - 115, 32),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            # Ligne de référence du sol
            cv2.line(frame, (0, h - self.ground_sample_height - 10), 
                    (w, h - self.ground_sample_height - 10), (255, 255, 0), 1)
            cv2.putText(frame, "Ref. sol", (5, h - self.ground_sample_height - 15),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.3, (255, 255, 0), 1)
            
            return frame, obstacles, (danger_level, danger_color)
            
        except Exception as e:
            logger.error(f"Erreur détection: {e}")
            import traceback
            traceback.print_exc()
            return frame, [], ("ERREUR", (128, 0, 128))


class MJPEGStreamHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour le stream MJPEG"""
    
    shared_frame = None
    shared_lock = threading.Lock()
    shared_stats = {'fps': 0, 'timestamp': '', 'obstacles': 0, 'danger': 'INIT'}
    
    def do_GET(self):
        """Gère les requêtes GET"""
        if self.path == '/':
            self.send_index()
        elif self.path == '/stream':
            self.send_mjpeg_stream()
        elif self.path == '/status':
            self.send_status()
        else:
            self.send_error(404, "Not Found")
    
    def send_index(self):
        """Envoie la page HTML avec la vidéo"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Hexapode - Détection Obstacles</title>
            <style>
                body { 
                    font-family: Arial; 
                    text-align: center; 
                    background: #1a1a2e; 
                    color: #eee; 
                    margin: 20px; 
                }
                h1 { color: #00ff88; }
                #video { 
                    max-width: 90%; 
                    border: 3px solid #00ff88; 
                    border-radius: 10px;
                    box-shadow: 0 0 20px rgba(0, 255, 136, 0.3);
                }
                .info { 
                    margin-top: 20px; 
                    font-size: 14px; 
                    background: #16213e;
                    padding: 15px;
                    border-radius: 10px;
                    display: inline-block;
                }
                .code { 
                    background: #0f0f23; 
                    padding: 10px; 
                    border-radius: 5px; 
                    font-family: monospace;
                    color: #00ff88;
                }
                .legend {
                    margin-top: 20px;
                    text-align: left;
                    display: inline-block;
                    background: #16213e;
                    padding: 15px;
                    border-radius: 10px;
                }
                .legend-item {
                    margin: 5px 0;
                    display: flex;
                    align-items: center;
                }
                .legend-color {
                    width: 20px;
                    height: 20px;
                    margin-right: 10px;
                    border-radius: 3px;
                }
                .status {
                    margin-top: 15px;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                }
            </style>
            <script>
                function updateStatus() {
                    fetch('/status')
                        .then(r => r.json())
                        .then(data => {
                            document.getElementById('fps').textContent = data.fps.toFixed(1);
                            document.getElementById('obstacles').textContent = data.obstacles;
                            document.getElementById('danger').textContent = data.danger;
                            let statusDiv = document.getElementById('status');
                            statusDiv.className = 'status';
                            if (data.danger === 'DANGER') {
                                statusDiv.style.background = '#ff0000';
                            } else if (data.danger === 'ATTENTION') {
                                statusDiv.style.background = '#ffa500';
                            } else if (data.danger === 'OBSTACLE') {
                                statusDiv.style.background = '#ffff00';
                                statusDiv.style.color = '#000';
                            } else {
                                statusDiv.style.background = '#00ff00';
                                statusDiv.style.color = '#000';
                            }
                        })
                        .catch(e => {});
                }
                setInterval(updateStatus, 500);
            </script>
        </head>
        <body>
            <h1>🤖 Hexapode - Détection d'Obstacles</h1>
            <img id="video" src="/stream" />
            
            <div id="status" class="status" style="background: #666;">
                État: <span id="danger">INIT</span> | 
                Obstacles: <span id="obstacles">0</span> | 
                FPS: <span id="fps">0</span>
            </div>
            
            <div class="legend">
                <h3>Légende:</h3>
                <div class="legend-item">
                    <div class="legend-color" style="background: #00ff00;"></div>
                    <span>LIBRE - Aucun obstacle détecté</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ffff00;"></div>
                    <span>OBSTACLE - Obstacle détecté (éloigné)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ffa500;"></div>
                    <span>ATTENTION - Obstacle proche ou grand</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ff0000;"></div>
                    <span>DANGER - Obstacle proche au centre</span>
                </div>
            </div>
            
            <div class="info">
                <h3>Accès SSH depuis PC:</h3>
                <div class="code">ssh -L 8080:localhost:8080 user@[IP_RASPBERRY]</div>
                <p>Puis ouvrir: <code>http://localhost:8080</code></p>
            </div>
        </body>
        </html>
        """
        
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', len(html))
        self.end_headers()
        self.wfile.write(html.encode())
    
    def send_status(self):
        """Envoie le status en JSON"""
        import json
        with self.shared_lock:
            status = json.dumps(self.shared_stats)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', len(status))
        self.end_headers()
        self.wfile.write(status.encode())
    
    def send_mjpeg_stream(self):
        """Envoie le stream MJPEG"""
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=FRAME')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        try:
            while True:
                with self.shared_lock:
                    frame = self.shared_frame
                
                if frame is not None:
                    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    
                    if ret:
                        self.wfile.write(b'--FRAME\r\n')
                        self.wfile.write(b'Content-Type: image/jpeg\r\n')
                        self.wfile.write(f'Content-Length: {len(buffer)}\r\n\r\n'.encode())
                        self.wfile.write(buffer)
                        self.wfile.write(b'\r\n')
                
                time.sleep(0.05)
        
        except Exception as e:
            logger.debug(f"Client déconnecté: {e}")
    
    def log_message(self, format, *args):
        """Supprime les logs HTTP verbeux"""
        return


class HexapodeObstacleStreamer:
    """Orchestrateur principal pour la détection d'obstacles"""
    
    def __init__(self, port=8080, 
                 min_obstacle_area=500,
                 color_threshold=40,
                 detection_enabled=True):
        self.port = port
        self.detection_enabled = detection_enabled
        self.running = False
        
        # Initialiser la caméra
        self.camera = CameraStreamRPiCAM(width=640, height=480, fps=15)
        time.sleep(1)
        
        # Initialiser le détecteur d'obstacles
        self.detector = ObstacleDetector(
            min_obstacle_area=min_obstacle_area,
            color_diff_threshold=color_threshold,
            enabled=detection_enabled
        )
        
        # Initialiser le serveur HTTP
        self.server = HTTPServer(('0.0.0.0', port), MJPEGStreamHandler)
        
        logger.info(f"Serveur MJPEG lancé sur port {port}")
        logger.info(f"Détection d'obstacles: {'activée' if detection_enabled else 'désactivée'}")
    
    def process_frames(self):
        """Boucle principale de traitement des frames"""
        logger.info("Démarrage de la boucle de traitement...")
        self.running = True
        
        frame_count = 0
        start_time = time.time()
        last_fps_update = start_time
        
        try:
            while self.running:
                frame = self.camera.get_frame()
                
                if frame is not None:
                    # Détection d'obstacles
                    frame, obstacles, (danger_level, danger_color) = self.detector.detect(frame)
                    
                    # Calculer FPS
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Overlay d'information
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (5, 5), (200, 75), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.4, frame, 0.6, 0, frame)
                    
                    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 25), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, timestamp, (10, 45),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
                    cv2.putText(frame, f"Obstacles: {len(obstacles)}", (10, 65),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                    
                    # Mettre à jour le frame partagé
                    with MJPEGStreamHandler.shared_lock:
                        MJPEGStreamHandler.shared_frame = frame
                        MJPEGStreamHandler.shared_stats = {
                            'fps': fps,
                            'timestamp': timestamp,
                            'obstacles': len(obstacles),
                            'danger': danger_level
                        }
                    
                    frame_count += 1
                    
                    # Log des stats
                    if time.time() - last_fps_update > 5:
                        logger.info(f"FPS: {fps:.1f} | Obstacles: {len(obstacles)} | État: {danger_level}")
                        last_fps_update = time.time()
                else:
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Arrêt demandé...")
        except Exception as e:
            logger.error(f"Erreur: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.stop()
    
    def run(self):
        """Lance le streaming"""
        process_thread = threading.Thread(target=self.process_frames, daemon=True)
        process_thread.start()
        
        try:
            logger.info(f"✓ Serveur écoutant sur http://0.0.0.0:{self.port}")
            logger.info(f"  Accès local: http://localhost:{self.port}")
            logger.info(f"  Via SSH: ssh -L {self.port}:localhost:{self.port} user@[IP_RPI]")
            logger.info("")
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Arrêt du serveur...")
        finally:
            self.stop()
    
    def stop(self):
        """Arrête tout"""
        self.running = False
        if self.camera:
            self.camera.stop()
        if self.server:
            self.server.shutdown()


def signal_handler(sig, frame):
    """Gère Ctrl+C"""
    logger.info("Signal reçu, arrêt...")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Hexapode - Détection d\'Obstacles MJPEG Stream')
    parser.add_argument('--port', type=int, default=8080, 
                       help='Port HTTP (défaut: 8080)')
    parser.add_argument('--min-area', type=int, default=500,
                       help='Surface minimum pour détecter un obstacle en pixels² (défaut: 500)')
    parser.add_argument('--color-threshold', type=int, default=40,
                       help='Seuil de différence de couleur (défaut: 40)')
    parser.add_argument('--no-detection', action='store_true', 
                       help='Désactiver la détection d\'obstacles')
    
    args = parser.parse_args()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 60)
    logger.info("Hexapode - Détection d'Obstacles Stream MJPEG")
    logger.info("=" * 60)
    
    streamer = HexapodeObstacleStreamer(
        port=args.port,
        min_obstacle_area=args.min_area,
        color_threshold=args.color_threshold,
        detection_enabled=not args.no_detection
    )
    
    streamer.run()


if __name__ == '__main__':
    main()
