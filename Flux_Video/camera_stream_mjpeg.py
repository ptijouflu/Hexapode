#!/usr/bin/env python3
"""
Script de Streaming Vidéo MJPEG avec Détection d'Objets
Capture vidéo Raspberry Pi → Détection YOLO → Stream MJPEG HTTP
Accessible en SSH avec port forwarding: ssh -L 8080:localhost:8080 user@rpi_ip
"""

import os
import cv2
import numpy as np
from pathlib import Path
from datetime import datetime
import threading
import time
import logging
from collections import deque

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CameraCapture:
    """Gère la capture vidéo depuis rpicam"""
    
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.frame_count = 0
        self.fps = 0
        self.start_time = time.time()
        
    def capture_frame_rpicam(self):
        """Capture une frame via rpicam en temps réel"""
        # On utilise une approche simple: capturer une photo et la lire
        # Pour un vrai streaming, on utiliserait rpicam-vid avec un pipe
        try:
            temp_file = "/tmp/frame_temp.jpg"
            cmd = f"rpicam-jpeg -o {temp_file} --timeout=100 --nopreview --width {self.width} --height {self.height} 2>/dev/null"
            
            exit_code = os.system(cmd)
            
            if exit_code == 0 and os.path.exists(temp_file):
                frame = cv2.imread(temp_file)
                os.remove(temp_file)
                
                if frame is not None:
                    self.frame_count += 1
                    return frame
            
            return None
            
        except Exception as e:
            logger.error(f"Erreur capture: {e}")
            return None
    
    def get_fps(self):
        """Calcule le FPS"""
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            self.fps = self.frame_count / elapsed
        return self.fps


class ObjectDetector:
    """Détection d'objets avec YOLO"""
    
    def __init__(self, model_size="nano"):
        """
        Initialise le détecteur YOLO
        model_size: "nano", "small", "medium", "large"
        """
        self.model_size = model_size
        self.model = None
        self.class_names = []
        self.initialized = False
        
        self.init_yolo()
    
    def init_yolo(self):
        """Initialise YOLO"""
        try:
            from ultralytics import YOLO
            
            # Modèles disponibles
            models = {
                "nano": "yolov8n.pt",
                "small": "yolov8s.pt",
                "medium": "yolov8m.pt",
                "large": "yolov8l.pt"
            }
            
            model_name = models.get(self.model_size, "yolov8n.pt")
            
            logger.info(f"Chargement YOLO {self.model_size}...")
            self.model = YOLO(model_name)
            self.initialized = True
            logger.info("✓ YOLO chargé avec succès")
            
        except ImportError:
            logger.warning("ultralytics non installé")
            logger.info("Installation: pip install ultralytics")
            self.initialized = False
        except Exception as e:
            logger.error(f"Erreur YOLO: {e}")
            self.initialized = False
    
    def detect(self, frame):
        """
        Détecte les objets dans une frame
        Retourne: frame annotée, liste des détections
        """
        if not self.initialized or self.model is None:
            return frame, []
        
        try:
            # Exécuter YOLO
            results = self.model(frame, conf=0.5, verbose=False)
            
            detections = []
            
            # Tracer les boîtes de détection
            for result in results:
                for box in result.boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    class_name = result.names[cls]
                    
                    # Ajouter à la liste
                    detections.append({
                        "class": class_name,
                        "confidence": conf,
                        "box": (x1, y1, x2, y2)
                    })
                    
                    # Dessiner le rectangle
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Ajouter le label
                    label = f"{class_name} {conf:.2f}"
                    cv2.putText(frame, label, (x1, y1 - 10),
                              cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            
            return frame, detections
            
        except Exception as e:
            logger.error(f"Erreur détection: {e}")
            return frame, []


class MJPEGServer:
    """Serveur MJPEG HTTP simple"""
    
    def __init__(self, port=8080, host="127.0.0.1"):
        """Initialise le serveur"""
        self.port = port
        self.host = host
        self.frame = None
        self.frame_lock = threading.Lock()
        self.server_running = False
        
    def set_frame(self, frame):
        """Met à jour la frame à streamer"""
        with self.frame_lock:
            self.frame = frame.copy() if frame is not None else None
    
    def get_frame_jpeg(self):
        """Retourne la frame en JPEG"""
        with self.frame_lock:
            if self.frame is None:
                return None
            ret, buffer = cv2.imencode('.jpg', self.frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if ret:
                return buffer.tobytes()
        return None
    
    def run(self):
        """Lance le serveur HTTP"""
        try:
            from http.server import HTTPServer, BaseHTTPRequestHandler
            
            server_ref = self
            
            class StreamHandler(BaseHTTPRequestHandler):
                def do_GET(self):
                    if self.path == '/stream':
                        self.stream_video()
                    elif self.path == '/':
                        self.send_index()
                    else:
                        self.send_error(404)
                
                def stream_video(self):
                    """Envoie le stream MJPEG"""
                    self.send_response(200)
                    self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
                    self.end_headers()
                    
                    try:
                        while server_ref.server_running:
                            jpeg_data = server_ref.get_frame_jpeg()
                            if jpeg_data:
                                self.wfile.write(b'--frame\r\n')
                                self.wfile.write(b'Content-Type: image/jpeg\r\n')
                                self.wfile.write(f'Content-Length: {len(jpeg_data)}\r\n\r\n'.encode())
                                self.wfile.write(jpeg_data)
                                self.wfile.write(b'\r\n')
                            time.sleep(0.05)
                    except Exception as e:
                        logger.debug(f"Stream error: {e}")
                
                def send_index(self):
                    """Page HTML d'index"""
                    html = """
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>Hexapode Camera Stream</title>
                        <style>
                            body { font-family: Arial; text-align: center; margin: 20px; }
                            img { max-width: 100%; height: auto; border: 2px solid #333; }
                            h1 { color: #333; }
                        </style>
                    </head>
                    <body>
                        <h1>📷 Hexapode - Caméra Stream</h1>
                        <img src="/stream" alt="Video Stream">
                    </body>
                    </html>
                    """
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(html.encode())
                
                def log_message(self, format, *args):
                    """Supprime les logs de requête verbose"""
                    pass
            
            # Créer et lancer le serveur
            server = HTTPServer((self.host, self.port), StreamHandler)
            self.server_running = True
            logger.info(f"Serveur MJPEG lancé sur http://{self.host}:{self.port}/stream")
            server.serve_forever()
            
        except Exception as e:
            logger.error(f"Erreur serveur HTTP: {e}")
            self.server_running = False


class HexapodeCameraStreamer:
    """Gestionnaire principal du streaming caméra"""
    
    def __init__(self, port=8080, detector_model="nano"):
        """Initialise le streameur"""
        self.camera = CameraCapture(width=640, height=480)
        self.detector = ObjectDetector(model_size=detector_model)
        self.server = MJPEGServer(port=port, host="127.0.0.1")
        self.running = False
        self.last_detection = None
        
    def add_info_overlay(self, frame, fps, detection_count):
        """Ajoute des infos sur l'image"""
        # FPS
        cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        # Timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        cv2.putText(frame, timestamp, (10, 65),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        # Nombre d'objets détectés
        cv2.putText(frame, f"Detections: {detection_count}", (10, 100),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
        
        return frame
    
    def capture_and_process(self):
        """Capture et traite les frames en continu"""
        logger.info("Démarrage du capture/traitement...")
        
        while self.running:
            try:
                # Capturer une frame
                frame = self.camera.capture_frame_rpicam()
                
                if frame is None:
                    logger.warning("Impossible de capturer une frame")
                    time.sleep(0.1)
                    continue
                
                # Détecter les objets
                frame_annotated, detections = self.detector.detect(frame)
                
                # Ajouter les infos
                fps = self.camera.get_fps()
                frame_with_info = self.add_info_overlay(frame_annotated, fps, len(detections))
                
                # Envoyer au serveur
                self.server.set_frame(frame_with_info)
                
                # Sauvegarder dernière détection
                self.last_detection = detections
                
                # Log périodique
                if self.camera.frame_count % 30 == 0:
                    logger.info(f"Frames: {self.camera.frame_count} | FPS: {fps:.1f} | Détections: {len(detections)}")
                
            except Exception as e:
                logger.error(f"Erreur traitement: {e}")
                time.sleep(0.1)
    
    def run(self):
        """Lance le streaming complet"""
        logger.info("="*70)
        logger.info("HEXAPODE - Camera Stream MJPEG avec Détection YOLO")
        logger.info("="*70)
        
        self.running = True
        
        # Lancer le serveur dans un thread
        server_thread = threading.Thread(target=self.server.run, daemon=True)
        server_thread.start()
        
        # Attendre que le serveur soit prêt
        time.sleep(1)
        
        # Lancer la capture/traitement dans le thread principal
        try:
            self.capture_and_process()
        except KeyboardInterrupt:
            logger.info("\nArrêt demandé par l'utilisateur")
        finally:
            self.stop()
    
    def stop(self):
        """Arrête le streaming"""
        logger.info("Arrêt du streaming...")
        self.running = False
        self.server.server_running = False
        logger.info(f"Stats finales: {self.camera.frame_count} frames, FPS moyen: {self.camera.get_fps():.1f}")


def main():
    """Fonction principale"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Hexapode Camera Stream MJPEG")
    parser.add_argument("--port", type=int, default=8080, help="Port HTTP (default: 8080)")
    parser.add_argument("--model", choices=["nano", "small", "medium", "large"], 
                       default="nano", help="Taille du modèle YOLO")
    parser.add_argument("--no-detection", action="store_true", help="Désactiver la détection")
    
    args = parser.parse_args()
    
    # Initialiser
    if args.no_detection:
        logger.info("Détection YOLO désactivée")
        detector_model = None
    else:
        detector_model = args.model
    
    streamer = HexapodeCameraStreamer(port=args.port, detector_model=detector_model)
    
    # Afficher les instructions
    logger.info("")
    logger.info("📡 STREAMING EN COURS")
    logger.info("")
    logger.info(f"   URL locale: http://localhost:{args.port}")
    logger.info(f"   Port: {args.port}")
    logger.info("")
    logger.info("🔗 ACCÈS EN SSH:")
    logger.info(f"   ssh -L {args.port}:localhost:{args.port} user@rpi_ip")
    logger.info(f"   Puis: http://localhost:{args.port} sur PC")
    logger.info("")
    logger.info("Appuyez sur Ctrl+C pour arrêter")
    logger.info("")
    
    # Lancer
    streamer.run()


if __name__ == "__main__":
    main()
