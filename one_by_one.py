import time
from dynamixel_sdk import *

# Initialisation de la connexion au port série et du gestionnaire de paquets
portHandler = PortHandler('/dev/ttyUSB0')  # Remplacez par votre port
packetHandler = PacketHandler(2.0)  # Utilisation du protocole 2.0

# Constantes liées au Dynamixel
BAUDRATE = 57600  # Assurez-vous que cela correspond au paramètre du Dynamixel
ADDR_PRESENT_POSITION = 132  # Adresse de la position actuelle
LEN_PRESENT_POSITION = 4  # Longueur des données de position en octets
DXL_MOVING_STATUS_THRESHOLD = 10  # Seuil de tolérance pour déterminer si la position est atteinte

# Définition des positions des servos (exemple de configuration)
LIFT_SERVOS = [2, 8, 10]  # Servos pour lever les pattes
ROTATE_SERVOS = [4, 6, 12]  # Servos pour la rotation des pattes

# Positions préconfigurées (valeurs fictives pour l'exemple)
lift_positions = {
    2: [500, 1000],
    8: [500, 1000],
    10: [500, 1000]
}

rotate_positions = {
    4: [300, 600],
    6: [300, 600],
    12: [300, 600]
}

def move_one_by_one(ids_positions):
    # Ouvrir le port série
    if not portHandler.openPort():
        print("[ERROR] Échec de l'ouverture du port")
        return
    
    # Définir la vitesse de communication
    if not portHandler.setBaudRate(BAUDRATE):
        print("[ERROR] Échec de la configuration du baud rate")
        return
    
    for dxl_id, position in ids_positions.items():
        print(f"\n[INFO] Déplacement du Dynamixel ID {dxl_id} à la position {position}...")

        # Définir la position cible
        if dxl_id in LIFT_SERVOS:
            goal_position = lift_positions[dxl_id][position]
        elif dxl_id in ROTATE_SERVOS:
            goal_position = rotate_positions[dxl_id][position]
        else:
            print(f"[WARNING] Le servo {dxl_id} n'est ni un servo de levage ni de rotation.")
            continue

        # Conversion de la position en format 4 octets
        param_goal_position = [
            DXL_LOBYTE(DXL_LOWORD(goal_position)),
            DXL_HIBYTE(DXL_LOWORD(goal_position)),
            DXL_LOBYTE(DXL_HIWORD(goal_position)),
            DXL_HIBYTE(DXL_HIWORD(goal_position)),
        ]

        # Écrire la position
        result, error = packetHandler.write4ByteTxRx(portHandler, dxl_id, 116, goal_position)  # 116 est l’adresse de la position cible pour le Dynamixel
        if result != COMM_SUCCESS:
            print(f"[ERROR] Erreur de communication pour le servo {dxl_id}: {packetHandler.getTxRxResult(result)}")
            continue
        if error != 0:
            print(f"[ERROR] Erreur de statut pour le servo {dxl_id}: {packetHandler.getRxPacketError(error)}")

        # Attendre jusqu'à ce que la position soit atteinte
        while True:
            dxl_present_position, result, error = packetHandler.read4ByteTxRx(portHandler, dxl_id, ADDR_PRESENT_POSITION)
            if result != COMM_SUCCESS:
                print(f"[ERROR] Échec de lecture de la position actuelle pour le servo {dxl_id}")
                break

            # Vérifier si la position est atteinte
            if abs(goal_position - dxl_present_position) <= DXL_MOVING_STATUS_THRESHOLD:
                print(f"[SUCCESS] Le Dynamixel ID {dxl_id} a atteint la position {goal_position}.")
                break

        # Pause pour éviter d'envoyer les commandes trop rapidement
        time.sleep(0.2)

    # Fermer le port série
    portHandler.closePort()
    print("\n[INFO] Tous les servos ont atteint leur position.")

# Exemple d'utilisation
if __name__ == "__main__":
    move_one_by_one({
        4: 0, 6: 0, 12: 0,  # Servos de rotation
        2: 1, 8: 1, 10: 1   # Servos de levage
    })
