import os
import sys
import time
import select
import termios
import tty
from dynamixel_sdk import *

# --- CONFIGURATION UTILISATEUR ---
DEVICENAME          = '/dev/ttyUSB0'
BAUDRATE            = 1000000
PROTOCOL_VERSION    = 2.0
DXL_IDS             = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

# LE REGLAGE QUE VOUS CHERCHEZ :
# 1.0 = Mouvement normal
# 1.5 = Pas 50% plus grands (Recommandé)
# 2.0 = Pas 2x plus grands (Attention aux limites mécaniques)
AMPLITUDE_FACTOR    = 1.5 

# Adresses mémoire (XL430-W250)
ADDR_TORQUE_ENABLE  = 64
ADDR_GOAL_POSITION  = 116
LEN_GOAL_POSITION   = 4

# --- DONNÉES ORIGINALES (Avancer.mtn3) ---
INIT_POSE_DEG = [30, -30, -30, -30, 15, -30, -15, -30, -30, -30, 30, -30]

WALK_SEQUENCE_DEG = [
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

# --- FONCTIONS ---

def deg2dxl(deg):
    return int(2048 + (deg * (4095.0 / 360.0)))

def amplify_sequence(sequence, factor):
    """Recalcule les pas en augmentant l'amplitude autour de la moyenne"""
    new_sequence = []
    num_motors = len(sequence[0])
    
    # 1. Calculer la position moyenne de chaque moteur (le "centre" du mouvement)
    means = [sum(step[i] for step in sequence) / len(sequence) for i in range(num_motors)]
    
    # 2. Appliquer le facteur d'amplification
    for step in sequence:
        new_step = []
        for i in range(num_motors):
            # Ecart par rapport au centre
            delta = step[i] - means[i]
            # Nouvelle position = Centre + (Ecart * Facteur)
            new_val = means[i] + (delta * factor)
            new_step.append(new_val)
        new_sequence.append(new_step)
        
    return new_sequence

def is_key_pressed():
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

def setup_terminal():
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(sys.stdin.fileno())
    except:
        pass
    return fd, old_settings

def restore_terminal(fd, old_settings):
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def write_positions(groupSyncWrite, angle_list_deg):
    groupSyncWrite.clearParam()
    for i, motor_id in enumerate(DXL_IDS):
        goal_pos = deg2dxl(angle_list_deg[i])
        # Sécurité : Limiter entre 0 et 4095
        goal_pos = max(0, min(4095, goal_pos))
        
        param_goal_position = [DXL_LOBYTE(DXL_LOWORD(goal_pos)), 
                               DXL_HIBYTE(DXL_LOWORD(goal_pos)), 
                               DXL_LOBYTE(DXL_HIWORD(goal_pos)), 
                               DXL_HIBYTE(DXL_HIWORD(goal_pos))]
        groupSyncWrite.addParam(motor_id, param_goal_position)
    groupSyncWrite.txPacket()

# --- MAIN ---

portHandler = PortHandler(DEVICENAME)
packetHandler = PacketHandler(PROTOCOL_VERSION)
groupSyncWrite = GroupSyncWrite(portHandler, packetHandler, ADDR_GOAL_POSITION, LEN_GOAL_POSITION)

try:
    if not portHandler.openPort():
        print("Erreur: Impossible d'ouvrir le port USB.")
        quit()
    if not portHandler.setBaudRate(BAUDRATE):
        print("Erreur: Impossible de changer le Baudrate.")
        quit()
    
    for motor_id in DXL_IDS:
        packetHandler.write1ByteTxRx(portHandler, motor_id, ADDR_TORQUE_ENABLE, 1)

    print(f"--- HEXAPODE PRET (AMPLITUDE x{AMPLITUDE_FACTOR}) ---")
    
    # Calculer la nouvelle marche amplifiée
    amplified_walk = amplify_sequence(WALK_SEQUENCE_DEG, AMPLITUDE_FACTOR)

    print("Position initiale...")
    write_positions(groupSyncWrite, INIT_POSE_DEG)
    time.sleep(2.0)

    print("Marche en cours... (Appuyez sur une touche pour arrêter)")
    fd, old_settings = setup_terminal()

    step_index = 0
    walking = True
    
    while walking:
        if is_key_pressed():
            print("\nArrêt demandé !")
            walking = False
            break

        current_step = amplified_walk[step_index]
        write_positions(groupSyncWrite, current_step)
        
        step_index = (step_index + 1) % len(amplified_walk)
        time.sleep(0.08) 

finally:
    try:
        restore_terminal(fd, old_settings)
    except:
        pass
    portHandler.closePort()
    print("Terminé.")