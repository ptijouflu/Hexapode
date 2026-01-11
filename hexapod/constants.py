"""
Hexapode - Constantes partagées
Configuration des moteurs, ports et paramètres globaux
"""

# ============================================================================
# CONFIGURATION PORT SÉRIE
# ============================================================================

DEVICENAME = '/dev/ttyUSB0'
BAUDRATE = 1000000
PROTOCOL_VERSION = 2.0

# ============================================================================
# CONFIGURATION MOTEURS DYNAMIXEL
# ============================================================================

# IDs des 12 moteurs (6 pattes x 2 articulations)
DXL_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

# Adresses mémoire (XL430-W250)
ADDR_TORQUE_ENABLE = 64
ADDR_GOAL_POSITION = 116
LEN_GOAL_POSITION = 4

# ============================================================================
# FACTEURS D'AMPLITUDE DES MOUVEMENTS
# ============================================================================

FACTOR_WALK = 2       # Marche avant/arrière (amplitude doublée)
FACTOR_SLIDE = 1.2    # Translation latérale
FACTOR_TURN = 1.0     # Rotation

# ============================================================================
# CONFIGURATION SERVEUR HTTP (streaming vidéo)
# ============================================================================

HTTP_PORT = 8080

# ============================================================================
# CONFIGURATION CAMÉRA
# ============================================================================

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 240
CAMERA_FPS = 10

# ============================================================================
# CONFIGURATION DÉTECTION D'OBSTACLES
# ============================================================================

# Surface minimale pour détecter un obstacle (en pixels²)
OBSTACLE_MIN_AREA = 4000

# Zone de détection dans l'image (ratio de hauteur)
OBSTACLE_ROI_TOP = 0.25      # Début de la ROI (25% du haut)
OBSTACLE_ROI_BOTTOM = 0.95   # Fin de la ROI (95% du haut)

# Seuil de détection de contours Canny
OBSTACLE_EDGE_THRESH = 60

# Seuils de distance pour déclencher les alertes
OBSTACLE_DIST_THRESHOLD_SIDE = 0.45    # Obstacles latéraux
OBSTACLE_DIST_THRESHOLD_CENTER = 0.50  # Obstacles centraux
OBSTACLE_DIST_THRESHOLD_STOP = 0.65    # Distance critique (STOP)

# Seuils pour le traitement d'image
OBSTACLE_SAT_THRESHOLD = 70    # Seuil de saturation
OBSTACLE_LAP_THRESHOLD = 25    # Seuil Laplacien
OBSTACLE_MIN_HEIGHT = 35       # Hauteur minimale d'un obstacle (pixels)
