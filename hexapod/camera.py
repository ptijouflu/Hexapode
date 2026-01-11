"""
Hexapode - Capture caméra
Capture vidéo optimisée pour Raspberry Pi
"""

import os
import subprocess
import tempfile
import threading
import time
import logging

import cv2
import numpy as np

from .constants import CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS

logger = logging.getLogger(__name__)


class FastCamera:
    """
    Capture caméra optimisée pour Raspberry Pi.
    Supporte libcamera-vid (préféré) et rpicam-jpeg (fallback).
    """
    
    def __init__(self, width=None, height=None, fps=None):
        self.width = width if width is not None else CAMERA_WIDTH
        self.height = height if height is not None else CAMERA_HEIGHT
        self.fps = fps if fps is not None else CAMERA_FPS
        
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.process = None
        self.temp_dir = None
        
        logger.info(f"Init camera {self.width}x{self.height}@{self.fps}fps")
        self._start()
    
    def _start(self):
        """Démarre la capture caméra"""
        self.running = True
        
        # Essayer libcamera-vid d'abord
        try:
            cmd = [
                'libcamera-vid',
                '--width', str(self.width),
                '--height', str(self.height),
                '--framerate', str(self.fps),
                '--timeout', '0',
                '--codec', 'mjpeg',
                '--quality', '60',
                '--nopreview',
                '-o', '-'
            ]
            
            self.process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=10**6
            )
            
            self.capture_thread = threading.Thread(target=self._read_mjpeg, daemon=True)
            self.capture_thread.start()
            logger.info("✓ Camera (libcamera-vid)")
            
        except Exception as e:
            logger.warning(f"libcamera-vid échoué: {e}, fallback rpicam-jpeg")
            self._start_fallback()
    
    def _start_fallback(self):
        """Démarre en mode fallback avec rpicam-jpeg"""
        self.temp_dir = tempfile.mkdtemp()
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def _read_mjpeg(self):
        """Lit le flux MJPEG de libcamera-vid"""
        buffer = b''
        jpeg_start = b'\xff\xd8'
        jpeg_end = b'\xff\xd9'
        
        try:
            while self.running and self.process:
                chunk = self.process.stdout.read(4096)
                if not chunk:
                    break
                
                buffer += chunk
                
                start_idx = buffer.find(jpeg_start)
                if start_idx != -1:
                    end_idx = buffer.find(jpeg_end, start_idx)
                    if end_idx != -1:
                        jpeg_data = buffer[start_idx:end_idx + 2]
                        buffer = buffer[end_idx + 2:]
                        
                        frame = cv2.imdecode(
                            np.frombuffer(jpeg_data, dtype=np.uint8),
                            cv2.IMREAD_COLOR
                        )
                        
                        if frame is not None:
                            with self.frame_lock:
                                self.current_frame = frame
                
                # Limiter la taille du buffer
                if len(buffer) > 500000:
                    buffer = buffer[-100000:]
        except:
            pass
        finally:
            self.running = False
    
    def _capture_loop(self):
        """Capture en mode fallback avec rpicam-jpeg"""
        frame_delay = 1.0 / self.fps
        frame_file = os.path.join(self.temp_dir, "frame.jpg")
        
        while self.running:
            start = time.time()
            try:
                subprocess.run(
                    ['rpicam-jpeg', 
                     '--width', str(self.width), 
                     '--height', str(self.height),
                     '--timeout', '500', 
                     '--quality', '60', 
                     '--output', frame_file, 
                     '--nopreview'],
                    capture_output=True, timeout=2
                )
                
                if os.path.exists(frame_file):
                    frame = cv2.imread(frame_file)
                    if frame is not None:
                        with self.frame_lock:
                            self.current_frame = frame
            except:
                pass
            
            elapsed = time.time() - start
            if elapsed < frame_delay:
                time.sleep(frame_delay - elapsed)
    
    def get_frame(self):
        """Retourne la dernière frame capturée"""
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def stop(self):
        """Arrête la capture caméra"""
        self.running = False
        
        if self.process:
            self.process.terminate()
            self.process = None
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None
        
        logger.info("Camera arrêtée")
    
    def __del__(self):
        """Destructeur"""
        self.stop()
