import numpy as np  # Bibliothèque pour les calculs numériques
import matplotlib.pyplot as plt  # Bibliothèque pour la visualisation
from colorsys import hsv_to_rgb  # Fonction pour convertir les couleurs HSV en RGB

# Définition des plages de couleurs en HSV (Teinte, Saturation, Valeur)
color_ranges = {
    # "Rouge 1 (0-10°)": ([Teinte min, Saturation min, Valeur min], [Teinte max, Saturation max, Valeur max])
    "Rouge 1 (0-10°)": ([0, 250, 250], [10, 200, 200]),  # Rouge (première plage)
    "Vert 2 (170-180°)": ([170, 150, 150], [180, 250, 250]),  # Vert proche du cyan
    "Vert (40-80°)": ([40, 100, 100], [70, 200, 255])  # Vert classique
}

def hsv_to_rgb_np(h, s, v):
    """ 
    Convertit des valeurs HSV (0-360, 0-255, 0-255) en RGB (0-1) pour matplotlib.
    
    :param h: Teinte (0-360 degrés)
    :param s: Saturation (0-255)
    :param v: Valeur (0-255)
    :return: Tuple (r, g, b) avec des valeurs entre 0 et 1
    """
    h, s, v = h / 360, s / 255, v / 255  # Normalisation des valeurs pour hsv_to_rgb
    return hsv_to_rgb(h, s, v)  # Conversion en RGB

# Création des bandes de couleurs
fig, ax = plt.subplots(len(color_ranges), 1, figsize=(8, 3))  # Création d'une figure avec plusieurs sous-graphiques

# Parcours des différentes plages de couleurs définies
for i, (label, (lower, upper)) in enumerate(color_ranges.items()):
    h_values = np.linspace(lower[0], upper[0], 100)  # Génération d'une gamme de teintes entre la borne inférieure et supérieure
    s_value, v_value = lower[1], lower[2]  # Saturation et luminosité fixes (prises depuis la borne inférieure)

    # Conversion de chaque valeur de teinte en RGB
    rgb_colors = [hsv_to_rgb_np(h, s_value, v_value) for h in h_values]  
    rgb_strip = np.array([rgb_colors])  # Création d'une "image" de 1 pixel de hauteur et 100 pixels de largeur

    # Affichage de la bande colorée correspondante
    ax[i].imshow(rgb_strip, aspect='auto')  # Affichage en mode automatique
    ax[i].set_title(label)  # Ajout du titre correspondant à la plage de couleur
    ax[i].axis("off")  # Suppression des axes pour une meilleure lisibilité

# Ajustement automatique des espacements entre les sous-graphiques
plt.tight_layout()

# Affichage final
plt.show()
