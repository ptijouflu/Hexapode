"""
Hexapode - Serveur HTTP pour le flux vidéo
"""

import io
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

import cv2

logger = logging.getLogger(__name__)


class StreamHandler(BaseHTTPRequestHandler):
    """Handler HTTP pour le streaming MJPEG"""
    
    camera = None  # Sera défini avant le démarrage du serveur
    detector = None  # Optionnel: pour afficher les détections
    
    def log_message(self, format, *args):
        """Désactive les logs HTTP standard"""
        pass
    
    def do_GET(self):
        """Gère les requêtes GET"""
        if self.path == '/':
            self._handle_stream()
        elif self.path == '/status':
            self._handle_status()
        else:
            self.send_error(404)
    
    def _handle_stream(self):
        """Envoie le flux MJPEG"""
        self.send_response(200)
        self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            while True:
                frame = StreamHandler.camera.get_frame() if StreamHandler.camera else None
                
                if frame is not None:
                    # Appliquer les détections si disponibles
                    if StreamHandler.detector:
                        obstacles, _, _ = StreamHandler.detector.detect(frame)
                        frame = StreamHandler.detector.draw(frame, obstacles)
                    
                    # Encoder en JPEG
                    _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    data = jpeg.tobytes()
                    
                    self.wfile.write(b'--frame\r\n')
                    self.wfile.write(b'Content-Type: image/jpeg\r\n')
                    self.wfile.write(f'Content-Length: {len(data)}\r\n\r\n'.encode())
                    self.wfile.write(data)
                    self.wfile.write(b'\r\n')
        except (BrokenPipeError, ConnectionResetError):
            pass
    
    def _handle_status(self):
        """Retourne le statut du serveur"""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'{"status": "running"}')


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Serveur HTTP multi-threadé"""
    daemon_threads = True


def start_stream_server(camera, detector=None, port=8080):
    """
    Démarre le serveur de streaming en arrière-plan.
    
    Args:
        camera: Instance de FastCamera
        detector: Instance de ObstacleDetector (optionnel)
        port: Port HTTP (défaut: 8080)
    
    Returns:
        Instance du serveur
    """
    import threading
    
    StreamHandler.camera = camera
    StreamHandler.detector = detector
    
    server = ThreadedHTTPServer(('0.0.0.0', port), StreamHandler)
    
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    
    logger.info(f"✓ Streaming sur http://0.0.0.0:{port}/")
    return server
