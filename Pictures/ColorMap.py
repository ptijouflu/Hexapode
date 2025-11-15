import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import hsv_to_rgb
from PIL import Image

# Création de la carte de couleurs en HSV (valeurs normalisées entre 0 et 1)
hue = np.linspace(0, 1, 360).reshape(1, -1)  # De 0° à 360° pour la teinte
saturation = np.ones_like(hue)  # Saturation max (1)
value = np.ones_like(hue)  # Luminosité max (1)

# Stack pour former une image HSV complète (H, S, V)
hsv_map = np.dstack((hue, saturation, value))

# Convertir HSV → RGB pour l'affichage
rgb_map = hsv_to_rgb(hsv_map)

# Affichage avec Matplotlib
fig, ax = plt.subplots(figsize=(10, 2))
ax.imshow(rgb_map, aspect="auto")
ax.set_title("Carte des couleurs HSV - Cliquez pour obtenir la couleur")

# Fonction pour récupérer la couleur lorsqu'on clique sur l'image
def on_click(event):
    if event.xdata is not None and event.ydata is not None:
        x = int(event.xdata)  # Position x (correspond à la teinte)
        hue_value = hue[0, x]  # Récupérer la teinte en HSV
        
        # Convertir en RGB (Pillow utilise [0, 255] au lieu de [0, 1])
        rgb_color = hsv_to_rgb([[hue_value, 1, 1]])[0] * 255
        rgb_color = tuple(map(int, rgb_color))  # Convertir en entiers
        
        print(f"Teinte (H): {int(hue_value * 360)}° | RGB: {rgb_color}")

# Ajouter l'événement de clic
fig.canvas.mpl_connect('button_press_event', on_click)

# Afficher la carte
plt.show()
