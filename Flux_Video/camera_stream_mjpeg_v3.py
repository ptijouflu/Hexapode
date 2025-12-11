#!/usr/bin/env python3
"""
Script de Streaming Vidéo MJPEG avec Détection d'Objets - V3
Utilise rpicam-jpeg continu + détection YOLO locale
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
        self.process = None
        self.temp_dir = tempfile.mkdtemp()
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.frame_count = 0
        
        logger.info(f"Initialisation camera {width}x{height} @ {fps} FPS...")
        logger.info(f"Répertoire temp: {self.temp_dir}")
        self._start_camera_stream()
    
    def _start_camera_stream(self):
        """Lance rpicam-jpeg en mode continu vers des fichiers"""
        try:
            output_pattern = os.path.join(self.temp_dir, "frame_%03d.jpg")
            
            # Capture 10 images par seconde max avec timeout global pour ne pas bloquer
            cmd = [
                'rpicam-jpeg',
                '--width', str(self.width),
                '--height', str(self.height),
                '--timeout', '0',  # Infinite
                '--framerate', str(self.fps),
                '--quality', '80',
                '--output', output_pattern,
                '--nopreview'
            ]
            
            logger.info(f"Commande: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.running = True
            
            # Thread pour lire les frames au fur et à mesure
            read_thread = threading.Thread(target=self._read_jpeg_frames, daemon=True)
            read_thread.start()
            
            logger.info("✓ Camera stream lancé (rpicam-jpeg)")
            
        except Exception as e:
            logger.error(f"✗ Erreur démarrage camera: {e}")
            self.running = False
    
    def _read_jpeg_frames(self):
        """Lit les frames JPEG au fur et à mesure qu'elles sont générées"""
        try:
            frame_id = 0
            missing_count = 0
            
            while self.running:
                # Chercher le fichier de la frame actuelle
                frame_file = os.path.join(self.temp_dir, f"frame_{frame_id:03d}.jpg")
                
                if os.path.exists(frame_file):
                    try:
                        frame = cv2.imread(frame_file)
                        
                        if frame is not None:
                            with self.frame_lock:
                                self.current_frame = frame.copy()
                                self.frame_count += 1
                            
                            # Supprimer l'ancien fichier pour économiser l'espace
                            if frame_id > 0:
                                old_file = os.path.join(self.temp_dir, f"frame_{frame_id-1:03d}.jpg")
                                if os.path.exists(old_file):
                                    try:
                                        os.remove(old_file)
                                    except:
                                        pass
                            
                            frame_id += 1
                            missing_count = 0
                        
                    except Exception as e:
                        logger.debug(f"Erreur lecture frame {frame_id}: {e}")
                else:
                    missing_count += 1
                    if missing_count < 10:
                        time.sleep(0.05)  # Attendre que la frame soit générée
                    else:
                        time.sleep(0.1)
                        missing_count = 0
        
        except Exception as e:
            logger.error(f"Erreur lecture frames: {e}")
        finally:
            self.running = False
    
    def get_frame(self):
        """Récupère la frame actuelle"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def stop(self):
        """Arrête la capture"""
        self.running = False
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
            except:
                self.process.kill()
        
        # Nettoyer les fichiers temp
        try:
            import shutil
            shutil.rmtree(self.temp_dir)
        except:
            pass


class ObjectDetector:
    """Détection d'objets avec YOLO"""
    
    def __init__(self, model_size="nano", enabled=True):
        """
        Initialise le détecteur YOLO
        model_size: "nano", "small", "medium", "large"
        """
        self.model_size = model_size
        self.model = None
        self.enabled = enabled
        self.initialized = False
        
        if self.enabled:
            self.init_yolo()
    
    def init_yolo(self):
        """Initialise YOLO"""
        try:
            from ultralytics import YOLO
            
            models = {
                "nano": "yolov8n.pt",
                "small": "yolov8s.pt",
                "medium": "yolov8m.pt",
                "large": "yolov8l.pt"
            }
            
            model_name = models.get(self.model_size, "yolov8n.pt")
            logger.info(f"Chargement YOLO {self.model_size} ({model_name})...")
            
            self.model = YOLO(model_name)
            self.initialized = True
            logger.info(f"✓ YOLO {self.model_size} prêt")
            
        except Exception as e:
            logger.error(f"✗ Erreur YOLO: {e}")
            self.enabled = False
    
    def detect(self, frame):
        """Lance la détection sur une frame"""
        if not self.enabled or not self.initialized:
            return frame, []
        
        try:
            results = self.model(frame, verbose=False, conf=0.5)
            detections = []
            
            for result in results:
                if result.boxes:
                    for box in result.boxes:
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                        conf = box.conf[0].cpu().numpy()
                        cls = int(box.cls[0].cpu().numpy())
                        
                        detections.append({
                            'bbox': (int(x1), int(y1), int(x2), int(y2)),
                            'confidence': float(conf),
                            'class_id': cls,
                            'class_name': result.names[cls]
                        })
                        
                        # Dessiner la bbox
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                        label = f"{result.names[cls]} {conf:.2f}"
                        cv2.putText(frame, label, (int(x1), int(y1)-5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            return frame, detections
            
        except Exception as e:
            logger.error(f"Erreur détection: {e}")
            return frame, []


class MJPEGStreamHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour le stream MJPEG"""
    
    # Shared state
    shared_frame = None
    shared_lock = threading.Lock()
    shared_stats = {'fps': 0, 'timestamp': '', 'detections': 0}
    
    def do_GET(self):
        """Gère les requêtes GET"""
        
        if self.path == '/':
            self.send_index()
        elif self.path == '/stream':
            self.send_mjpeg_stream()
        else:
            self.send_error(404, "Not Found")
    
    def send_index(self):
        """Envoie la page HTML avec la vidéo"""
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Hexapode Camera Stream</title>
            <style>
                body { font-family: Arial; text-align: center; background: #222; color: #fff; margin: 20px; }
                h1 { color: #0f0; }
                #video { max-width: 90%; border: 2px solid #0f0; }
                .info { margin-top: 20px; font-size: 14px; }
                .code { background: #111; padding: 10px; border-radius: 5px; font-family: monospace; }
            </style>
        </head>
        <body>
            <h1>🤖 Hexapode - Camera Stream MJPEG</h1>
            <img id="video" src="/stream" />
            <div class="info">
                <h3>Accès SSH depuis PC:</h3>
                <div class="code">ssh -L 8080:localhost:8080 user@10.187.69.95</div>
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
                
                time.sleep(0.05)  # ~20 FPS max
        
        except Exception as e:
            logger.debug(f"Client déconnecté: {e}")
    
    def log_message(self, format, *args):
        """Supprime les logs HTTP verbeux"""
        return


class HexapodeCameraStreamer:
    """Orchestrateur principal"""
    
    def __init__(self, port=8080, model_size="nano", detection_enabled=True):
        self.port = port
        self.model_size = model_size
        self.detection_enabled = detection_enabled
        self.running = False
        
        # Initialiser la caméra
        self.camera = CameraStreamRPiCAM(width=640, height=480, fps=15)
        time.sleep(1)  # Attendre que le premier capture démarre
        
        # Initialiser le détecteur
        self.detector = ObjectDetector(model_size=model_size, enabled=detection_enabled)
        
        # Initialiser le serveur HTTP
        self.server = HTTPServer(('0.0.0.0', port), MJPEGStreamHandler)
        
        logger.info(f"Serveur MJPEG lancé sur port {port}")
        if detection_enabled:
            logger.info(f"Détection YOLO activée ({model_size})")
        else:
            logger.info("Détection YOLO désactivée")
    
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
                    # Détection
                    frame, detections = self.detector.detect(frame)
                    
                    # Ajouter les infos
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        fps = frame_count / elapsed
                    else:
                        fps = 0
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Fond semi-transparent pour les textes
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (5, 5), (300, 95), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                    
                    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(frame, timestamp, (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                    if len(detections) > 0:
                        cv2.putText(frame, f"Objets: {len(detections)}", (10, 90),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                    
                    # Mettre à jour le frame partagé
                    with MJPEGStreamHandler.shared_lock:
                        MJPEGStreamHandler.shared_frame = frame
                        MJPEGStreamHandler.shared_stats = {
                            'fps': fps,
                            'timestamp': timestamp,
                            'detections': len(detections)
                        }
                    
                    frame_count += 1
                    
                    # Log des stats toutes les 5 secondes
                    if time.time() - last_fps_update > 5:
                        logger.info(f"FPS: {fps:.1f} | Frames: {frame_count} | Détections: {len(detections)}")
                        last_fps_update = time.time()
                else:
                    logger.warning("Aucune frame disponible")
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
        # Thread de traitement des frames
        process_thread = threading.Thread(target=self.process_frames, daemon=True)
        process_thread.start()
        
        # Serveur HTTP (bloquant)
        try:
            logger.info(f"✓ Serveur écoutant sur http://0.0.0.0:{self.port}")
            logger.info(f"  Accès local: http://localhost:{self.port}")
            logger.info(f"  Via SSH: ssh -L {self.port}:localhost:{self.port} user@10.187.69.95")
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
    parser = argparse.ArgumentParser(description='Hexapode Camera MJPEG Stream')
    parser.add_argument('--port', type=int, default=8080, help='Port HTTP (défaut: 8080)')
    parser.add_argument('--model', choices=['nano', 'small', 'medium', 'large'], 
                       default='nano', help='Modèle YOLO (défaut: nano)')
    parser.add_argument('--no-detection', action='store_true', 
                       help='Désactiver la détection YOLO')
    
    args = parser.parse_args()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 60)
    logger.info("Hexapode Camera Stream MJPEG V3 (rpicam-jpeg)")
    logger.info("=" * 60)
    
    streamer = HexapodeCameraStreamer(
        port=args.port,
        model_size=args.model,
        detection_enabled=not args.no_detection
    )
    
    streamer.run()


if __name__ == '__main__':
    main()
