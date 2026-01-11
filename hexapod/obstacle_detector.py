"""
Hexapode - Détecteur d'obstacles
Détection d'obstacles par vision pour navigation autonome
"""

import cv2
import numpy as np

from .constants import (
    OBSTACLE_MIN_AREA,
    OBSTACLE_ROI_TOP,
    OBSTACLE_ROI_BOTTOM,
    OBSTACLE_EDGE_THRESH,
    OBSTACLE_DIST_THRESHOLD_SIDE,
    OBSTACLE_DIST_THRESHOLD_CENTER,
    OBSTACLE_DIST_THRESHOLD_STOP,
    OBSTACLE_SAT_THRESHOLD,
    OBSTACLE_LAP_THRESHOLD,
    OBSTACLE_MIN_HEIGHT
)


class ObstacleDetector:
    """
    Détection d'obstacles optimisée pour l'hexapode.
    Utilise plusieurs méthodes combinées pour détecter les gros obstacles.
    """
    
    def __init__(self, min_area=None, roi_top=None, roi_bottom=None, edge_thresh=None):
        # Utiliser les valeurs par défaut des constantes si non spécifiées
        self.min_area = min_area if min_area is not None else OBSTACLE_MIN_AREA
        self.roi_top = roi_top if roi_top is not None else OBSTACLE_ROI_TOP
        self.roi_bottom = roi_bottom if roi_bottom is not None else OBSTACLE_ROI_BOTTOM
        self.edge_thresh = edge_thresh if edge_thresh is not None else OBSTACLE_EDGE_THRESH
        
        self._kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
    
    def detect(self, frame):
        """
        Détecte les obstacles dans une frame.
        
        Args:
            frame: Image BGR de la caméra
            
        Returns:
            obstacles: Liste de dictionnaires avec bbox, pos, dist, size
            danger: Niveau de danger ('OK', 'OBS', 'WARN', 'STOP')
            position: Position de l'obstacle ('LEFT', 'RIGHT', 'CENTER', 'BOTH', None)
        """
        if frame is None:
            return [], "INIT", None
        
        h, w = frame.shape[:2]
        y1 = int(h * self.roi_top)
        y2 = int(h * self.roi_bottom)
        roi = frame[y1:y2, :]
        
        # Conversion en différents espaces couleur
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        
        # Canal de saturation (objets colorés)
        saturation = hsv[:, :, 1]
        
        # Flou pour réduire le bruit
        blurred_gray = cv2.GaussianBlur(gray, (9, 9), 0)
        blurred_sat = cv2.GaussianBlur(saturation, (9, 9), 0)
        
        # Méthode 1: Seuillage sur saturation
        _, sat_thresh = cv2.threshold(blurred_sat, OBSTACLE_SAT_THRESHOLD, 255, cv2.THRESH_BINARY)
        
        # Méthode 2: Laplacien (contraste local)
        laplacian = cv2.Laplacian(blurred_gray, cv2.CV_64F)
        laplacian = np.uint8(np.absolute(laplacian))
        _, lap_thresh = cv2.threshold(laplacian, OBSTACLE_LAP_THRESHOLD, 255, cv2.THRESH_BINARY)
        
        # Méthode 3: Canny
        edges = cv2.Canny(blurred_gray, self.edge_thresh, self.edge_thresh * 2)
        
        # Combiner les méthodes
        combined = cv2.bitwise_or(sat_thresh, lap_thresh)
        combined = cv2.bitwise_or(combined, edges)
        
        # Morphologie
        kernel_large = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
        kernel_medium = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, kernel_large)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, kernel_medium)
        combined = cv2.dilate(combined, kernel_medium, iterations=1)
        
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
            
            # Filtrer formes trop plates
            aspect_ratio = bw / max(bh, 1)
            if aspect_ratio > 8:
                continue
            
            # Hauteur minimale
            if bh < OBSTACLE_MIN_HEIGHT:
                continue
            
            y_global = y + y1
            cx = x + bw // 2
            
            # Distance (bas de l'objet)
            dist = (y + bh) / (y2 - y1)
            
            # Position (Gauche/Centre/Droite)
            if cx < third_w:
                pos = "G"
                if dist > OBSTACLE_DIST_THRESHOLD_SIDE:
                    has_left = True
            elif cx > 2 * third_w:
                pos = "D"
                if dist > OBSTACLE_DIST_THRESHOLD_SIDE:
                    has_right = True
            else:
                pos = "C"
                if dist > OBSTACLE_DIST_THRESHOLD_CENTER:
                    has_center = True
                    closest_center_dist = max(closest_center_dist, dist)
            
            # Taille
            size = "S" if area < 5000 else ("M" if area < 15000 else "L")
            
            obstacles.append({
                'bbox': (x, y_global, bw, bh),
                'pos': pos,
                'dist': dist,
                'size': size
            })
        
        # Déterminer niveau de danger
        if has_center and closest_center_dist > OBSTACLE_DIST_THRESHOLD_STOP:
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
        """Dessine les obstacles et informations sur la frame"""
        if frame is None:
            return frame
        
        h, w = frame.shape[:2]
        y1 = int(h * self.roi_top)
        y2 = int(h * self.roi_bottom)
        
        # Zone ROI
        cv2.rectangle(frame, (0, y1), (w-1, y2), (60, 60, 60), 1)
        
        # Lignes de séparation G/C/D
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
        
        # Couleurs selon danger
        colors = {
            "OK": (0, 255, 0),
            "OBS": (0, 220, 220),
            "WARN": (0, 140, 255),
            "STOP": (0, 0, 255)
        }
        color = colors.get(danger, (128, 128, 128))
        
        # Dessiner obstacles
        for o in obstacles:
            x, y, bw, bh = o['bbox']
            cv2.rectangle(frame, (x, y), (x+bw, y+bh), color, 2)
            cv2.putText(frame, f"{o['size']}{o['pos']}", (x, y-3),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)
        
        # Indicateur danger
        cv2.rectangle(frame, (w-60, 5), (w-5, 28), color, -1)
        cv2.putText(frame, danger, (w-55, 22),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        return frame
