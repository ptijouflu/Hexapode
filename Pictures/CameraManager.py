import os  # Module pour la gestion des fichiers et des répertoires
import time  # Module pour la gestion du temps et des timestamps
from collections import deque  # Structure de données pour gérer un buffer circulaire
from Pictures.ColorDetection import ColorDetection  # Import de la classe pour la détection de couleur

class CameraManager:
    """
    Gère la capture de photos et leur traitement pour la détection de couleur.
    Les photos sont stockées temporairement dans un buffer circulaire.
    """

    def __init__(self, photo_dir, buffer_size=10):
        """
        Initialise le gestionnaire de caméra.

        :param photo_dir: Chemin du répertoire où les photos seront stockées.
        :param buffer_size: Nombre maximum de photos stockées dans le buffer.
        """
        self.photo_dir = photo_dir  # Dossier de stockage des photos
        self.photo_buffer = deque(maxlen=buffer_size)  # Buffer circulaire pour limiter le stockage
        self.ensure_directory_exists()  # Vérifie que le répertoire existe, sinon le crée

    def ensure_directory_exists(self):
        """
        Vérifie si le répertoire photo existe, sinon il le crée.
        """
        if not os.path.exists(self.photo_dir):  # Vérifie si le dossier existe
            os.makedirs(self.photo_dir)  # Crée le dossier s'il n'existe pas

    def capture_photo(self):
        """
        Capture une photo et l'ajoute au buffer.

        :return: Chemin du fichier photo capturé.
        """
        # Génère un nom de fichier avec timestamp pour éviter les conflits
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        photo_path = os.path.join(self.photo_dir, f"photo_{timestamp}.jpg")

        # Affiche une information sur la capture
        print(f"[INFO] Capture de la photo : {photo_path}")

        # Commande système pour capturer une image avec libcamera
        os.system(f"libcamera-still -o {photo_path} -t 1 ")

        # Ajoute la photo capturée au buffer circulaire
        self.photo_buffer.append(photo_path)

        return photo_path  # Retourne le chemin de la photo capturée

    def process_photos(self):
        """
        Analyse les photos présentes dans le buffer pour détecter les couleurs.
        """
        # Parcours du buffer et analyse de chaque photo avec la classe ColorDetection
        for photo in list(self.photo_buffer):
            ColorDetection.analyze_photos(photo)

    def run(self, interval=0.1):
        """
        Lance la capture et l'analyse des photos en boucle.

        :param interval: Intervalle de temps (en secondes) entre chaque capture.
        """
        while True:
            photo_path = self.capture_photo()  # Capture une nouvelle photo
            self.process_photos()  # Analyse la photo capturée

            # Pause avant la prochaine capture pour éviter une surcharge du système
            time.sleep(interval)
