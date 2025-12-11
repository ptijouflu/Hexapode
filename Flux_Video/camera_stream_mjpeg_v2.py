#!/usr/bin/env python3
"""
Script de Streaming Vidéo MJPEG avec Détection d'Objets - V2
Utilise rpicam-vid avec pipe pour un streaming continu + YOLO detection
Accessible en SSH: ssh -L 8080:localhost:8080 user@rpi_ip
"""

import os
import cv2
import numpy as np
import threading
import time
import logging
import subprocess
from io import BytesIO
from http.server import HTTPServer, BaseHTTPRequestHandler
import argparse
from datetime import datetime

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CameraStreamViaPipe:
    """Capture vidéo via rpicam-vid avec pipe H264"""
    
    def __init__(self, width=640, height=480, fps=30):
        self.width = width
        self.height = height
        self.fps = fps
        self.process = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        
        logger.info(f"Initialisation camera {width}x{height} @ {fps} FPS...")
        self._start_camera_stream()
    
    def _start_camera_stream(self):
        """Lance rpicam-vid en pipe vers ffmpeg pour extraire les frames H264"""
        try:
            # rpicam-vid output raw h264 to stdout, we'll use ffmpeg to decode
            cmd = [
                'rpicam-vid',
                '--width', str(self.width),
                '--height', str(self.height),
                '--framerate', str(self.fps),
                '--codec', 'h264',
                '--bitrate', '2000000',  # 2 Mbps
                '--timeout', '0',  # Infinite
                '-o', '-'  # Output to stdout
            ]
            
            logger.info(f"Commande: {' '.join(cmd)}")
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10*1024  # 10KB buffer
            )
            
            self.running = True
            
            # Thread pour lire et décoder les frames
            read_thread = threading.Thread(target=self._read_h264_stream, daemon=True)
            read_thread.start()
            
            logger.info("✓ Camera stream lancé")
            
        except Exception as e:
            logger.error(f"✗ Erreur démarrage camera: {e}")
            self.running = False
    
    def _read_h264_stream(self):
        """Lit et décode le stream H264 depuis rpicam-vid"""
        try:
            # Approche alternative: utiliser ffmpeg pour décoder
            ffmpeg_cmd = [
                'ffmpeg',
                '-i', 'pipe:0',  # Input from stdin
                '-f', 'image2pipe',  # Output format: image2pipe
                '-pix_fmt', 'bgr24',  # OpenCV uses BGR
                '-vcodec', 'rawvideo',  # Raw video output
                '-'  # Output to stdout
            ]
            
            ffmpeg_process = subprocess.Popen(
                ffmpeg_cmd,
                stdin=self.process.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=10*1024
            )
            
            frame_size = self.width * self.height * 3  # BGR format
            
            while self.running:
                try:
                    raw_frame = ffmpeg_process.stdout.read(frame_size)
                    
                    if len(raw_frame) != frame_size:
                        logger.warning("Frame size mismatch, trying to resync...")
                        continue
                    
                    frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((self.height, self.width, 3))
                    
                    with self.frame_lock:
                        self.current_frame = frame.copy()
                        
                except Exception as e:
                    logger.error(f"Erreur lecture frame: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Erreur stream ffmpeg: {e}")
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
            self.process.wait(timeout=2)


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
                body { font-family: Arial; text-align: center; background: #222; color: #fff; }
                h1 { color: #0f0; }
                img { max-width: 90%; border: 2px solid #0f0; }
                .info { margin-top: 20px; font-size: 14px; }
            </style>
        </head>
        <body>
            <h1>🤖 Hexapode - Camera Stream MJPEG</h1>
            <img src="/stream" style="width: 640px; height: 480px;" />
            <div class="info">
                <p>SSH Port Forward: <code>ssh -L 8080:localhost:8080 user@10.187.69.95</code></p>
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
                
                time.sleep(0.03)  # ~30 FPS
        
        except Exception as e:
            logger.error(f"Erreur stream: {e}")
    
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
        self.camera = CameraStreamViaPipe(width=640, height=480, fps=30)
        time.sleep(1)  # Attendre que le stream démarre
        
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
        
        try:
            while self.running:
                frame = self.camera.get_frame()
                
                if frame is not None:
                    # Détection
                    frame, detections = self.detector.detect(frame)
                    
                    # Ajouter les infos
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, timestamp, (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    if len(detections) > 0:
                        cv2.putText(frame, f"Objets: {len(detections)}", (10, 90),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Mettre à jour le frame partagé
                    with MJPEGStreamHandler.shared_lock:
                        MJPEGStreamHandler.shared_frame = frame
                        MJPEGStreamHandler.shared_stats = {
                            'fps': fps,
                            'timestamp': timestamp,
                            'detections': len(detections)
                        }
                    
                    frame_count += 1
                else:
                    logger.warning("Aucune frame disponible")
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Arrêt demandé...")
        except Exception as e:
            logger.error(f"Erreur: {e}")
        finally:
            self.stop()
    
    def run(self):
        """Lance le streaming"""
        # Thread de traitement des frames
        process_thread = threading.Thread(target=self.process_frames, daemon=True)
        process_thread.start()
        
        # Serveur HTTP (bloquant)
        try:
            logger.info(f"Serveur écoutant sur http://0.0.0.0:{self.port}")
            logger.info(f"Accès local: http://localhost:{self.port}")
            logger.info(f"Via SSH: ssh -L {self.port}:localhost:{self.port} user@10.187.69.95")
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


def main():
    parser = argparse.ArgumentParser(description='Hexapode Camera MJPEG Stream')
    parser.add_argument('--port', type=int, default=8080, help='Port HTTP (défaut: 8080)')
    parser.add_argument('--model', choices=['nano', 'small', 'medium', 'large'], 
                       default='nano', help='Modèle YOLO (défaut: nano)')
    parser.add_argument('--no-detection', action='store_true', 
                       help='Désactiver la détection YOLO')
    
    args = parser.parse_args()
    
    logger.info("=" * 50)
    logger.info("Hexapode Camera Stream MJPEG V2")
    logger.info("=" * 50)
    
    streamer = HexapodeCameraStreamer(
        port=args.port,
        model_size=args.model,
        detection_enabled=not args.no_detection
    )
    
    streamer.run()


if __name__ == '__main__':
    main()
