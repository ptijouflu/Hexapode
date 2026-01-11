#!/usr/bin/env python3
"""
Script de Streaming Vidéo UDP avec Détection d'Objets
Utilise rpicam-jpeg continu + détection YOLO locale
Envoie le flux via UDP vers un client distant

Usage:
  Sur le Raspberry Pi (émetteur):
    python3 camera_stream_udp.py --host 192.168.1.100 --port 5000
  
  Sur le PC (récepteur):
    python3 camera_stream_udp.py --receive --port 5000
"""

import os
import cv2
import numpy as np
import threading
import time
import logging
import subprocess
import socket
import struct
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

# Taille maximale d'un paquet UDP (65507 bytes max, on utilise moins pour la fiabilité)
MAX_DGRAM_SIZE = 65000
CHUNK_SIZE = 60000  # Taille des chunks pour fragmenter les images


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
                frame_file = os.path.join(self.temp_dir, "current_frame.jpg")
                
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
                        
                        cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
                        label = f"{result.names[cls]} {conf:.2f}"
                        cv2.putText(frame, label, (int(x1), int(y1)-5), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            
            return frame, detections
            
        except Exception as e:
            logger.error(f"Erreur détection: {e}")
            return frame, []


class UDPVideoSender:
    """Émetteur de flux vidéo UDP"""
    
    def __init__(self, host, port, quality=80):
        self.host = host
        self.port = port
        self.quality = quality
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.running = False
        self.frame_id = 0
        
        logger.info(f"✓ Émetteur UDP configuré vers {host}:{port}")
    
    def send_frame(self, frame):
        """Envoie une frame via UDP (fragmentée si nécessaire)"""
        try:
            # Encoder l'image en JPEG
            ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
            if not ret:
                return False
            
            data = buffer.tobytes()
            data_size = len(data)
            
            # Calculer le nombre de chunks nécessaires
            num_chunks = (data_size + CHUNK_SIZE - 1) // CHUNK_SIZE
            
            self.frame_id += 1
            
            # Envoyer chaque chunk avec un header
            for i in range(num_chunks):
                start = i * CHUNK_SIZE
                end = min(start + CHUNK_SIZE, data_size)
                chunk = data[start:end]
                
                # Header: frame_id (4 bytes) + chunk_id (2 bytes) + num_chunks (2 bytes) + data_size (4 bytes)
                header = struct.pack('!IHHI', self.frame_id, i, num_chunks, data_size)
                packet = header + chunk
                
                self.socket.sendto(packet, (self.host, self.port))
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi UDP: {e}")
            return False
    
    def close(self):
        """Ferme le socket"""
        self.socket.close()


class UDPVideoReceiver:
    """Récepteur de flux vidéo UDP"""
    
    def __init__(self, port, buffer_size=10):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(('0.0.0.0', port))
        self.socket.settimeout(1.0)
        
        self.running = False
        self.current_frame = None
        self.frame_lock = threading.Lock()
        
        # Buffer pour reconstituer les frames fragmentées
        self.frame_buffer = {}
        self.last_complete_frame_id = 0
        
        logger.info(f"✓ Récepteur UDP en écoute sur port {port}")
    
    def receive_loop(self):
        """Boucle de réception des paquets"""
        self.running = True
        
        while self.running:
            try:
                data, addr = self.socket.recvfrom(MAX_DGRAM_SIZE)
                
                if len(data) < 12:  # Header minimum
                    continue
                
                # Décoder le header
                header = data[:12]
                frame_id, chunk_id, num_chunks, data_size = struct.unpack('!IHHI', header)
                chunk_data = data[12:]
                
                # Initialiser le buffer pour cette frame si nécessaire
                if frame_id not in self.frame_buffer:
                    self.frame_buffer[frame_id] = {
                        'chunks': {},
                        'num_chunks': num_chunks,
                        'data_size': data_size,
                        'timestamp': time.time()
                    }
                
                # Stocker le chunk
                self.frame_buffer[frame_id]['chunks'][chunk_id] = chunk_data
                
                # Vérifier si la frame est complète
                if len(self.frame_buffer[frame_id]['chunks']) == num_chunks:
                    self._reconstruct_frame(frame_id)
                
                # Nettoyer les vieux buffers (plus de 2 secondes)
                self._cleanup_old_buffers()
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"Erreur réception: {e}")
    
    def _reconstruct_frame(self, frame_id):
        """Reconstitue une frame à partir des chunks"""
        try:
            buffer_info = self.frame_buffer[frame_id]
            
            # Assembler les chunks dans l'ordre
            data = b''
            for i in range(buffer_info['num_chunks']):
                if i in buffer_info['chunks']:
                    data += buffer_info['chunks'][i]
                else:
                    logger.warning(f"Chunk {i} manquant pour frame {frame_id}")
                    del self.frame_buffer[frame_id]
                    return
            
            # Décoder l'image
            nparr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                with self.frame_lock:
                    self.current_frame = frame
                    self.last_complete_frame_id = frame_id
            
            # Supprimer du buffer
            del self.frame_buffer[frame_id]
            
        except Exception as e:
            logger.error(f"Erreur reconstruction frame: {e}")
            if frame_id in self.frame_buffer:
                del self.frame_buffer[frame_id]
    
    def _cleanup_old_buffers(self):
        """Supprime les buffers trop vieux"""
        current_time = time.time()
        old_frames = [fid for fid, info in self.frame_buffer.items() 
                      if current_time - info['timestamp'] > 2.0]
        for fid in old_frames:
            del self.frame_buffer[fid]
    
    def get_frame(self):
        """Récupère la dernière frame reçue"""
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
            return None
    
    def close(self):
        """Ferme le socket"""
        self.running = False
        self.socket.close()


class HexapodeCameraUDPStreamer:
    """Émetteur principal de flux vidéo UDP"""
    
    def __init__(self, host, port, model_size="nano", detection_enabled=True, quality=80):
        self.host = host
        self.port = port
        self.model_size = model_size
        self.detection_enabled = detection_enabled
        self.quality = quality
        self.running = False
        
        # Initialiser la caméra
        self.camera = CameraStreamRPiCAM(width=640, height=480, fps=15)
        time.sleep(1)
        
        # Initialiser le détecteur
        self.detector = ObjectDetector(model_size=model_size, enabled=detection_enabled)
        
        # Initialiser l'émetteur UDP
        self.sender = UDPVideoSender(host, port, quality)
        
        logger.info(f"Émetteur UDP configuré vers {host}:{port}")
        if detection_enabled:
            logger.info(f"Détection YOLO activée ({model_size})")
        else:
            logger.info("Détection YOLO désactivée")
    
    def run(self):
        """Lance le streaming UDP"""
        logger.info("Démarrage du streaming UDP...")
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
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Overlay d'informations
                    overlay = frame.copy()
                    cv2.rectangle(overlay, (5, 5), (300, 95), (0, 0, 0), -1)
                    cv2.addWeighted(overlay, 0.3, frame, 0.7, 0, frame)
                    
                    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(frame, timestamp, (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                    cv2.putText(frame, f"UDP -> {self.host}:{self.port}", (10, 90),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)
                    
                    if len(detections) > 0:
                        cv2.putText(frame, f"Objets: {len(detections)}", (200, 30),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
                    
                    # Envoyer via UDP
                    self.sender.send_frame(frame)
                    frame_count += 1
                    
                    # Log des stats toutes les 5 secondes
                    if time.time() - last_fps_update > 5:
                        logger.info(f"FPS: {fps:.1f} | Frames envoyées: {frame_count}")
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
    
    def stop(self):
        """Arrête tout"""
        self.running = False
        if self.camera:
            self.camera.stop()
        if self.sender:
            self.sender.close()


class UDPVideoViewer:
    """Visualiseur de flux vidéo UDP (côté récepteur/PC)"""
    
    def __init__(self, port):
        self.port = port
        self.receiver = UDPVideoReceiver(port)
        self.running = False
    
    def run(self):
        """Lance la réception et l'affichage"""
        logger.info(f"Démarrage du récepteur UDP sur port {self.port}...")
        self.running = True
        
        # Thread de réception
        receive_thread = threading.Thread(target=self.receiver.receive_loop, daemon=True)
        receive_thread.start()
        
        frame_count = 0
        start_time = time.time()
        last_fps_update = start_time
        
        logger.info("En attente de flux vidéo... (Appuyez sur 'q' pour quitter)")
        
        try:
            while self.running:
                frame = self.receiver.get_frame()
                
                if frame is not None:
                    # Ajouter info de réception
                    elapsed = time.time() - start_time
                    fps = frame_count / elapsed if elapsed > 0 else 0
                    
                    cv2.putText(frame, f"RX FPS: {fps:.1f}", (frame.shape[1] - 150, 30), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
                    
                    cv2.imshow('Hexapode Camera - UDP Stream', frame)
                    frame_count += 1
                    
                    # Log des stats toutes les 5 secondes
                    if time.time() - last_fps_update > 5:
                        logger.info(f"RX FPS: {fps:.1f} | Frames reçues: {frame_count}")
                        last_fps_update = time.time()
                
                # Gérer les événements OpenCV
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            logger.info("Arrêt demandé...")
        except Exception as e:
            logger.error(f"Erreur: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """Arrête le récepteur"""
        self.running = False
        self.receiver.close()
        cv2.destroyAllWindows()


def signal_handler(sig, frame):
    """Gère Ctrl+C"""
    logger.info("Signal reçu, arrêt...")
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description='Hexapode Camera UDP Stream')
    
    # Mode réception
    parser.add_argument('--receive', action='store_true',
                       help='Mode réception (côté PC)')
    
    # Paramètres réseau
    parser.add_argument('--host', type=str, default='127.0.0.1',
                       help='Adresse IP du destinataire (défaut: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=5000,
                       help='Port UDP (défaut: 5000)')
    
    # Paramètres vidéo
    parser.add_argument('--quality', type=int, default=80,
                       help='Qualité JPEG 1-100 (défaut: 80)')
    
    # Paramètres YOLO
    parser.add_argument('--model', choices=['nano', 'small', 'medium', 'large'], 
                       default='nano', help='Modèle YOLO (défaut: nano)')
    parser.add_argument('--no-detection', action='store_true', 
                       help='Désactiver la détection YOLO')
    
    args = parser.parse_args()
    
    signal.signal(signal.SIGINT, signal_handler)
    
    logger.info("=" * 60)
    
    if args.receive:
        # Mode récepteur (PC)
        logger.info("Hexapode Camera - Récepteur UDP")
        logger.info("=" * 60)
        logger.info(f"En écoute sur le port {args.port}")
        
        viewer = UDPVideoViewer(port=args.port)
        viewer.run()
    else:
        # Mode émetteur (Raspberry Pi)
        logger.info("Hexapode Camera - Émetteur UDP")
        logger.info("=" * 60)
        logger.info(f"Envoi vers {args.host}:{args.port}")
        
        streamer = HexapodeCameraUDPStreamer(
            host=args.host,
            port=args.port,
            model_size=args.model,
            detection_enabled=not args.no_detection,
            quality=args.quality
        )
        streamer.run()


if __name__ == '__main__':
    main()
