#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Video Stream Reader - Reads MJPEG streams via HTTP
"""

import threading
import urllib.request
import urllib.error
import time as time_module
from PyQt6.QtGui import QImage, QPixmap
from video_signals import VideoSignals
from config import DEFAULT_VIDEO_URL, VIDEO_RECONNECT_INTERVAL


class VideoStreamReader:
    """Lecteur de flux vidéo MJPEG via HTTP"""
    
    def __init__(self, url=DEFAULT_VIDEO_URL):
        self.url = url
        self.running = False
        self.thread = None
        self.signals = VideoSignals()
        
    def start(self):
        """Démarre la lecture du flux"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._read_stream, daemon=True)
            self.thread.start()
            self.signals.status_changed.emit("Connexion au flux...")
    
    def stop(self):
        """Arrête la lecture du flux"""
        self.running = False
        self.signals.status_changed.emit("Flux arrêté")
    
    def _read_stream(self):
        """Lit le flux MJPEG (exécuté dans un thread)"""
        while self.running:
            try:
                # Connexion HTTP au flux
                req = urllib.request.Request(self.url)
                response = urllib.request.urlopen(req, timeout=5)
                
                self.signals.status_changed.emit("Flux actif")
                
                # Buffer pour l'image JPEG
                bytes_data = b''
                
                while self.running:
                    # Lire des chunks
                    chunk = response.read(1024)
                    if not chunk:
                        break
                    
                    bytes_data += chunk
                    
                    # Chercher les marqueurs JPEG
                    a = bytes_data.find(b'\xff\xd8')  # Début JPEG
                    b = bytes_data.find(b'\xff\xd9')  # Fin JPEG
                    
                    if a != -1 and b != -1:
                        jpg = bytes_data[a:b+2]
                        bytes_data = bytes_data[b+2:]
                        
                        # Convertir en QPixmap
                        image = QImage()
                        if image.loadFromData(jpg):
                            pixmap = QPixmap.fromImage(image)
                            self.signals.frame_ready.emit(pixmap)
                
            except urllib.error.URLError:
                if self.running:
                    self.signals.status_changed.emit(f"Flux non disponible - Réessai dans {VIDEO_RECONNECT_INTERVAL}s...")
                time_module.sleep(VIDEO_RECONNECT_INTERVAL)
            except Exception as e:
                if self.running:
                    self.signals.status_changed.emit(f"Erreur: {str(e)[:30]} - Réessai dans {VIDEO_RECONNECT_INTERVAL}s...")
                time_module.sleep(VIDEO_RECONNECT_INTERVAL)
