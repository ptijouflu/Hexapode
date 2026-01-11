    #!/usr/bin/env python3
"""
Détection d'Obstacles Optimisée pour Hexapode - Version FAST WIDE
Format large (640x240) pour meilleure vision latérale
Objectif: 5+ détections/seconde sur Raspberry Pi
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
from socketserver import ThreadingMixIn
import argparse
from datetime import datetime
import tempfile
import signal
import sys
from collections import deque

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FastCameraCapture:
    """
    Capture vidéo ultra-optimisée avec libcamera-vid + pipe
    Plus rapide que rpicam-jpeg en boucle
    Format large pour meilleure vision latérale
    """
    
    def __init__(self, width=640, height=240, fps=10):
        self.width = width
        self.height = height
        self.fps = fps
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.frame_count = 0
        self.process = None
        self.capture_thread = None
        self.last_frame_time = 0
        
        logger.info(f"Initialisation camera {width}x{height} @ {fps} FPS...")
        self._start_capture()
    
    def _start_capture(self):
        """Lance la capture via libcamera-vid avec pipe MJPEG"""
        try:
            self.running = True
            
            # Méthode 1: libcamera-vid en MJPEG vers stdout (plus rapide)
            cmd = [
                'libcamera-vid',
                '--width', str(self.width),
                '--height', str(self.height),
                '--framerate', str(self.fps),
                '--timeout', '0',  # Infini
                '--codec', 'mjpeg',
                '--quality', '60',
                '--nopreview',
                '-o', '-'  # Sortie stdout
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=10**6
            )
            
            self.capture_thread = threading.Thread(target=self._read_mjpeg_stream, daemon=True)
            self.capture_thread.start()
            
            logger.info("✓ Camera stream lancé (libcamera-vid MJPEG pipe)")
            
        except Exception as e:
            logger.warning(f"libcamera-vid échoué: {e}, fallback sur rpicam-jpeg")
            self._start_capture_fallback()
    
    def _start_capture_fallback(self):
        """Fallback: utilise rpicam-jpeg en boucle"""
        self.temp_dir = tempfile.mkdtemp()
        self.capture_thread = threading.Thread(target=self._capture_jpeg_loop, daemon=True)
        self.capture_thread.start()
        logger.info("✓ Camera stream lancé (rpicam-jpeg fallback)")
    
    def _read_mjpeg_stream(self):
        """Lit le flux MJPEG depuis le pipe"""
        buffer = b''
        jpeg_start = b'\xff\xd8'
        jpeg_end = b'\xff\xd9'
        
        try:
            while self.running and self.process:
                chunk = self.process.stdout.read(4096)
                if not chunk:
                    break
                
                buffer += chunk
                
                # Chercher une frame JPEG complète
                start_idx = buffer.find(jpeg_start)
                if start_idx != -1:
                    end_idx = buffer.find(jpeg_end, start_idx)
                    if end_idx != -1:
                        jpeg_data = buffer[start_idx:end_idx + 2]
                        buffer = buffer[end_idx + 2:]
                        
                        # Décoder JPEG
                        frame = cv2.imdecode(
                            np.frombuffer(jpeg_data, dtype=np.uint8),
                            cv2.IMREAD_COLOR
                        )
                        
                        if frame is not None:
                            with self.frame_lock:
                                self.current_frame = frame
                                self.frame_count += 1
                                self.last_frame_time = time.time()
                            
                            if self.frame_count == 1:
                                logger.info(f"✓ Première frame ({frame.shape})")
                
                # Limiter la taille du buffer
                if len(buffer) > 500000:
                    buffer = buffer[-100000:]
                    
        except Exception as e:
            logger.error(f"Erreur lecture stream: {e}")
        finally:
            self.running = False
    
    def _capture_jpeg_loop(self):
        """Fallback: capture JPEG en boucle (plus lent)"""
        frame_delay = 1.0 / self.fps
        frame_file = os.path.join(self.temp_dir, "frame.jpg")
        
        while self.running:
            start = time.time()
            
            try:
                result = subprocess.run(
                    ['rpicam-jpeg', '--width', str(self.width), '--height', str(self.height),
                     '--timeout', '500', '--quality', '60', '--output', frame_file, '--nopreview'],
                    capture_output=True, timeout=2
                )
                
                if os.path.exists(frame_file):
                    frame = cv2.imread(frame_file)
                    if frame is not None:
                        with self.frame_lock:
                            self.current_frame = frame
                            self.frame_count += 1
                            self.last_frame_time = time.time()
                        
                        if self.frame_count == 1:
                            logger.info(f"✓ Première frame ({frame.shape})")
                            
            except Exception as e:
                pass
            
            elapsed = time.time() - start
            if elapsed < frame_delay:
                time.sleep(frame_delay - elapsed)
    
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
        
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


class FastObstacleDetector:
    """
    Détection d'obstacles ultra-optimisée
    Algorithmes simplifiés pour max performance
    Format large pour meilleure vision latérale
    """
    
    def __init__(self, 
                 min_area=400,  # Augmenté car image plus large
                 process_scale=1.0,
                 roi_top=0.30,  # Zone plus haute pour voir plus loin
                 roi_bottom=0.95,  # Zone plus basse
                 edge_thresh=50,  # Seuil ajusté
                 enabled=True):
        
        self.min_area = min_area
        self.process_scale = process_scale
        self.roi_top = roi_top
        self.roi_bottom = roi_bottom
        self.edge_thresh = edge_thresh
        self.enabled = enabled
        
        # Cache pour éviter recalculs
        self._kernel_small = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        self._kernel_medium = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        
        # Stats
        self.detection_times = deque(maxlen=30)
        self.avg_detection_time = 0
        
        logger.info(f"✓ Détecteur obstacles FAST initialisé (min_area={min_area})")
    
    def detect(self, frame):
        """
        Détection optimisée - objectif < 200ms
        """
        if not self.enabled:
            return frame, [], "OFF", (128, 128, 128)
        
        start_time = time.time()
        
        h, w = frame.shape[:2]
        
        # Extraire ROI (zone sol)
        y1 = int(h * self.roi_top)
        y2 = int(h * self.roi_bottom)
        roi = frame[y1:y2, :]
        
        # Convertir en niveaux de gris (plus rapide)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        
        # Méthode combinée rapide:
        # 1. Flou léger
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # 2. Seuillage adaptatif (détecte objets plus sombres/clairs que le sol)
        thresh = cv2.adaptiveThreshold(
            blurred, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            21, 5
        )
        
        # 3. Détection de contours Canny (rapide)
        edges = cv2.Canny(blurred, self.edge_thresh, self.edge_thresh * 2)
        
        # 4. Combiner
        combined = cv2.bitwise_or(thresh, edges)
        
        # 5. Morphologie minimale
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, self._kernel_small)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, self._kernel_small)
        
        # Trouver contours
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        obstacles = []
        third_w = w // 3
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue
            
            x, y, bw, bh = cv2.boundingRect(cnt)
            y_global = y + y1
            cx = x + bw // 2
            
            # Classification rapide
            if cx < third_w:
                pos = "G"  # Gauche
            elif cx > 2 * third_w:
                pos = "D"  # Droite
            else:
                pos = "C"  # Centre
            
            # Distance (plus bas = plus proche)
            dist = (y_global - y1) / (y2 - y1)
            
            # Taille (seuils ajustés pour image large)
            size = "S" if area < 1500 else ("M" if area < 6000 else "L")
            
            obstacles.append({
                'bbox': (x, y_global, bw, bh),
                'area': area,
                'pos': pos,
                'dist': dist,
                'size': size
            })
        
        # Trier par proximité
        obstacles.sort(key=lambda o: o['dist'], reverse=True)
        
        # Niveau de danger
        danger, color = self._calc_danger(obstacles)
        
        # Dessiner (optimisé)
        self._draw_fast(frame, obstacles, y1, y2, danger, color)
        
        # Stats temps
        det_time = time.time() - start_time
        self.detection_times.append(det_time)
        self.avg_detection_time = sum(self.detection_times) / len(self.detection_times)
        
        return frame, obstacles, danger, color
    
    def _calc_danger(self, obstacles):
        """Calcul rapide du niveau de danger"""
        if not obstacles:
            return "OK", (0, 255, 0)
        
        for o in obstacles:
            if o['dist'] > 0.65 and o['pos'] == "C":
                return "STOP", (0, 0, 255)
            if o['dist'] > 0.5 and o['size'] in ["M", "L"]:
                return "WARN", (0, 140, 255)
        
        return "OBS", (0, 220, 220)
    
    def _draw_fast(self, frame, obstacles, y1, y2, danger, color):
        """Dessin optimisé pour format large"""
        h, w = frame.shape[:2]
        
        # Zone ROI (ligne fine)
        cv2.rectangle(frame, (0, y1), (w-1, y2), (60, 60, 60), 1)
        
        # Lignes de séparation des zones G/C/D
        third_w = w // 3
        cv2.line(frame, (third_w, y1), (third_w, y2), (40, 40, 40), 1)
        cv2.line(frame, (2*third_w, y1), (2*third_w, y2), (40, 40, 40), 1)
        
        # Labels zones
        cv2.putText(frame, "G", (third_w//2 - 5, y1 + 12), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (80, 80, 80), 1)
        cv2.putText(frame, "C", (w//2 - 5, y1 + 12), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (80, 80, 80), 1)
        cv2.putText(frame, "D", (2*third_w + third_w//2 - 5, y1 + 12), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.3, (80, 80, 80), 1)
        
        # Obstacles
        for o in obstacles:
            x, y, bw, bh = o['bbox']
            cv2.rectangle(frame, (x, y), (x+bw, y+bh), color, 2)
            
            # Label compact
            label = f"{o['size']}{o['pos']}"
            cv2.putText(frame, label, (x, y-3), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Indicateur danger (coin supérieur droit)
        cv2.rectangle(frame, (w-60, 5), (w-5, 28), color, -1)
        cv2.putText(frame, danger, (w-55, 22), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Serveur HTTP multi-thread pour meilleure réactivité"""
    daemon_threads = True


class FastStreamHandler(BaseHTTPRequestHandler):
    """Handler HTTP optimisé"""
    
    shared_frame = None
    shared_lock = threading.Lock()
    shared_stats = {'fps': 0, 'det_fps': 0, 'obstacles': 0, 'danger': 'INIT', 'det_ms': 0}
    
    protocol_version = 'HTTP/1.1'
    
    def do_GET(self):
        if self.path == '/':
            self._send_html()
        elif self.path == '/stream':
            self._send_stream()
        elif self.path == '/status':
            self._send_status()
        else:
            self.send_error(404)
    
    def _send_html(self):
        html = """<!DOCTYPE html>
<html><head>
<title>Hexapode Obstacles</title>
<meta charset="utf-8">
<style>
body{font-family:Arial;background:#111;color:#eee;text-align:center;margin:10px}
h1{color:#0f8;margin:10px 0}
#v{max-width:95%;border:2px solid #0f8;border-radius:8px}
#s{margin:10px;padding:8px;border-radius:5px;font-size:16px;font-weight:bold}
.info{font-size:12px;color:#888;margin-top:10px}
.leg{display:inline-block;background:#222;padding:10px;border-radius:5px;margin:10px;text-align:left}
.leg span{display:inline-block;width:12px;height:12px;margin-right:5px;border-radius:2px}
</style>
<script>
function u(){fetch('/status').then(r=>r.json()).then(d=>{
let s=document.getElementById('s');
s.innerHTML='État: '+d.danger+' | Obs: '+d.obstacles+' | Det: '+d.det_fps.toFixed(1)+'/s | '+d.det_ms+'ms';
s.style.background=d.danger=='STOP'?'#f00':d.danger=='WARN'?'#f80':d.danger=='OBS'?'#ff0':'#0f0';
s.style.color=d.danger=='OBS'||d.danger=='OK'?'#000':'#fff';
}).catch(e=>{});}
setInterval(u,300);
</script>
</head><body>
<h1>🤖 Hexapode - Vision Large</h1>
<img id="v" src="/stream">
<div id="s">Chargement...</div>
<div class="leg">
<span style="background:#0f0"></span>OK - Libre
<span style="background:#ff0;margin-left:15px"></span>OBS - Obstacle
<span style="background:#f80;margin-left:15px"></span>WARN - Attention
<span style="background:#f00;margin-left:15px"></span>STOP - Danger
</div>
<div class="info">SSH: ssh -L 8080:localhost:8080 user@[IP] puis http://localhost:8080</div>
</body></html>"""
        
        data = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)
    
    def _send_status(self):
        import json
        with self.shared_lock:
            data = json.dumps(self.shared_stats).encode()
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(data))
        self.end_headers()
        self.wfile.write(data)
    
    def _send_stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=F')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        
        try:
            while True:
                with self.shared_lock:
                    frame = self.shared_frame
                
                if frame is not None:
                    _, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    self.wfile.write(b'--F\r\nContent-Type:image/jpeg\r\n\r\n')
                    self.wfile.write(buf)
                    self.wfile.write(b'\r\n')
                
                time.sleep(0.05)  # ~20 FPS max affichage
        except:
            pass
    
    def log_message(self, *args):
        pass


class HexapodeObstacleFast:
    """Orchestrateur principal optimisé - Format large"""
    
    def __init__(self, port=8080, min_area=400, width=640, height=240, 
                 camera_fps=10, detection_enabled=True):
        self.port = port
        self.running = False
        
        # Camera basse résolution pour vitesse
        self.camera = FastCameraCapture(width=width, height=height, fps=camera_fps)
        time.sleep(0.5)
        
        # Détecteur optimisé
        self.detector = FastObstacleDetector(min_area=min_area, enabled=detection_enabled)
        
        # Serveur HTTP multi-thread
        self.server = ThreadedHTTPServer(('0.0.0.0', port), FastStreamHandler)
        
        # Stats
        self.detection_count = 0
        self.detection_start_time = None
        
        logger.info(f"✓ Serveur sur port {port}")
    
    def _process_loop(self):
        """Boucle de traitement optimisée"""
        self.running = True
        self.detection_start_time = time.time()
        last_log = time.time()
        
        while self.running:
            frame = self.camera.get_frame()
            
            if frame is None:
                time.sleep(0.02)
                continue
            
            # Détection
            frame, obstacles, danger, color = self.detector.detect(frame)
            self.detection_count += 1
            
            # Calcul FPS détection
            elapsed = time.time() - self.detection_start_time
            det_fps = self.detection_count / elapsed if elapsed > 0 else 0
            det_ms = int(self.detector.avg_detection_time * 1000)
            
            # Overlay FPS
            ts = datetime.now().strftime("%H:%M:%S")
            info = f"{det_fps:.1f}d/s | {det_ms}ms | {ts}"
            cv2.putText(frame, info, (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            
            # Update shared state
            with FastStreamHandler.shared_lock:
                FastStreamHandler.shared_frame = frame
                FastStreamHandler.shared_stats = {
                    'fps': det_fps,
                    'det_fps': det_fps,
                    'obstacles': len(obstacles),
                    'danger': danger,
                    'det_ms': det_ms
                }
            
            # Log terminal toutes les secondes
            if time.time() - last_log >= 1.0:
                obs_info = ""
                if obstacles:
                    obs_info = " | " + ", ".join([f"{o['size']}{o['pos']}@{o['dist']:.1f}" for o in obstacles[:3]])
                logger.info(f"[{danger:4}] {det_fps:.1f} det/s | {det_ms:3}ms | {len(obstacles)} obs{obs_info}")
                last_log = time.time()
    
    def run(self):
        """Lance le système"""
        # Thread de traitement
        proc_thread = threading.Thread(target=self._process_loop, daemon=True)
        proc_thread.start()
        
        logger.info("=" * 50)
        logger.info(f"✓ Serveur: http://0.0.0.0:{self.port}")
        logger.info(f"✓ SSH: ssh -L {self.port}:localhost:{self.port} user@[IP]")
        logger.info("=" * 50)
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            logger.info("Arrêt...")
        finally:
            self.stop()
    
    def stop(self):
        self.running = False
        self.camera.stop()
        self.server.shutdown()


def main():
    parser = argparse.ArgumentParser(description='Hexapode Obstacle Detection FAST - Format Large')
    parser.add_argument('--port', type=int, default=8080, help='Port HTTP (8080)')
    parser.add_argument('--min-area', type=int, default=400, help='Surface min obstacle (400)')
    parser.add_argument('--width', type=int, default=640, help='Largeur image (640 - format large)')
    parser.add_argument('--height', type=int, default=240, help='Hauteur image (240)')
    parser.add_argument('--fps', type=int, default=10, help='FPS camera (10)')
    parser.add_argument('--no-detect', action='store_true', help='Désactiver détection')
    
    args = parser.parse_args()
    
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    
    logger.info("=" * 50)
    logger.info("HEXAPODE - Détection Obstacles FAST WIDE")
    logger.info(f"Résolution: {args.width}x{args.height} (format large) @ {args.fps} FPS")
    logger.info("=" * 50)
    
    streamer = HexapodeObstacleFast(
        port=args.port,
        min_area=args.min_area,
        width=args.width,
        height=args.height,
        camera_fps=args.fps,
        detection_enabled=not args.no_detect
    )
    
    streamer.run()


if __name__ == '__main__':
    main()
