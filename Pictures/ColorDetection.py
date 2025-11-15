import cv2  # Bibliothèque OpenCV pour le traitement d'image
import numpy as np  # Bibliothèque NumPy pour la gestion des matrices et tableaux
import os  # Module pour la gestion des fichiers (suppression d'images après analyse)

class ColorDetection:
    """
    Cette classe permet de détecter les couleurs rouge et verte dans une image.
    L'image est convertie en espace de couleur HSV pour une meilleure détection.
    """

    @staticmethod
    def detecter_couleur(image):
        """
        Détecte la présence de rouge et de vert dans une image en utilisant les masques HSV.

        :param image: Image chargée sous forme de matrice NumPy (BGR).
        :return: (rouge_detecte, vert_detecte) - Booléens indiquant la présence des couleurs.
        """

        # Conversion de l'image du format BGR (par défaut OpenCV) vers HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Définition des plages de couleur rouge en HSV (teinte, saturation, valeur)
        rouge_bas = np.array([0, 150, 150])  # Borne inférieure pour le rouge
        rouge_haut = np.array([10, 255, 255])  # Borne supérieure pour le rouge

        # Définition de la plage de couleur verte en HSV
        vert_bas = np.array([40, 100, 100])  # Borne inférieure pour le vert
        vert_haut = np.array([80, 255, 255])  # Borne supérieure pour le vert

        # Création des masques de détection de couleur
        masque_rouge = cv2.inRange(hsv, rouge_bas, rouge_haut)  # Masque des zones rouges
        masque_vert = cv2.inRange(hsv, vert_bas, vert_haut)  # Masque des zones vertes

        # Détection des contours des objets détectés dans les masques
        contours_rouge, _ = cv2.findContours(masque_rouge, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        contours_vert, _ = cv2.findContours(masque_vert, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # Vérification de la présence d'objets significatifs
        # On considère qu'une couleur est détectée si au moins un objet dépasse une certaine surface
        rouge_detecte = any(cv2.contourArea(contour) > 1500 for contour in contours_rouge)
        vert_detecte = any(cv2.contourArea(contour) > 1000 for contour in contours_vert)

        return rouge_detecte, vert_detecte

    @staticmethod
    def analyser_photo(chemin_photo):
        """
        Analyse une photo pour détecter les couleurs rouge et verte.
        Supprime l'image après analyse pour économiser de l'espace disque.

        :param chemin_photo: Chemin du fichier image à analyser.
        :return: (rouge_detecte, vert_detecte) - Booléens indiquant si une couleur est détectée.
        """

        # Chargement de l'image depuis le disque
        image = cv2.imread(chemin_photo)

        # Vérification si l'image a bien été chargée
        if image is None:
            print(f"[ERREUR] Impossible de lire la photo : {chemin_photo}")
            return None, None  # Retourne None si l'image est invalide

        # Détection des couleurs dans l'image
        rouge_detecte, vert_detecte = ColorDetection.detecter_couleur(image)

        # Affichage des résultats
        if rouge_detecte:
            print("[INFO] Rouge détecté !")
        if vert_detecte:
            print("[INFO] Vert détecté !")
        if not rouge_detecte and not vert_detecte:
            print("[INFO] Aucune couleur détectée.")

        # Suppression de l'image après analyse pour éviter l'encombrement
        # ColorDetection.supprimer_photo(chemin_photo)  # Décommenter si nécessaire

        return rouge_detecte, vert_detecte

    @staticmethod
    def supprimer_photo(chemin_photo):
        """
        Supprime une photo après analyse pour libérer de l'espace disque.

        :param chemin_photo: Chemin de l'image à supprimer.
        """
        try:
            os.remove(chemin_photo)  # Suppression du fichier image
            print(f"[INFO] Photo supprimée : {chemin_photo}")
        except OSError as e:
            print(f"[ERREUR] Impossible de supprimer {chemin_photo}: {e}")
