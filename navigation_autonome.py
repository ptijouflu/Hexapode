#!/usr/bin/env python3
"""
Hexapode - Navigation Autonome avec Évitement d'Obstacles
Avance automatiquement et esquive les obstacles détectés
Format large (640x240) pour meilleure vision latérale
"""

import os
import sys
import cv2
import numpy as np
import threading
import time
import logging
import subprocess
import tempfile
import signal
import select
import termios
import tty
from collections import deque
from datetime import datetime

# Ajouter le chemin parent pour importer les modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from dynamixel_sdk import *
    DYNAMIXEL_AVAILABLE = True
except ImportError:
    DYNAMIXEL_AVAILABLE = False
    print("⚠ dynamixel_sdk non disponible - Mode simulation")

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION MOTEURS (depuis deplacement.py)
# ============================================================================

DEVICENAME = '/dev/ttyUSB0'
BAUDRATE = 1000000
PROTOCOL_VERSION = 2.0
DXL_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

ADDR_TORQUE_ENABLE = 64
ADDR_GOAL_POSITION = 116
LEN_GOAL_POSITION = 4

# Facteurs d'amplitude
FACTOR_WALK = 2
FACTOR_SLIDE = 1.2

# Position initiale
INIT_POSE = [30, -30, -30, -30, 15, -30, -15, -30, -30, -30, 30, -30]

# Séquences de mouvement
SEQ_MOVE_F = [
    [51.54, -40, -40, -10, 10, -10, -10, -10, -50, -10, 61.54, -20],
    [43.85, -20, -43.85, -10, 13.85, -10, -13.85, -10, -46.15, -10, 69.23, -30],
    [47.69, -10, -47.69, -10, 17.69, -10, -17.69, -10, -53.85, -20, 76.92, -40],
    [51.54, -10, -51.54, -10, 21.54, -10, -21.54, -10, -61.54, -30, 84.62, -20],
    [55.38, -10, -55.38, -10, 25.38, -10, -13.85, -20, -69.23, -40, 80.77, -10],
    [59.23, -10, -59.23, -10, 29.23, -10, -6.15, -30, -76.92, -20, 76.92, -10],
    [63.08, -10, -63.08, -10, 21.54, -20, 1.54, -40, -73.08, -10, 73.08, -10],
    [66.92, -10, -66.92, -10, 13.85, -30, 9.23, -20, -69.23, -10, 69.23, -10],
    [70.77, -10, -59.23, -20, 6.15, -40, 5.38, -10, -65.38, -10, 65.38, -10],
    [74.62, -10, -51.54, -30, -1.54, -20, 1.54, -10, -61.54, -10, 61.54, -10],
    [66.92, -20, -43.85, -40, 2.31, -10, -2.31, -10, -57.69, -10, 57.69, -10],
    [59.23, -30, -36.15, -20, 6.15, -10, -6.15, -10, -53.85, -10, 53.85, -10]
]

SEQ_SLIDE_R = [
    [0, -35, -60, -25, 8, -60, -8, -50, 0, -35, 40, -25],
    [-10, -20, -50, -50, 8, -20, -8, -30, 10, -20, -10, -50],
    [-10, -40, -50, -20, 8, -20, -8, -30, 10, -40, -10, -20],
    [40, -40, -50, -20, 8, -20, -8, -30, -40, -40, -10, -20],
    [60, -20, -60, -30, 8, -50, -8, -50, -60, -20, -10, -30]
]

SEQ_SLIDE_L = [
    [60, -25, 0, -35, 8, -50, -8, -60, -40, -25, 0, -35],
    [50, -50, 10, -20, 8, -30, -8, -20, 10, -50, -10, -20],
    [50, -20, 10, -40, 8, -30, -8, -20, 10, -20, -10, -40],
    [50, -20, -40, -40, 8, -30, -8, -20, 10, -20, 40, -40],
    [60, -30, -60, -20, 8, -50, -8, -50, 10, -30, 60, -20]
]


def deg2dxl(deg):
    return int(2048 + (deg * (4095.0 / 360.0)))


def amplify_sequence(sequence, factor):
    new_sequence = []
    num_motors = len(sequence[0])
    means = [sum(step[i] for step in sequence) / len(sequence) for i in range(num_motors)]
    for step in sequence:
        new_step = []
        for i in range(num_motors):
            delta = step[i] - means[i]
            new_val = means[i] + (delta * factor)
            new_step.append(new_val)
        new_sequence.append(new_step)
    return new_sequence


# ============================================================================
# GESTION CLAVIER
# ============================================================================

class KeyboardHandler:
    """Gestion du clavier en mode non-bloquant"""
    
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        self._setup()
    
    def _setup(self):
        """Configure le terminal en mode raw"""
        tty.setcbreak(self.fd)
    
    def get_key(self):
        """Retourne la touche pressée ou None"""
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return None
    
    def restore(self):
        """Restaure les paramètres du terminal"""
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)


# ============================================================================
# CAMERA CAPTURE (optimisée)
# ============================================================================

class FastCamera:
    """
    Capture caméra optimisée
    Format large (640x240) pour meilleure vision latérale
    """
    
    def __init__(self, width=640, height=240, fps=10):
        self.width = width
        self.height = height
        self.fps = fps
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.process = None
        
        logger.info(f"Init camera {width}x{height}@{fps}fps")
        self._start()
    
    def _start(self):
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
        self.temp_dir = tempfile.mkdtemp()
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
    
    def _read_mjpeg(self):
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
                
                if len(buffer) > 500000:
                    buffer = buffer[-100000:]
        except:
            pass
        finally:
            self.running = False
    
    def _capture_loop(self):
        frame_delay = 1.0 / self.fps
        frame_file = os.path.join(self.temp_dir, "frame.jpg")
        
        while self.running:
            start = time.time()
            try:
                subprocess.run(
                    ['rpicam-jpeg', '--width', str(self.width), '--height', str(self.height),
                     '--timeout', '500', '--quality', '60', '--output', frame_file, '--nopreview'],
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
        with self.frame_lock:
            return self.current_frame.copy() if self.current_frame is not None else None
    
    def stop(self):
        self.running = False
        if self.process:
            self.process.terminate()
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)


# ============================================================================
# DÉTECTEUR D'OBSTACLES
# ============================================================================

class ObstacleDetector:
    """
    Détection d'obstacles optimisée
    Format large pour meilleure vision latérale
    """
    
    def __init__(self, min_area=400, roi_top=0.30, roi_bottom=0.95, edge_thresh=50):
        self.min_area = min_area
        self.roi_top = roi_top
        self.roi_bottom = roi_bottom
        self.edge_thresh = edge_thresh
        self._kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        
    def detect(self, frame):
        """
        Retourne: obstacles, danger_level, obstacle_position
        obstacle_position: 'LEFT', 'RIGHT', 'CENTER', 'BOTH', None
        """
        if frame is None:
            return [], "INIT", None
        
        h, w = frame.shape[:2]
        y1 = int(h * self.roi_top)
        y2 = int(h * self.roi_bottom)
        roi = frame[y1:y2, :]
        
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Seuillage adaptatif (détecte objets plus sombres/clairs que le sol)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV, 21, 5
        )
        
        # Détection de contours Canny avec seuils ajustés
        edges = cv2.Canny(blurred, self.edge_thresh, self.edge_thresh * 2)
        combined = cv2.bitwise_or(thresh, edges)
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, self._kernel)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, self._kernel)
        
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        obstacles = []
        third_w = w // 3
        
        has_left = False
        has_right = False
        has_center = False
        closest_center_dist = 0
        
        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.min_area:
                continue
            
            x, y, bw, bh = cv2.boundingRect(cnt)
            y_global = y + y1
            cx = x + bw // 2
            
            dist = (y_global - y1) / (y2 - y1)
            
            if cx < third_w:
                pos = "G"
                if dist > 0.35:  # Seuil ajusté pour détecter plus tôt
                    has_left = True
            elif cx > 2 * third_w:
                pos = "D"
                if dist > 0.35:  # Seuil ajusté pour détecter plus tôt
                    has_right = True
            else:
                pos = "C"
                if dist > 0.45:  # Seuil ajusté
                    has_center = True
                    closest_center_dist = max(closest_center_dist, dist)
            
            # Taille (seuils ajustés pour image large 640x240)
            size = "S" if area < 1500 else ("M" if area < 6000 else "L")
            
            obstacles.append({
                'bbox': (x, y_global, bw, bh),
                'pos': pos,
                'dist': dist,
                'size': size
            })
        
        # Déterminer le niveau de danger et la position
        if has_center and closest_center_dist > 0.55:  # Seuil ajusté
            danger = "STOP"
            position = "CENTER"
        elif has_center:
            danger = "WARN"
            position = "CENTER"
        elif has_left and has_right:
            danger = "WARN"
            position = "BOTH"
        elif has_left:
            danger = "OBS"
            position = "LEFT"
        elif has_right:
            danger = "OBS"
            position = "RIGHT"
        else:
            danger = "OK"
            position = None
        
        return obstacles, danger, position
    
    def draw(self, frame, obstacles, danger, position):
        """Dessine les obstacles sur la frame (format large)"""
        if frame is None:
            return frame
        
        h, w = frame.shape[:2]
        y1 = int(h * self.roi_top)
        y2 = int(h * self.roi_bottom)
        
        # Zone ROI
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
        
        # Couleur selon danger
        colors = {
            "OK": (0, 255, 0),
            "OBS": (0, 220, 220),
            "WARN": (0, 140, 255),
            "STOP": (0, 0, 255)
        }
        color = colors.get(danger, (128, 128, 128))
        
        for o in obstacles:
            x, y, bw, bh = o['bbox']
            cv2.rectangle(frame, (x, y), (x+bw, y+bh), color, 2)
            cv2.putText(frame, f"{o['size']}{o['pos']}", (x, y-3),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Indicateur danger (coin supérieur droit)
        cv2.rectangle(frame, (w-60, 5), (w-5, 28), color, -1)
        cv2.putText(frame, danger, (w-55, 22),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        return frame


# ============================================================================
# CONTRÔLEUR MOTEURS
# ============================================================================

class MotorController:
    """Contrôle des moteurs Dynamixel"""
    
    def __init__(self):
        self.connected = False
        self.portHandler = None
        self.packetHandler = None
        self.groupSyncWrite = None
        
        # Séquences pré-calculées
        self.seq_forward = amplify_sequence(SEQ_MOVE_F, FACTOR_WALK)
        self.seq_slide_left = amplify_sequence(SEQ_SLIDE_L, FACTOR_SLIDE)
        self.seq_slide_right = amplify_sequence(SEQ_SLIDE_R, FACTOR_SLIDE)
        
        self.step_index = 0
        self.current_action = 'stop'
        
        if DYNAMIXEL_AVAILABLE:
            self._connect()
    
    def _connect(self):
        try:
            self.portHandler = PortHandler(DEVICENAME)
            self.packetHandler = PacketHandler(PROTOCOL_VERSION)
            
            if not self.portHandler.openPort():
                logger.error("Impossible d'ouvrir le port série")
                return
            
            if not self.portHandler.setBaudRate(BAUDRATE):
                logger.error("Impossible de configurer le baudrate")
                return
            
            self.groupSyncWrite = GroupSyncWrite(
                self.portHandler, self.packetHandler,
                ADDR_GOAL_POSITION, LEN_GOAL_POSITION
            )
            
            # Activer le torque
            for mid in DXL_IDS:
                self.packetHandler.write1ByteTxRx(
                    self.portHandler, mid, ADDR_TORQUE_ENABLE, 1
                )
            
            self.connected = True
            logger.info("✓ Moteurs connectés")
            
            # Position initiale
            self._write_positions(INIT_POSE)
            time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Erreur connexion moteurs: {e}")
            self.connected = False
    
    def _write_positions(self, angles):
        if not self.connected or self.groupSyncWrite is None:
            return
        
        self.groupSyncWrite.clearParam()
        
        for i, motor_id in enumerate(DXL_IDS):
            goal_pos = deg2dxl(angles[i])
            goal_pos = max(0, min(4095, goal_pos))
            param = [
                DXL_LOBYTE(DXL_LOWORD(goal_pos)),
                DXL_HIBYTE(DXL_LOWORD(goal_pos)),
                DXL_LOBYTE(DXL_HIWORD(goal_pos)),
                DXL_HIBYTE(DXL_HIWORD(goal_pos))
            ]
            self.groupSyncWrite.addParam(motor_id, param)
        
        self.groupSyncWrite.txPacket()
    
    def stop(self):
        """Arrête le mouvement"""
        if self.current_action != 'stop':
            self.current_action = 'stop'
            self.step_index = 0
            self._write_positions(INIT_POSE)
            logger.info("🛑 STOP")
    
    def forward(self):
        """Avance d'un pas"""
        self.current_action = 'forward'
        self._write_positions(self.seq_forward[self.step_index])
        self.step_index = (self.step_index + 1) % len(self.seq_forward)
    
    def slide_left(self):
        """Translation gauche d'un pas"""
        if self.current_action != 'slide_left':
            self.step_index = 0
        self.current_action = 'slide_left'
        self._write_positions(self.seq_slide_left[self.step_index])
        self.step_index = (self.step_index + 1) % len(self.seq_slide_left)
    
    def slide_right(self):
        """Translation droite d'un pas"""
        if self.current_action != 'slide_right':
            self.step_index = 0
        self.current_action = 'slide_right'
        self._write_positions(self.seq_slide_right[self.step_index])
        self.step_index = (self.step_index + 1) % len(self.seq_slide_right)
    
    def get_delay(self):
        """Retourne le délai selon l'action"""
        if self.current_action in ['slide_left', 'slide_right']:
            return 0.15
        return 0.08
    
    def disconnect(self):
        if self.connected:
            self._write_positions(INIT_POSE)
            time.sleep(0.3)
            for mid in DXL_IDS:
                self.packetHandler.write1ByteTxRx(
                    self.portHandler, mid, ADDR_TORQUE_ENABLE, 0
                )
            self.portHandler.closePort()
            logger.info("Moteurs déconnectés")


# ============================================================================
# NAVIGATEUR AUTONOME
# ============================================================================

class AutonomousNavigator:
    """
    Navigation autonome avec évitement d'obstacles
    
    Logique:
    1. Avancer par défaut
    2. Si obstacle à gauche -> translation droite
    3. Si obstacle à droite -> translation gauche
    4. Si obstacle au centre -> stop puis décider
    5. Si libre -> reprendre avance
    
    Contrôles:
    - ESPACE: Pause/Reprendre (arrête moteurs + position initiale)
    - Ctrl+C: Quitter complètement
    """
    
    def __init__(self):
        self.running = False
        self.paused = False  # État pause
        self.quit_requested = False  # Demande de quitter
        
        # Gestion clavier
        self.keyboard = KeyboardHandler()
        
        # Composants - Format large pour meilleure vision latérale
        self.camera = FastCamera(width=640, height=240, fps=10)
        self.detector = ObstacleDetector(
            min_area=400,      # Surface min pour détecter un obstacle
            roi_top=0.30,      # Zone de détection commence à 30% du haut
            roi_bottom=0.95,   # Zone de détection finit à 95% du haut
            edge_thresh=50     # Seuil Canny
        )
        self.motors = MotorController()
        
        # État
        self.current_state = "INIT"
        self.last_obstacle_position = None
        self.escape_direction = None
        self.escape_steps = 0
        self.max_escape_steps = 10  # Max pas de translation avant de réessayer
        
        # Stats
        self.detection_count = 0
        self.start_time = None
        
        time.sleep(1)  # Attendre initialisation camera
        logger.info("✓ Navigateur autonome initialisé")
    
    def _decide_action(self, danger, position):
        """
        Machine à états pour décider de l'action
        Retourne: 'forward', 'slide_left', 'slide_right', 'stop'
        Seuils ajustés pour format large (640x240)
        """
        
        # Obstacle au centre proche -> STOP
        if danger == "STOP":
            self.current_state = "BLOCKED"
            # Choisir direction d'échappement si pas déjà définie
            if self.escape_direction is None:
                self.escape_direction = "LEFT"  # Par défaut gauche
            # Essayer de contourner au lieu de rester bloqué
            if self.escape_direction == "LEFT":
                return 'slide_left'
            else:
                return 'slide_right'
        
        # Obstacle au centre (moins proche) -> essayer de contourner
        if position == "CENTER":
            self.current_state = "AVOIDING"
            if self.escape_direction is None:
                self.escape_direction = "LEFT"
            if self.escape_direction == "LEFT":
                return 'slide_left'
            else:
                return 'slide_right'
        
        # Obstacles des deux côtés -> alterner la direction
        if position == "BOTH":
            self.current_state = "BLOCKED"
            self.escape_steps += 1
            # Alterner la direction tous les 5 pas
            if self.escape_steps % 10 < 5:
                return 'slide_left'
            else:
                return 'slide_right'
        
        # Obstacle à gauche -> translation droite
        if position == "LEFT":
            self.current_state = "AVOIDING"
            self.escape_direction = "RIGHT"
            self.escape_steps += 1
            if self.escape_steps > self.max_escape_steps:
                # Trop de translations, essayer d'avancer
                self.escape_steps = 0
                return 'forward'
            return 'slide_right'
        
        # Obstacle à droite -> translation gauche
        if position == "RIGHT":
            self.current_state = "AVOIDING"
            self.escape_direction = "LEFT"
            self.escape_steps += 1
            if self.escape_steps > self.max_escape_steps:
                self.escape_steps = 0
                return 'forward'
            return 'slide_left'
        
        # Pas d'obstacle -> avancer
        self.current_state = "FORWARD"
        self.escape_direction = None
        self.escape_steps = 0
        return 'forward'
    
    def _handle_keyboard(self):
        """
        Gère les entrées clavier
        Retourne True si on doit quitter
        """
        key = self.keyboard.get_key()
        
        if key is None:
            return False
        
        # Espace = Pause/Reprendre
        if key == ' ':
            self.paused = not self.paused
            if self.paused:
                self.motors.stop()
                logger.info("⏸️  PAUSE - Appuyez sur ESPACE pour reprendre")
            else:
                logger.info("▶️  REPRISE de la navigation")
                self.step_index = 0
            return False
        
        # Ctrl+C ou 'q' = Quitter
        if key == '\x03' or key == 'q' or key == 'Q':
            self.quit_requested = True
            return True
        
        return False
    
    def run(self):
        """Boucle principale de navigation"""
        self.running = True
        self.start_time = time.time()
        last_log_time = time.time()
        
        logger.info("=" * 50)
        logger.info("🤖 NAVIGATION AUTONOME DÉMARRÉE")
        logger.info("   ESPACE = Pause/Reprendre")
        logger.info("   Ctrl+C ou Q = Quitter")
        logger.info("=" * 50)
        
        try:
            while self.running and not self.quit_requested:
                # Vérifier le clavier
                if self._handle_keyboard():
                    break
                
                # Si en pause, juste attendre
                if self.paused:
                    time.sleep(0.1)
                    continue
                
                # Capturer frame
                frame = self.camera.get_frame()
                
                if frame is None:
                    time.sleep(0.05)
                    continue
                
                # Détecter obstacles
                obstacles, danger, position = self.detector.detect(frame)
                self.detection_count += 1
                
                # Décider action
                action = self._decide_action(danger, position)
                
                # Exécuter action
                if action == 'forward':
                    self.motors.forward()
                elif action == 'slide_left':
                    self.motors.slide_left()
                elif action == 'slide_right':
                    self.motors.slide_right()
                else:
                    self.motors.stop()
                
                # Log toutes les secondes
                if time.time() - last_log_time >= 1.0:
                    elapsed = time.time() - self.start_time
                    det_fps = self.detection_count / elapsed if elapsed > 0 else 0
                    
                    action_symbols = {
                        'forward': '⬆️  AVANCE',
                        'slide_left': '⬅️  GAUCHE',
                        'slide_right': '➡️  DROITE',
                        'stop': '🛑 STOP'
                    }
                    
                    obs_info = ""
                    if obstacles:
                        obs_info = " | " + ", ".join([f"{o['size']}{o['pos']}" for o in obstacles[:3]])
                    
                    logger.info(
                        f"[{danger:4}] {action_symbols.get(action, action):12} | "
                        f"{det_fps:.1f} det/s | {len(obstacles)} obs{obs_info}"
                    )
                    last_log_time = time.time()
                
                # Délai selon action
                time.sleep(self.motors.get_delay())
                
        except KeyboardInterrupt:
            logger.info("\n⚠️ Ctrl+C détecté - Arrêt...")
        finally:
            self.stop()
    
    def stop(self):
        """Arrête tout proprement"""
        logger.info("Arrêt en cours...")
        self.running = False
        
        # Arrêter les moteurs et position initiale
        self.motors.stop()
        time.sleep(0.5)
        
        # Déconnecter les moteurs
        self.motors.disconnect()
        
        # Arrêter la caméra
        self.camera.stop()
        
        # Restaurer le terminal
        self.keyboard.restore()
        
        logger.info("✓ Navigation arrêtée proprement")
        logger.info("Au revoir! 👋")


# ============================================================================
# MAIN
# ============================================================================

def main():
    # Ignorer SIGINT pour le gérer manuellement
    original_sigint = signal.getsignal(signal.SIGINT)
    
    print()
    print("=" * 60)
    print("   🤖 HEXAPODE - NAVIGATION AUTONOME")
    print("   Format large (640x240) pour vision latérale")
    print("=" * 60)
    print()
    print("   Comportement:")
    print("   - Avance automatiquement")
    print("   - Obstacle à GAUCHE  → Translation DROITE")
    print("   - Obstacle à DROITE  → Translation GAUCHE")
    print("   - Obstacle au CENTRE → Contournement")
    print("   - Obstacles des 2 côtés → Alternance G/D")
    print()
    print("   Contrôles:")
    print("   - ESPACE   : Pause / Reprendre")
    print("   - Ctrl+C   : Quitter")
    print("   - Q        : Quitter")
    print()
    print("=" * 60)
    print()
    print("   Démarrage dans 3 secondes...")
    
    time.sleep(3)
    
    navigator = None
    try:
        navigator = AutonomousNavigator()
        navigator.run()
    except Exception as e:
        logger.error(f"Erreur: {e}")
    finally:
        if navigator:
            navigator.stop()
        # Restaurer le handler SIGINT original
        signal.signal(signal.SIGINT, original_sigint)


if __name__ == '__main__':
    main()
