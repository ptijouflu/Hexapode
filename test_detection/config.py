#!/usr/bin/env python3
"""
Configuration personnalisée pour le test de détection d'obstacles
Modifiez ces paramètres pour ajuster la sensibilité de détection
"""

# Paramètres de la caméra
CAMERA_CONFIG = {
    'width': 640,       # Largeur de l'image
    'height': 480,      # Hauteur de l'image
    'fps': 15,          # Images par seconde
}

# Paramètres de détection d'obstacles
DETECTION_CONFIG = {
    'min_area': 800,           # Aire minimale des obstacles (pixels²)
    'roi_top': 0.3,            # Début de la zone d'intérêt (% de hauteur)
    'roi_bottom': 0.9,         # Fin de la zone d'intérêt (% de hauteur)
    'edge_thresh': 50,         # Seuil pour détection de contours Canny
}

# Paramètres de sauvegarde
SAVE_CONFIG = {
    'photos_dir': 'photos_obstacles',     # Dossier de sauvegarde
    'save_original': False,               # Sauver aussi l'image originale
    'jpeg_quality': 90,                   # Qualité JPEG (0-100)
}

# Paramètres d'affichage
DISPLAY_CONFIG = {
    'show_roi_lines': True,        # Afficher les lignes de la zone d'intérêt
    'show_thirds': True,           # Afficher les divisions tiers
    'show_obstacle_numbers': True, # Numéroter les obstacles
    'danger_frame_thickness': 3,   # Épaisseur du cadre de danger
    'obstacle_frame_thickness': 2, # Épaisseur du cadre des obstacles
}

# Couleurs (BGR format)
COLORS = {
    'danger': {
        'OK': (0, 255, 0),      # Vert
        'OBS': (0, 255, 255),   # Jaune
        'WARN': (0, 165, 255),  # Orange
        'STOP': (0, 0, 255),    # Rouge
        'INIT': (128, 128, 128) # Gris
    },
    'position': {
        'G': (255, 0, 0),       # Bleu (Gauche)
        'C': (0, 0, 255),       # Rouge (Centre)
        'D': (0, 255, 0),       # Vert (Droite)
    },
    'roi_lines': (255, 255, 0),    # Cyan pour les lignes ROI
    'text_bg': (0, 0, 0),          # Noir pour fond de texte
    'text_fg': (255, 255, 255),    # Blanc pour texte
}

# Messages personnalisés
MESSAGES = {
    'ready': "Prêt! Appuyez sur ESPACE pour prendre une photo...",
    'capturing': "Prise de photo en cours...",
    'success': "Photo avec détection sauvegardée!",
    'error': "Erreur lors de la prise de photo",
    'quit': "Au revoir!",
}

def get_camera_config():
    """Retourne la configuration de la caméra"""
    return CAMERA_CONFIG.copy()

def get_detection_config():
    """Retourne la configuration de détection"""
    return DETECTION_CONFIG.copy()

def get_save_config():
    """Retourne la configuration de sauvegarde"""
    return SAVE_CONFIG.copy()

def get_display_config():
    """Retourne la configuration d'affichage"""
    return DISPLAY_CONFIG.copy()

def get_colors():
    """Retourne les couleurs configurées"""
    return COLORS.copy()

def get_messages():
    """Retourne les messages configurés"""
    return MESSAGES.copy()