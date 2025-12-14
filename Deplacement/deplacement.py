import sys
import time
import select
import termios
import tty
from dynamixel_sdk import *

# --- CONFIGURATION ---
DEVICENAME          = '/dev/ttyUSB0'
BAUDRATE            = 1000000
PROTOCOL_VERSION    = 2.0
DXL_IDS             = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

# --- REGLAGES D'AMPLITUDE ---
FACTOR_WALK    = 2 
FACTOR_SLIDE   = 1.2 # On garde 0.9 pour la translation, c'est plus sûr
FACTOR_TURN    = 1.0

# Adresses Mémoire (XL430-W250)
ADDR_TORQUE_ENABLE  = 64
ADDR_GOAL_POSITION  = 116
LEN_GOAL_POSITION   = 4

# --- DONNÉES EXTRAITES ---

INIT_POSE = [30, -30, -30, -30, 15, -30, -15, -30, -30, -30, 30, -30]

# Séquence Avancer (Move F)
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

# Séquence Reculer (Move B)
SEQ_MOVE_B = [
    [59.23, -30, -36.15, -20, 6.15, -10, -6.15, -10, -53.85, -10, 53.85, -10],
    [66.92, -20, -43.85, -40, 2.31, -10, -2.31, -10, -57.69, -10, 58, -10],
    [75, -10, -52, -30, -2, -20, 2, -10, -62, -10, 62, -10],
    [71, -10, -59, -20, 6.2, -40, 5, -10, -65, -10, 65, -10],
    [67, -10, -67, -10, 14, -30, 9, -20, -69, -10, 69, -10],
    [63, -10, -63, -10, 22, -20, 2, -40, -73, -10, 73, -10],
    [59, -10, -59, -10, 29, -10, -6.2, -30, -77, -20, 77, -10],
    [55, -10, -55, -10, 25, -10, -14, -20, -69, -40, 81, -10],
    [52, -10, -52, -10, 22, -10, -22, -10, -62, -30, 85, -20],
    [48, -10, -48, -10, 18, -10, -18, -10, -54, -20, 77, -40],
    [44, -20, -44, -10, 14, -10, -14, -10, -46, -10, 69, -30],
    [52, -40, -40, -10, 10, -10, -10, -10, -50, -10, 62, -20]
]

# --- CORRECTION DES SEQUENCES DE TRANSLATION ---

# Translation Droite (Slide R) - CORRIGÉE
# On force la patte avant gauche (ID 3) à reculer (valeur plus négative)
# pour libérer le passage à la patte droite.
SEQ_SLIDE_R = [
    # M1    M2    M3(Recul) M4   M5   M6   M7   M8   M9   M10  M11  M12
    [0,    -35,  -60,     -25,  8,  -60, -8,  -50,  0,  -35,  40, -25],
    [-10,  -20,  -50,     -50,  8,  -20, -8,  -30,  10, -20, -10, -50],
    [-10,  -40,  -50,     -20,  8,  -20, -8,  -30,  10, -40, -10, -20],
    [40,   -40,  -50,     -20,  8,  -20, -8,  -30, -40, -40, -10, -20],
    [60,   -20,  -60,     -30,  8,  -50, -8,  -50, -60, -20, -10, -30]
]

# Translation Gauche (Slide L) - CORRIGÉE
# On force la patte avant droite (ID 1) à reculer (valeur plus positive/grande)
# pour libérer le passage à la patte gauche.
SEQ_SLIDE_L = [
    # M1(Recul) M2   M3    M4   M5   M6   M7   M8   M9   M10  M11  M12
    [60,       -25,  0,   -35,  8,  -50, -8,  -60, -40, -25,  0,  -35],
    [50,       -50,  10,  -20,  8,  -30, -8,  -20,  10, -50, -10, -20],
    [50,       -20,  10,  -40,  8,  -30, -8,  -20,  10, -20, -10, -40],
    [50,       -20, -40,  -40,  8,  -30, -8,  -20,  10, -20,  40, -40],
    [60,       -30, -60,  -20,  8,  -50, -8,  -50,  10, -30,  60, -20]
]

# Rotation Gauche (Pivot L)
SEQ_PIVOT_L = [
    [55, -20, -55, -40, -7, -40, 7, -20, -35, -20, 35, -40],
    [70, -10, -70, -10, -22, -10, 22, -10, -20, -10, 20, -10],
    [55.29, -40, -55.29, -20, -7.29, -20, 7.29, -40, -34.71, -40, 34.71, -20],
    [40, -10, -40, -10, 8, -10, -8, -10, -50, -10, 50, -10]
]

# Rotation Droite (Pivot R)
SEQ_PIVOT_R = [
    [25, -20, -25, -40, 23, -40, -23, -20, -65, -20, 65, -40],
    [10, -10, -10, -10, 38, -10, -38, -10, -80, -10, 80, -10],
    [25.29, -40, -25.29, -20, 22.71, -20, -22.71, -40, -64.71, -40, 64.71, -20],
    [40, -10, -40, -10, 8, -10, -8, -10, -50, -10, 50, -10]
]

# --- FONCTIONS ---

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

def get_key():
    if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
        return sys.stdin.read(1)
    return None

def write_positions(groupSyncWrite, angle_list_deg):
    groupSyncWrite.clearParam()
    for i, motor_id in enumerate(DXL_IDS):
        goal_pos = deg2dxl(angle_list_deg[i])
        goal_pos = max(0, min(4095, goal_pos))
        param = [DXL_LOBYTE(DXL_LOWORD(goal_pos)), DXL_HIBYTE(DXL_LOWORD(goal_pos)), 
                 DXL_LOBYTE(DXL_HIWORD(goal_pos)), DXL_HIBYTE(DXL_HIWORD(goal_pos))]
        groupSyncWrite.addParam(motor_id, param)
    groupSyncWrite.txPacket()

# --- MAIN ---

fd = sys.stdin.fileno()
old_settings = termios.tcgetattr(fd)
tty.setcbreak(sys.stdin.fileno())

portHandler = PortHandler(DEVICENAME)
packetHandler = PacketHandler(PROTOCOL_VERSION)
groupSyncWrite = GroupSyncWrite(portHandler, packetHandler, ADDR_GOAL_POSITION, LEN_GOAL_POSITION)

if not portHandler.openPort() or not portHandler.setBaudRate(BAUDRATE):
    print("Erreur port série.")
    quit()

for mid in DXL_IDS:
    packetHandler.write1ByteTxRx(portHandler, mid, ADDR_TORQUE_ENABLE, 1)

# --- CALCUL DES SEQUENCES AVEC FACTEURS ADAPTES ---
moves = {
    'z': amplify_sequence(SEQ_MOVE_F, FACTOR_WALK),    # Avancer : Amplitude x1.5
    's': amplify_sequence(SEQ_MOVE_B, FACTOR_WALK),    # Reculer : Amplitude x1.5
    'q': amplify_sequence(SEQ_SLIDE_L, FACTOR_SLIDE),  # Gauche : Normal / Réduit
    'd': amplify_sequence(SEQ_SLIDE_R, FACTOR_SLIDE),  # Droite : Normal / Réduit
    'a': amplify_sequence(SEQ_PIVOT_L, FACTOR_TURN),   # Rotation
    'e': amplify_sequence(SEQ_PIVOT_R, FACTOR_TURN),   # Rotation
    'stop': [INIT_POSE]
}

current_mode = 'stop'
step_index = 0

print("--- HEXAPODE CONTROLE (ZQSD + AE) ---")
print(" [Z] Avancer (Rapide)")
print(" [S] Reculer (Rapide)")
print(" [Q] Pas Chassé Gauche (Optimisé)")
print(" [D] Pas Chassé Droite (Optimisé)")
print(" [A] Rotation Gauche")
print(" [E] Rotation Droite")
print(" [ESPACE] Stop")

try:
    write_positions(groupSyncWrite, INIT_POSE)
    time.sleep(1.0)
    
    while True:
        key = get_key()
        if key:
            key = key.lower()
            if key in moves:
                if current_mode != key: 
                    step_index = 0
                    time.sleep(0.1) 
                current_mode = key
                print(f"\r >> ACTION: {key.upper()}      ", end="")
            elif key == ' ' or key == 'x':
                current_mode = 'stop'
                print("\r >> STOP          ", end="")

        sequence = moves[current_mode]
        
        if current_mode == 'stop':
            write_positions(groupSyncWrite, sequence[0])
            time.sleep(0.1)
            continue

        write_positions(groupSyncWrite, sequence[step_index])
        step_index = (step_index + 1) % len(sequence)
        
        # Gestion des vitesses (Delay)
        if current_mode in ['q', 'd']:
            time.sleep(0.15) 
        elif current_mode in ['a', 'e']:
            time.sleep(0.15)
        else:
            time.sleep(0.08) # Marche rapide

except KeyboardInterrupt:
    print("\nFin.")

finally:
    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    portHandler.closePort()