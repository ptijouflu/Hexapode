#!/usr/bin/env python3
"""
Test simple du streaming vidéo sans contrôle moteur
"""

import cv2
import time
import threading
import json
import logging
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Import des modules partagés
from hexapod import FastCamera, HTTP_PORT

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class TestStreamHandler(BaseHTTPRequestHandler):
    shared_frame = None
    shared_lock = threading.Lock()
    
    def do_GET(self):
        if self.path == '/':
            self._send_html()
        elif self.path == '/stream':
            self._send_stream()
        else:
            self.send_error(404)
    
    def _send_html(self):
        html = '''<!DOCTYPE html>
<html><head><title>Test Streaming</title></head><body>
<h1>Test Flux Vidéo</h1>
<img src="/stream" style="border:1px solid #000;">
</body></html>'''
        
        data = html.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
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
                
                time.sleep(0.1)
        except:
            pass
    
    def log_message(self, *args):
        pass


def main():
    print("Test du streaming vidéo...")
    
    # Initialiser caméra
    camera = FastCamera()
    time.sleep(1)
    
    # Démarrer serveur HTTP
    server = ThreadedHTTPServer(('localhost', HTTP_PORT), TestStreamHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    
    print(f"Serveur démarré sur http://localhost:{HTTP_PORT}")
    print("Appuyez sur Ctrl+C pour arrêter")
    
    try:
        frame_count = 0
        while True:
            frame = camera.get_frame()
            
            if frame is not None:
                frame_count += 1
                # Ajouter texte sur frame
                cv2.putText(frame, f"Frame {frame_count}", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                with TestStreamHandler.shared_lock:
                    TestStreamHandler.shared_frame = frame
            else:
                # Frame noire de test
                test_frame = np.zeros((240, 640, 3), dtype=np.uint8)
                cv2.putText(test_frame, "CAMERA TEST", (200, 120), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                with TestStreamHandler.shared_lock:
                    TestStreamHandler.shared_frame = test_frame
            
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        print("\nArrêt...")
    
    finally:
        camera.stop()
        server.shutdown()
        print("Terminé.")


if __name__ == '__main__':
    main()