import time  # Module pour gérer les temporisations
import threading  # Module pour créer et gérer des threads
import os  # Module pour interagir avec le système de fichiers
from controller import Controller  # Importation du contrôleur qui gère les mouvements du robot
from movementbank import MovementBank  # Importation de la classe qui stocke les mouvements
from movementimport import import_all  # Fonction qui importe tous les mouvements dans MovementBank
from Pictures.take_pictures import CameraManager  # Importation des modules pour la gestion de la caméra

# Définition d'un thread pour la suppression automatique des anciennes photos
class PhotoDeletionThread(threading.Thread):
    def __init__(self, photo_dir, buffer_size):
        """
        Initialise le thread qui va surveiller et supprimer les photos excédentaires.
        
        :param photo_dir: Répertoire où les photos sont stockées
        :param buffer_size: Nombre maximal de photos à conserver
        """
        super().__init__(daemon=True)  # Le thread s'arrêtera automatiquement à la fermeture du programme
        self.photo_dir = photo_dir  # Stocke le chemin du répertoire contenant les photos
        self.buffer_size = buffer_size  # Stocke le nombre maximal de photos à conserver

    def run(self):
        """
        Exécute la logique de suppression des photos en continu.
        Supprime les photos les plus anciennes si le nombre dépasse le buffer_size.
        """
        while True:
            try:
                # Récupère tous les fichiers .jpg dans le dossier spécifié et les trie par date de modification (du plus ancien au plus récent)
                photos = sorted(
                    [os.path.join(self.photo_dir, f) for f in os.listdir(self.photo_dir) if f.endswith(".jpg")],
                    key=os.path.getmtime
                )
                # Vérifie si le nombre de photos dépasse la limite autorisée
                if len(photos) > self.buffer_size:
                    # Supprime les photos les plus anciennes pour ne conserver que le buffer_size le plus récent
                    for photo in photos[:-self.buffer_size]:
                        os.remove(photo)  # Supprime le fichier
                        print(f"[INFO] Photo supprimée : {photo}")  # Message de confirmation
            except Exception as e:
                print(f"[ERROR] Erreur lors de la suppression des photos : {e}")  # Affiche une erreur en cas de problème
            time.sleep(0.5)  # Attente avant la prochaine vérification pour ne pas surcharger le système

# Exécution du programme principal
if __name__ == "__main__":
    # Initialisation des modules nécessaires
    try:
        movement_bank = MovementBank()  # Création d'une instance pour gérer les mouvements du robot
        import_all(movement_bank)  # Importation des mouvements disponibles dans la banque de mouvements
        basic_set = movement_bank.get_movement_set("basic movements")  # Récupération du jeu de mouvements de base
        controller = Controller()  # Création d'une instance du contrôleur du robot
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'initialisation des modules : {e}")  # Affiche un message d'erreur si l'initialisation échoue
        exit(1)  # Arrête le programme en cas d'erreur

    # Définition des paramètres pour la gestion des photos
    PHOTO_DIR = "./Pictures/photos"  # Chemin du dossier où les photos seront enregistrées
    BUFFER_SIZE = 1  # Nombre maximal de photos conservées (pour éviter de saturer le stockage)

    try:
        # Initialisation du gestionnaire de caméra
        camera_manager = CameraManager(PHOTO_DIR, BUFFER_SIZE)
        # Création et démarrage du thread pour la suppression des anciennes photos
        deletion_thread = PhotoDeletionThread(PHOTO_DIR, BUFFER_SIZE)
        deletion_thread.start()  # Lancement du thread en arrière-plan
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'initialisation de CameraManager ou du thread : {e}")  # Affiche un message d'erreur si l'initialisation échoue
        exit(1)  # Arrête le programme en cas d'erreur

    # Capture d'une première photo et détection de la couleur présente dans l'image
    try:
        camera_manager.capture_photo()  # Capture une image avec la caméra
        detected_color = camera_manager.process_photos()  # Analyse l'image pour détecter une couleur dominante
    except Exception as e:
        print(f"[ERROR] Erreur lors de la capture ou de la détection de couleur : {e}")  # Affiche un message d'erreur en cas d'échec
        exit(1)  # Arrête le programme en cas d'erreur

    # Boucle principale du programme (fonctionnement en continu)
    while True:
        try:
            print("[INFO] Boucle principale en cours...")  # Affiche un message pour indiquer que la boucle fonctionne

            # Détermine quel mouvement exécuter en fonction de la couleur détectée
            if detected_color == "red":
                movement = basic_set.get_movement("right")  # Si la couleur est rouge, tourner à droite
                controller.execute_movement(movement)  # Exécuter le mouvement
            elif detected_color == "green":
                movement = basic_set.get_movement("left")  # Si la couleur est verte, tourner à gauche
                controller.execute_movement(movement)  # Exécuter le mouvement
            elif detected_color == "none":
                movement = basic_set.get_movement("forward")  # Si aucune couleur n'est détectée, avancer
                controller.execute_movement(movement)  # Exécuter le mouvement
            else:
                movement = basic_set.get_movement("forward")  # Si la couleur n'est pas reconnue, avancer par défaut
                controller.execute_movement(movement)  # Exécuter le mouvement

            # Capture une nouvelle photo pour analyser la couleur suivante
            camera_manager.capture_photo()
            detected_color = camera_manager.process_photos()  # Mise à jour de la couleur détectée

            # Délai court pour éviter une surcharge du système et améliorer la réactivité du programme
            time.sleep(0.05)  # Attente de 50 ms avant la prochaine itération de la boucle

        except KeyboardInterrupt:
            print("[INFO] Arrêt manuel détecté.")  # Message indiquant que l'utilisateur a interrompu le programme (Ctrl + C)
            break  # Sort de la boucle et termine le programme proprement
        except Exception as e:
            print(f"[ERROR] Une erreur est survenue dans la boucle principale : {e}")  # Affiche un message d'erreur si un problème survient

    print("[INFO] Fin du programme.")  # Message indiquant que le programme s'est terminé correctement
