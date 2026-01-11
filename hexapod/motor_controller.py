"""
Hexapode - Contrôleur de moteurs Dynamixel
Classe partagée pour le contrôle des 12 servomoteurs
"""

import time
import logging

try:
    from dynamixel_sdk import *
    DYNAMIXEL_AVAILABLE = True
except ImportError:
    DYNAMIXEL_AVAILABLE = False
    print(" dynamixel_sdk non disponible - Mode simulation")

from .constants import (
    DEVICENAME, BAUDRATE, PROTOCOL_VERSION, DXL_IDS,
    ADDR_TORQUE_ENABLE, ADDR_GOAL_POSITION, LEN_GOAL_POSITION,
    FACTOR_WALK, FACTOR_SLIDE, FACTOR_TURN
)
from .movements import (
    INIT_POSE, SEQ_MOVE_F, SEQ_MOVE_B, SEQ_SLIDE_L, SEQ_SLIDE_R,
    SEQ_PIVOT_L, SEQ_PIVOT_R, deg2dxl, amplify_sequence
)

logger = logging.getLogger(__name__)


class MotorController:
    """
    Contrôleur de moteurs Dynamixel pour l'hexapode.
    Gère la connexion, les mouvements et la déconnexion.
    """
    
    def __init__(self, auto_connect=True):
        self.connected = False
        self.portHandler = None
        self.packetHandler = None
        self.groupSyncWrite = None
        
        # Index de pas pour les séquences
        self.step_index = 0
        self.current_action = 'stop'
        
        # Séquences pré-calculées avec facteurs d'amplitude
        self.seq_forward = amplify_sequence(SEQ_MOVE_F, FACTOR_WALK)
        self.seq_backward = amplify_sequence(SEQ_MOVE_B, FACTOR_WALK)
        self.seq_slide_left = amplify_sequence(SEQ_SLIDE_L, FACTOR_SLIDE)
        self.seq_slide_right = amplify_sequence(SEQ_SLIDE_R, FACTOR_SLIDE)
        self.seq_pivot_left = amplify_sequence(SEQ_PIVOT_L, FACTOR_TURN)
        self.seq_pivot_right = amplify_sequence(SEQ_PIVOT_R, FACTOR_TURN)
        
        if auto_connect and DYNAMIXEL_AVAILABLE:
            self._connect()
    
    def _connect(self):
        """Établit la connexion avec les moteurs"""
        try:
            self.portHandler = PortHandler(DEVICENAME)
            self.packetHandler = PacketHandler(PROTOCOL_VERSION)
            
            if not self.portHandler.openPort():
                logger.error("Impossible d'ouvrir le port série")
                return False
            
            if not self.portHandler.setBaudRate(BAUDRATE):
                logger.error("Impossible de configurer le baudrate")
                return False
            
            self.groupSyncWrite = GroupSyncWrite(
                self.portHandler, self.packetHandler,
                ADDR_GOAL_POSITION, LEN_GOAL_POSITION
            )
            
            # Activer le torque sur tous les moteurs
            for mid in DXL_IDS:
                self.packetHandler.write1ByteTxRx(
                    self.portHandler, mid, ADDR_TORQUE_ENABLE, 1
                )
            
            self.connected = True
            logger.info("[OK] Moteurs connectés")
            
            # Position initiale
            self._write_positions(INIT_POSE)
            time.sleep(0.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur connexion moteurs: {e}")
            self.connected = False
            return False
    
    def _write_positions(self, angles):
        """Envoie les positions à tous les moteurs simultanément"""
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
        """Arrête le mouvement et retourne en position initiale"""
        if self.current_action != 'stop':
            self.current_action = 'stop'
            self.step_index = 0
            self._write_positions(INIT_POSE)
            logger.info("STOP STOP")
    
    def forward(self):
        """Effectue un pas en avant"""
        self.current_action = 'forward'
        self._write_positions(self.seq_forward[self.step_index])
        self.step_index = (self.step_index + 1) % len(self.seq_forward)
    
    def backward(self):
        """Effectue un pas en arrière"""
        self.current_action = 'backward'
        self._write_positions(self.seq_backward[self.step_index])
        self.step_index = (self.step_index + 1) % len(self.seq_backward)
    
    def slide_left(self):
        """Effectue un pas de translation vers la gauche"""
        if self.current_action != 'slide_left':
            self.step_index = 0
        self.current_action = 'slide_left'
        self._write_positions(self.seq_slide_left[self.step_index])
        self.step_index = (self.step_index + 1) % len(self.seq_slide_left)
    
    def slide_right(self):
        """Effectue un pas de translation vers la droite"""
        if self.current_action != 'slide_right':
            self.step_index = 0
        self.current_action = 'slide_right'
        self._write_positions(self.seq_slide_right[self.step_index])
        self.step_index = (self.step_index + 1) % len(self.seq_slide_right)
    
    def pivot_left(self):
        """Effectue un pas de rotation vers la gauche"""
        if self.current_action != 'pivot_left':
            self.step_index = 0
        self.current_action = 'pivot_left'
        self._write_positions(self.seq_pivot_left[self.step_index])
        self.step_index = (self.step_index + 1) % len(self.seq_pivot_left)
    
    def pivot_right(self):
        """Effectue un pas de rotation vers la droite"""
        if self.current_action != 'pivot_right':
            self.step_index = 0
        self.current_action = 'pivot_right'
        self._write_positions(self.seq_pivot_right[self.step_index])
        self.step_index = (self.step_index + 1) % len(self.seq_pivot_right)
    
    def get_delay(self):
        """Retourne le délai recommandé selon l'action en cours"""
        if self.current_action in ['slide_left', 'slide_right']:
            return 0.15  # Translation
        elif self.current_action in ['pivot_left', 'pivot_right']:
            return 0.15  # Rotation
        elif self.current_action in ['forward', 'backward']:
            return 0.08  # Marche rapide
        return 0.1  # Par défaut
    
    def get_delay_slow(self):
        """Retourne un délai plus lent (pour navigation avec détection)"""
        if self.current_action in ['slide_left', 'slide_right']:
            return 0.25  # Translation
        elif self.current_action in ['pivot_left', 'pivot_right']:
            return 0.20  # Rotation
        return 0.15  # Marche
    
    def disconnect(self):
        """Déconnecte les moteurs proprement"""
        if self.connected:
            self._write_positions(INIT_POSE)
            time.sleep(0.3)
            
            # Désactiver le torque
            for mid in DXL_IDS:
                self.packetHandler.write1ByteTxRx(
                    self.portHandler, mid, ADDR_TORQUE_ENABLE, 0
                )
            
            self.portHandler.closePort()
            self.connected = False
            logger.info("Moteurs déconnectés")
    
    def __del__(self):
        """Destructeur - assure la déconnexion propre"""
        if self.connected:
            self.disconnect()
