import time
import cv2
import numpy as np

# Détection des couleurs rouge et vert
def detect_color(image):
    hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

    lower_red = np.array([0, 100, 100])
    upper_red = np.array([10, 255, 255])
    lower_green = np.array([40, 100, 100])
    upper_green = np.array([80, 255, 255])

    mask_red = cv2.inRange(hsv, lower_red, upper_red)
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    contours_red, _ = cv2.findContours(
        mask_red, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    contours_green, _ = cv2.findContours(
        mask_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    red_detected = any(cv2.contourArea(contour) > 1000 for contour in contours_red)
    green_detected = any(cv2.contourArea(contour) > 1000 for contour in contours_green)

    return red_detected, green_detected, mask_red, mask_green

def initialize_camera(video_file=None):
    print("[INFO] Initialisation de la caméra ou de la vidéo...")
    
    if video_file:
        cap = cv2.VideoCapture(video_file)  # Charger une vidéo depuis le chemin donné
        if not cap.isOpened():
            print(f"[ERREUR] Impossible de lire la vidéo : {video_file}")
            return None
    else:
        cap = cv2.VideoCapture(0, cv2.CAP_V4L2)  # Utilise V4L2 pour la caméra réelle
        if not cap.isOpened():
            print("[ERREUR] Impossible d'accéder à la caméra.")
            return None

        # Configurer la résolution pour une caméra réelle
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)

    # Vérifier les propriétés de la source
    print("[DEBUG] Propriétés de la source :")
    print(f"Largeur : {cap.get(cv2.CAP_PROP_FRAME_WIDTH)}")
    print(f"Hauteur : {cap.get(cv2.CAP_PROP_FRAME_HEIGHT)}")
    print(f"FPS : {cap.get(cv2.CAP_PROP_FPS)}")

    print("[INFO] Source initialisée avec succès.")
    return cap

def main():
    video_file = "/home/aem/Desktop/rouge.mp4"  # Chemin de la vidéo convertie
    cap = initialize_camera(video_file)
    if cap is None:
        return

    try:
        while True:
            print("[INFO] Lecture d'une image de la source...")
            ret, frame = cap.read()

            if not ret:
                print("[INFO] Fin du flux ou erreur de lecture.")
                break

            print("[INFO] Image capturée. Détection des couleurs...")
            red_detected, green_detected, _, _ = detect_color(frame)

            if red_detected:
                print("[INFO] Rouge détecté!")
                cv2.putText(frame, "Red Detected", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            if green_detected:
                print("[INFO] Vert détecté!")
                cv2.putText(frame, "Green Detected", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            if not red_detected and not green_detected:
                print("[INFO] Aucune couleur détectée.")

            # Afficher l'image
            cv2.imshow("Video Feed", frame)

            # Quitter en appuyant sur 'q'
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("[INFO] Fermeture de l'application...")
                break

    except Exception as e:
        print(f"[ERREUR] Une exception s'est produite : {e}")

    finally:
        print("[INFO] Libération des ressources...")
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
