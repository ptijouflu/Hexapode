#!/usr/bin/env python3
"""
Script de Streaming Vidéo MJPEG avec Détection d'Objets - FINAL
Utilise capture bash + rpicam-jpeg + détection YOLO locale
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
import glob
import signal
import sys

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Répertoire de capture
CAPTURE_DIR = "/tmp/camera_stream"


class CameraStreamBashLoop:
    """Capture vidéo via script bash + rpicam-jpeg"""
    
    def __init__(self, width=640, height=480):
        self.width = width
        self.height = height
        self.process = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.frame_count = 0
        self.last_frame_file = None
        
        # Créer le répertoire de capture
        os.makedirs(CAPTURE_DIR, exist_ok=True)
        
        logger.info(f"Initialisation camera {width}x{height}...")
        self._start_camera_stream()
    
    def _start_camera_stream(self):
        """Lance la capture bash en background"""
        try:
            # Créer un script de capture simple
            script = f"""#!/bin/bash
OUTPUT_DIR="{CAPTURE_DIR}"
COUNTER=0
while true; do
    FILENAME=$(printf "$OUTPUT_DIR/frame_%05d.jpg" $COUNTER)
    rpicam-jpeg --width {self.width} --height {self.height} --quality 85 --timeout 100 --nopreview -o "$FILENAME" 2>/dev/null
    if [ -f "$FILENAME" ]; then
        COUNTER=$((COUNTER + 1))
        find "$OUTPUT_DIR" -name "frame_*.jpg" -type f | sort -r | tail -n +6 | xargs -r rm
    fi
done
"""
            
            # Écrire et exécuter le script
            script_file = "/tmp/capture_stream.sh"
            with open(script_file, 'w') as f:
                f.write(script)
            os.chmod(script_file, 0o755)
            
            self.process = subprocess.Popen(
                ['bash', script_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.running = True
            
            # Thread pour lire les frames au fur et à mesure
            read_thread = threading.Thread(target=self._read_jpeg_frames, daemon=True)
            read_thread.start()
            
            logger.info("✓ Camera stream lancé (bash loop + rpicam-jpeg)")
            
        except Exception as e:
            logger.error(f"✗ Erreur démarrage camera: {e}")
            self.running = False
    
    def _read_jpeg_frames(self):
        """Lit les frames JPEG au fur et à mesure qu'elles sont générées"""
        try:
            while self.running:
                # Chercher les fichiers JPEG
                frames = sorted(glob.glob(os.path.join(CAPTURE_DIR, "frame_*.jpg")))
                
                if frames:
                    # Prendre le dernier fichier
                    latest_frame = frames[-1]
                    
                    if latest_frame != self.last_frame_file:
                        try:
                            frame = cv2.imread(latest_frame)
                            
                            if frame is not None:
                                with self.frame_lock:
                                    self.current_frame = frame.copy()
                                    self.frame_count += 1
                                
                                self.last_frame_file = latest_frame
                        
                        except Exception as e:
                            logger.debug(f"Erreur lecture frame: {e}")
                
                time.sleep(0.05)
        
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


class ObjectDetector:
    """Détection d'objets avec YOLO"""
    
    def __init__(self, model_size="nano", enabled=True):
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
    
    shared_frame = None
    shared_lock = threading.Lock()
    
    def do_GET(self):
        if self.path == '/':
            self.send_index()
        elif self.path == '/stream':
            self.send_mjpeg_stream()
        else:
            self.send_error(404)
    
    def send_index(self):
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Hexapode Camera</title>
            <style>
                body { font-family: Arial; text-align: center; background: #222; color: #fff; margin: 20px; }
                h1 { color: #0f0; }
                img { max-width: 90%; border: 2px solid #0f0; margin: 20px 0; }
                .info { font-size: 14px; }
                code { background: #111; padding: 10px; display: block; margin: 10px 0; border-radius: 5px; font-family: monospace; }
            </style>
        </head>
        <body>
            <h1>🤖 Hexapode Camera Stream</h1>
            <img src="/stream" style="width: 640px; height: 480px;" />
            <div class="info">
                <h3>Access via SSH:</h3>
                <code>ssh -L 8080:localhost:8080 user@10.187.69.95</code>
                <p>Then open: <code>http://localhost:8080</code></p>
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
        
        except:
            pass
    
    def log_message(self, format, *args):
        return


class HexapodeCameraStreamer:
    """Orchestrateur principal"""
    
    def __init__(self, port=8080, model_size="nano", detection_enabled=True):
        self.port = port
        self.model_size = model_size
        self.detection_enabled = detection_enabled
        self.running = False
        
        self.camera = CameraStreamBashLoop(width=640, height=480)
        time.sleep(2)  # Attendre les premières captures
        
        self.detector = ObjectDetector(model_size=model_size, enabled=detection_enabled)
        
        self.server = HTTPServer(('0.0.0.0', port), MJPEGStreamHandler)
        
        logger.info(f"Serveur MJPEG sur port {port}")
        if detection_enabled:
            logger.info(f"Détection YOLO: {model_size}")
        else:
            logger.info("Détection YOLO: désactivée")
    
    def process_frames(self):
        """Boucle principale"""
        logger.info("Démarrage traitement...")
        self.running = True
        
        frame_count = 0
        start_time = time.time()
        
        try:
            while self.running:
                frame = self.camera.get_frame()
                
                if frame is not None:
                    frame, detections = self.detector.detect(frame)
                    
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    
                    # Overlay
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (5, 5), (300, 100), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                    
                    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(frame, f"Time: {timestamp}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                    if self.detection_enabled:
                        cv2.putText(frame, f"Objects: {len(detections)}", (10, 90),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                    
                    with MJPEGStreamHandler.shared_lock:
                        MJPEGStreamHandler.shared_frame = frame
                    
                    frame_count += 1
                    
                    if frame_count % 30 == 0:
                        logger.info(f"FPS: {fps:.1f} | Frames: {frame_count}")
                
                else:
                    time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Arrêt...")
        except Exception as e:
            logger.error(f"Erreur: {e}")
        finally:
            self.stop()
    
    def run(self):
        """Lance le serveur"""
        process_thread = threading.Thread(target=self.process_frames, daemon=True)
        process_thread.start()
        
        try:
            logger.info("")
            logger.info(f"✓ Serveur écoutant sur http://0.0.0.0:{self.port}")
            logger.info(f"  Local: http://localhost:{self.port}")
            logger.info(f"  SSH: ssh -L {self.port}:localhost:{self.port} user@10.187.69.95")
            logger.info("")
            self.server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self):
        """Arrête tout"""
        self.running = False
        if hasattr(self, 'camera'):
            self.camera.stop()
        if hasattr(self, 'server'):
            self.server.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Hexapode Camera MJPEG')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--model', choices=['nano', 'small', 'medium', 'large'], default='nano')
    parser.add_argument('--no-detection', action='store_true')
    
    args = parser.parse_args()
    
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    logger.info("=" * 60)
    logger.info("Hexapode Camera Stream MJPEG (Production)")
    logger.info("=" * 60)
    
    streamer = HexapodeCameraStreamer(
        port=args.port,
        model_size=args.model,
        detection_enabled=not args.no_detection
    )
    
    streamer.run()


if __name__ == '__main__':
    main()
