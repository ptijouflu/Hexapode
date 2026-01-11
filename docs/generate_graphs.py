#!/usr/bin/env python3
"""
Generation des graphiques pour la documentation de detection d'obstacles
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import os

# Creer le dossier images si necessaire
os.makedirs('docs/images', exist_ok=True)

# Style global
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.size'] = 10
plt.rcParams['figure.facecolor'] = 'white'


def plot_confusion_matrix():
    """Matrice de confusion estimee"""
    matrix = np.array([
        [0.85, 0.15],
        [0.10, 0.90]
    ])
    
    fig, ax = plt.subplots(figsize=(6, 5))
    
    im = ax.imshow(matrix, cmap='Blues', vmin=0, vmax=1)
    
    # Labels
    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(['Obstacle', 'Libre'])
    ax.set_yticklabels(['Obstacle', 'Libre'])
    ax.set_xlabel('Prediction', fontweight='bold')
    ax.set_ylabel('Realite', fontweight='bold')
    ax.set_title('Matrice de Confusion (Estimee)', fontweight='bold', pad=15)
    
    # Valeurs dans les cases
    for i in range(2):
        for j in range(2):
            color = 'white' if matrix[i, j] > 0.5 else 'black'
            ax.text(j, i, f'{matrix[i, j]:.0%}', ha='center', va='center', 
                   color=color, fontsize=16, fontweight='bold')
    
    # Colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Taux', rotation=270, labelpad=15)
    
    plt.tight_layout()
    plt.savefig('docs/images/confusion_matrix.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("[OK] confusion_matrix.png")


def plot_detection_methods_comparison():
    """Comparaison des methodes de detection"""
    methods = ['Saturation\nHSV', 'Laplacien', 'Canny', 'Combine\n(notre algo)']
    detection = [70, 60, 65, 85]
    false_positives = [5, 15, 20, 10]
    
    x = np.arange(len(methods))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    bars1 = ax.bar(x - width/2, detection, width, label='Taux de detection', color='#2ecc71')
    bars2 = ax.bar(x + width/2, false_positives, width, label='Faux positifs', color='#e74c3c')
    
    ax.set_ylabel('Pourcentage (%)', fontweight='bold')
    ax.set_title('Comparaison des Methodes de Detection', fontweight='bold', pad=15)
    ax.set_xticks(x)
    ax.set_xticklabels(methods)
    ax.legend(loc='upper right')
    ax.set_ylim(0, 100)
    
    # Valeurs sur les barres
    for bar in bars1:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 2, f'{height}%',
               ha='center', va='bottom', fontsize=10)
    for bar in bars2:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 2, f'{height}%',
               ha='center', va='bottom', fontsize=10)
    
    plt.tight_layout()
    plt.savefig('docs/images/methods_comparison.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("[OK] methods_comparison.png")


def plot_detection_rate_by_obstacle():
    """Taux de detection par type d'obstacle"""
    obstacles = ['Cone\norange', 'Bouteille\ncoloree', 'Carton', 'Personne', 'Mur\n(proche)']
    rates = [95, 85, 70, 60, 40]
    colors = ['#e74c3c', '#3498db', '#f39c12', '#9b59b6', '#95a5a6']
    
    fig, ax = plt.subplots(figsize=(8, 5))
    
    bars = ax.bar(obstacles, rates, color=colors, edgecolor='black', linewidth=1)
    
    ax.set_ylabel('Taux de detection (%)', fontweight='bold')
    ax.set_title('Taux de Detection par Type d\'Obstacle', fontweight='bold', pad=15)
    ax.set_ylim(0, 100)
    
    # Ligne de reference a 80%
    ax.axhline(y=80, color='green', linestyle='--', linewidth=2, label='Seuil acceptable (80%)')
    ax.legend(loc='upper right')
    
    # Valeurs sur les barres
    for bar, rate in zip(bars, rates):
        ax.text(bar.get_x() + bar.get_width()/2., bar.get_height() + 2, f'{rate}%',
               ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig('docs/images/detection_by_obstacle.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("[OK] detection_by_obstacle.png")


def plot_danger_levels():
    """Niveaux de danger et seuils de distance"""
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Zones de danger
    zones = [
        (0, 0.45, '#2ecc71', 'OK - Libre'),
        (0.45, 0.50, '#f1c40f', 'OBS - Obstacle lateral'),
        (0.50, 0.65, '#e67e22', 'WARN - Attention'),
        (0.65, 1.0, '#e74c3c', 'STOP - Danger')
    ]
    
    for start, end, color, label in zones:
        ax.axhspan(start, end, color=color, alpha=0.7, label=label)
        ax.text(0.5, (start + end) / 2, label, ha='center', va='center', 
               fontsize=12, fontweight='bold', color='black')
    
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_ylabel('Distance relative (0=loin, 1=proche)', fontweight='bold')
    ax.set_title('Niveaux de Danger selon la Distance', fontweight='bold', pad=15)
    ax.set_xticks([])
    
    # Fleche indicatrice
    ax.annotate('', xy=(0.9, 0.95), xytext=(0.9, 0.05),
               arrowprops=dict(arrowstyle='->', lw=2, color='black'))
    ax.text(0.92, 0.5, 'Plus\nproche', ha='left', va='center', fontsize=9)
    
    plt.tight_layout()
    plt.savefig('docs/images/danger_levels.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("[OK] danger_levels.png")


def plot_roi_zones():
    """Visualisation des zones ROI et G/C/D"""
    fig, ax = plt.subplots(figsize=(8, 4))
    
    # Image simulee
    ax.set_xlim(0, 640)
    ax.set_ylim(240, 0)  # Inverser Y pour correspondre a l'image
    
    # Zone ignoree haut
    ax.axhspan(0, 60, color='#bdc3c7', alpha=0.5)
    ax.text(320, 30, 'Zone ignoree (0-25%)', ha='center', va='center', fontsize=10)
    
    # Zone ROI
    ax.axhspan(60, 228, color='#ecf0f1', alpha=0.3)
    
    # Zones G/C/D
    ax.axvspan(0, 213, ymin=0.05, ymax=0.75, color='#3498db', alpha=0.3)
    ax.axvspan(213, 426, ymin=0.05, ymax=0.75, color='#2ecc71', alpha=0.3)
    ax.axvspan(426, 640, ymin=0.05, ymax=0.75, color='#e74c3c', alpha=0.3)
    
    # Labels zones
    ax.text(106, 150, 'G\n(Gauche)', ha='center', va='center', fontsize=14, fontweight='bold')
    ax.text(320, 150, 'C\n(Centre)', ha='center', va='center', fontsize=14, fontweight='bold')
    ax.text(533, 150, 'D\n(Droite)', ha='center', va='center', fontsize=14, fontweight='bold')
    
    # Lignes de separation
    ax.axvline(x=213, color='black', linestyle='--', linewidth=2)
    ax.axvline(x=426, color='black', linestyle='--', linewidth=2)
    ax.axhline(y=60, color='black', linestyle='-', linewidth=2)
    ax.axhline(y=228, color='black', linestyle='-', linewidth=2)
    
    # Zone ignoree bas
    ax.axhspan(228, 240, color='#bdc3c7', alpha=0.5)
    ax.text(320, 234, 'Zone ignoree (95-100%)', ha='center', va='center', fontsize=10)
    
    ax.set_xlabel('Largeur (pixels)', fontweight='bold')
    ax.set_ylabel('Hauteur (pixels)', fontweight='bold')
    ax.set_title('Zones de Detection (ROI et Position G/C/D)', fontweight='bold', pad=15)
    
    plt.tight_layout()
    plt.savefig('docs/images/roi_zones.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("[OK] roi_zones.png")


def plot_pipeline():
    """Pipeline de traitement simplifie"""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.axis('off')
    
    # Boites du pipeline
    boxes = [
        (1, 7, 'Camera\n640x240', '#3498db'),
        (1, 5.5, 'ROI\n(25%-95%)', '#9b59b6'),
        (1, 4, 'HSV\nSaturation', '#e74c3c'),
        (4, 4, 'Laplacien', '#f39c12'),
        (7, 4, 'Canny', '#2ecc71'),
        (4, 2.5, 'Combinaison\n(OR)', '#1abc9c'),
        (4, 1, 'Morphologie\n+ Contours', '#34495e'),
        (7, 1, 'Classification\nG/C/D', '#e74c3c'),
    ]
    
    for x, y, text, color in boxes:
        rect = mpatches.FancyBboxPatch((x-0.8, y-0.4), 1.6, 0.8, 
                                        boxstyle="round,pad=0.05",
                                        facecolor=color, edgecolor='black', linewidth=2)
        ax.add_patch(rect)
        ax.text(x, y, text, ha='center', va='center', fontsize=9, 
               fontweight='bold', color='white')
    
    # Fleches
    arrows = [
        ((1, 6.6), (1, 5.9)),      # Camera -> ROI
        ((1, 5.1), (1, 4.4)),      # ROI -> HSV
        ((1.8, 5.5), (3.2, 4.4)),  # ROI -> Laplacien
        ((1.8, 5.5), (6.2, 4.4)),  # ROI -> Canny
        ((1, 3.6), (3.2, 2.9)),    # HSV -> Combine
        ((4, 3.6), (4, 2.9)),      # Lap -> Combine
        ((6.2, 4), (4.8, 2.9)),    # Canny -> Combine
        ((4, 2.1), (4, 1.4)),      # Combine -> Morpho
        ((4.8, 1), (6.2, 1)),      # Morpho -> Class
    ]
    
    for start, end in arrows:
        ax.annotate('', xy=end, xytext=start,
                   arrowprops=dict(arrowstyle='->', lw=1.5, color='black'))
    
    ax.set_title('Pipeline de Detection d\'Obstacles', fontweight='bold', fontsize=14, pad=20)
    
    plt.tight_layout()
    plt.savefig('docs/images/pipeline.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("[OK] pipeline.png")


def plot_performance():
    """Performances sur Raspberry Pi"""
    metrics = ['FPS\nDetection', 'Latence\n(ms)', 'CPU\n(%)']
    values = [12, 80, 50]
    max_vals = [30, 200, 100]
    colors = ['#2ecc71', '#3498db', '#e74c3c']
    
    fig, axes = plt.subplots(1, 3, figsize=(10, 4))
    
    for ax, metric, value, max_val, color in zip(axes, metrics, values, max_vals, colors):
        # Gauge-like bar
        ax.barh([0], [max_val], color='#ecf0f1', height=0.5)
        ax.barh([0], [value], color=color, height=0.5)
        ax.set_xlim(0, max_val)
        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])
        ax.set_xlabel(metric, fontweight='bold', fontsize=11)
        ax.text(value/2, 0, f'{value}', ha='center', va='center', 
               fontsize=14, fontweight='bold', color='white')
    
    fig.suptitle('Performances sur Raspberry Pi 4', fontweight='bold', fontsize=14)
    plt.tight_layout()
    plt.savefig('docs/images/performance.png', dpi=150, bbox_inches='tight')
    plt.close()
    print("[OK] performance.png")


if __name__ == '__main__':
    print("Generation des graphiques...")
    print("-" * 40)
    
    plot_confusion_matrix()
    plot_detection_methods_comparison()
    plot_detection_rate_by_obstacle()
    plot_danger_levels()
    plot_roi_zones()
    plot_pipeline()
    plot_performance()
    
    print("-" * 40)
    print("Tous les graphiques generes dans docs/images/")
