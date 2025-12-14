#!/usr/bin/env python3
"""
=============================================================================
HEXAPODE ROBOTIS ENGINEER KIT 1 - Contrôle Interactif Autonome
=============================================================================

Ce fichier est autonome et contient tout le nécessaire pour contrôler
l'hexapode Robotis Engineer Kit 1 (2XL430-W250 DYNAMIXEL).

Contrôles:
  z - Avancer
  s - Reculer
  q - Tourner à gauche
  d - Tourner à droite
  ESPACE ou x - Arrêter (position still)
  h - Afficher l'aide
  quit/exit - Quitter le programme

Usage:
  python3 hexapode_control.py

=============================================================================
"""

import sys
import threading
import time

try:
    import dynamixel_sdk
except ImportError:
    print("ERREUR: dynamixel_sdk n'est pas installé!")
    print("Installez-le avec: pip install dynamixel-sdk")
    sys.exit(1)

# =============================================================================
# CONFIGURATION HARDWARE - Robotis Engineer Kit 1
# =============================================================================

# Port série
DEVICENAME = '/dev/ttyUSB0'  # Linux
# DEVICENAME = 'COM3'        # Windows

# Protocole Dynamixel
PROTOCOL_VERSION = 2.0
BAUDRATE = 1000000

# Adresses des registres (X Series / 2XL430)
ADDR_TORQUE_ENABLE = 64
ADDR_GOAL_POSITION = 116
LEN_GOAL_POSITION = 4
ADDR_PRESENT_POSITION = 132
LEN_PRESENT_POSITION = 4
ADDR_PROFILE_VELOCITY = 112
ADDR_PROFILE_ACCELERATION = 108

# Valeurs de contrôle
TORQUE_ENABLE = 1
TORQUE_DISABLE = 0
DXL_MOVING_STATUS_THRESHOLD = 80  # Seuil de position atteinte

# Vitesse et accélération des servos
PROFILE_VELOCITY = 80       # Vitesse de profil (plus haut = plus rapide)
PROFILE_ACCELERATION = 40   # Accélération

# IDs des servomoteurs
# Pattes : 1-2 (avant droite), 3-4 (milieu droite), 5-6 (arrière droite)
#          7-8 (avant gauche), 9-10 (milieu gauche), 11-12 (arrière gauche)
# Impairs = rotation, Pairs = levée
LIFT_SERVOS = [2, 4, 6, 8, 10, 12]      # Servos de levée (haut/bas)
ROTATE_SERVOS = [1, 3, 5, 7, 9, 11]     # Servos de rotation (avant/arrière)

# =============================================================================
# LIMITES DE POSITION - Calibrées pour Robotis Engineer Kit 1
# =============================================================================

# Positions min/max pour la levée (tous les servos pairs)
LIFT_MIN = 1210    # Patte levée
LIFT_MAX = 2200    # Patte au sol

# Positions min/max pour la rotation (servos impairs, par ID)
# Ces valeurs définissent la plage de mouvement de chaque patte
ROTATE_POSITIONS = {
    1:  (1450, 2650),   # Patte avant droite
    3:  (1200, 2400),   # Patte milieu droite
    5:  (1400, 2700),   # Patte arrière droite
    7:  (1300, 2600),   # Patte avant gauche
    9:  (1450, 2650),   # Patte milieu gauche
    11: (1450, 2650),   # Patte arrière gauche
}

# =============================================================================
# MOUVEMENTS PRÉDÉFINIS - Optimisés pour marche tripode
# =============================================================================
# Valeurs entre 0.0 et 1.0 :
#   - Pour LIFT : 0=levé, 1=au sol
#   - Pour ROTATE : 0=arrière, 0.5=neutre, 1=avant
# Amplitude ajustée pour un bon déplacement

MOVEMENTS = {
    # Position stable au repos
    "still": [
        {
            1: 0.5, 2: 0.5,
            3: 0.5, 4: 0.5,
            5: 0.5, 6: 0.5,
            7: 0.5, 8: 0.5,
            9: 0.5, 10: 0.5,
            11: 0.5, 12: 0.5
        }
    ],
    
    # Avancer - Marche tripode symétrique (amplitude augmentée 0.3-0.7)
    "forward": [
        # Phase 1: Lever tripode 1 (pattes 1,4,5 = servos 2,8,10)
        {
            2: 0.2, 8: 0.2, 10: 0.2,    # Lever pattes 1,4,5
            4: 1.0, 6: 1.0, 12: 1.0     # Pattes 2,3,6 au sol
        },
        # Phase 2: Avancer tripode 1 (pattes en l'air vont vers l'avant)
        {
            1: 0.7, 7: 0.7, 9: 0.3,     # Patte 1,4 avant / Patte 5 arrière
            3: 0.3, 5: 0.7, 11: 0.3     # Patte 2,6 arrière / Patte 3 avant
        },
        # Phase 3: Poser tripode 1, lever tripode 2
        {
            2: 1.0, 8: 1.0, 10: 1.0,    # Poser pattes 1,4,5
            4: 0.2, 6: 0.2, 12: 0.2     # Lever pattes 2,3,6
        },
        # Phase 4: Pousser avec tripode 1, avancer tripode 2
        {
            1: 0.3, 7: 0.3, 9: 0.7,     # Patte 1,4 reculent (poussent) / Patte 5 avance
            3: 0.7, 5: 0.3, 11: 0.7     # Patte 2,6 avancent / Patte 3 recule (pousse)
        }
    ],
    
    # Reculer - Inverse de forward
    "backward": [
        # Phase 1: Lever tripode 1
        {
            2: 0.2, 8: 0.2, 10: 0.2,
            4: 1.0, 6: 1.0, 12: 1.0
        },
        # Phase 2: Tripode 1 va vers l'arrière
        {
            1: 0.3, 7: 0.3, 9: 0.7,
            3: 0.7, 5: 0.3, 11: 0.7
        },
        # Phase 3: Poser tripode 1, lever tripode 2
        {
            2: 1.0, 8: 1.0, 10: 1.0,
            4: 0.2, 6: 0.2, 12: 0.2
        },
        # Phase 4: Tripode 1 pousse vers l'avant, tripode 2 va vers l'arrière
        {
            1: 0.7, 7: 0.7, 9: 0.3,
            3: 0.3, 5: 0.7, 11: 0.3
        }
    ],
    
    # Déplacement latéral gauche (strafe left)
    "strafe_left": [
        # Phase 1: Lever tripode 1
        {
            2: 0.2, 8: 0.2, 10: 0.2,
            4: 1.0, 6: 1.0, 12: 1.0
        },
        # Phase 2: Pattes gauches reculent, pattes droites avancent
        {
            1: 0.4, 3: 0.6, 5: 0.4,     # Droite: 1,5 reculent, 3 avance
            7: 0.6, 9: 0.4, 11: 0.6     # Gauche: 7,11 avancent, 9 recule
        },
        # Phase 3: Poser tripode 1, lever tripode 2
        {
            2: 1.0, 8: 1.0, 10: 1.0,
            4: 0.2, 6: 0.2, 12: 0.2
        },
        # Phase 4: Inverse
        {
            1: 0.6, 3: 0.4, 5: 0.6,
            7: 0.4, 9: 0.6, 11: 0.4
        }
    ],
    
    # Déplacement latéral droite (strafe right)
    "strafe_right": [
        # Phase 1: Lever tripode 1
        {
            2: 0.2, 8: 0.2, 10: 0.2,
            4: 1.0, 6: 1.0, 12: 1.0
        },
        # Phase 2: Pattes droites reculent, pattes gauches avancent
        {
            1: 0.6, 3: 0.4, 5: 0.6,     # Droite: 1,5 avancent, 3 recule
            7: 0.4, 9: 0.6, 11: 0.4     # Gauche: 7,11 reculent, 9 avance
        },
        # Phase 3: Poser tripode 1, lever tripode 2
        {
            2: 1.0, 8: 1.0, 10: 1.0,
            4: 0.2, 6: 0.2, 12: 0.2
        },
        # Phase 4: Inverse
        {
            1: 0.4, 3: 0.6, 5: 0.4,
            7: 0.6, 9: 0.4, 11: 0.6
        }
    ],
    
    # Rotation sur place vers la gauche (anti-horaire)
    "rotate_left": [
        # Phase 1: Lever tripode 1
        {
            2: 0.2, 8: 0.2, 10: 0.2,
            4: 1.0, 6: 1.0, 12: 1.0
        },
        # Phase 2: Toutes les pattes dans le même sens
        {
            1: 0.65, 7: 0.65, 9: 0.65,
            3: 0.35, 5: 0.35, 11: 0.35
        },
        # Phase 3: Poser tripode 1, lever tripode 2
        {
            2: 1.0, 8: 1.0, 10: 1.0,
            4: 0.2, 6: 0.2, 12: 0.2
        },
        # Phase 4: Rotation inverse pour revenir
        {
            1: 0.35, 7: 0.35, 9: 0.35,
            3: 0.65, 5: 0.65, 11: 0.65
        }
    ],
    
    # Rotation sur place vers la droite (horaire)
    "rotate_right": [
        # Phase 1: Lever tripode 1
        {
            2: 0.2, 8: 0.2, 10: 0.2,
            4: 1.0, 6: 1.0, 12: 1.0
        },
        # Phase 2: Toutes les pattes dans l'autre sens
        {
            1: 0.35, 7: 0.35, 9: 0.35,
            3: 0.65, 5: 0.65, 11: 0.65
        },
        # Phase 3: Poser tripode 1, lever tripode 2
        {
            2: 1.0, 8: 1.0, 10: 1.0,
            4: 0.2, 6: 0.2, 12: 0.2
        },
        # Phase 4: Rotation pour revenir
        {
            1: 0.65, 7: 0.65, 9: 0.65,
            3: 0.35, 5: 0.35, 11: 0.35
        }
    ]
}


# =============================================================================
# CLASSE HEXAPOD CONTROLLER
# =============================================================================

class HexapodController:
    """Contrôleur principal de l'hexapode"""
    
    def __init__(self):
        self.port_handler = None
        self.packet_handler = None
        self.group_sync_write = None
        self.group_sync_read = None
        self.connected = False
        
        # État du contrôle
        self.current_movement = "still"
        self.movement_lock = threading.Lock()
        self.running = True
        self.movement_in_progress = False  # Flag pour éviter la surcharge
        
    def connect(self):
        """Établit la connexion avec les servomoteurs"""
        print(f"[INFO] Connexion à {DEVICENAME}...")
        
        # Initialisation du port
        self.port_handler = dynamixel_sdk.PortHandler(DEVICENAME)
        self.packet_handler = dynamixel_sdk.PacketHandler(PROTOCOL_VERSION)
        
        # Ouverture du port
        if not self.port_handler.openPort():
            print("[ERREUR] Impossible d'ouvrir le port série!")
            print("         Vérifiez que le câble USB est connecté.")
            return False
        print("✓ Port ouvert")
        
        # Configuration du baudrate
        if not self.port_handler.setBaudRate(BAUDRATE):
            print("[ERREUR] Impossible de configurer le baudrate!")
            return False
        print(f"✓ Baudrate configuré à {BAUDRATE}")
        
        # Initialisation des groupes de synchronisation
        self.group_sync_write = dynamixel_sdk.GroupSyncWrite(
            self.port_handler, self.packet_handler,
            ADDR_GOAL_POSITION, LEN_GOAL_POSITION
        )
        self.group_sync_read = dynamixel_sdk.GroupSyncRead(
            self.port_handler, self.packet_handler,
            ADDR_PRESENT_POSITION, LEN_PRESENT_POSITION
        )
        
        # Activation de chaque servo
        all_servos = LIFT_SERVOS + ROTATE_SERVOS
        for dxl_id in all_servos:
            # Activer le torque
            result, error = self.packet_handler.write1ByteTxRx(
                self.port_handler, dxl_id, ADDR_TORQUE_ENABLE, TORQUE_ENABLE
            )
            if result != dynamixel_sdk.COMM_SUCCESS:
                print(f"[ERREUR] Servo {dxl_id}: {self.packet_handler.getTxRxResult(result)}")
                continue
            
            # Configurer la vitesse
            self.packet_handler.write4ByteTxRx(
                self.port_handler, dxl_id, ADDR_PROFILE_VELOCITY, PROFILE_VELOCITY
            )
            
            # Configurer l'accélération
            self.packet_handler.write4ByteTxRx(
                self.port_handler, dxl_id, ADDR_PROFILE_ACCELERATION, PROFILE_ACCELERATION
            )
            
            # Ajouter au groupe de lecture
            self.group_sync_read.addParam(dxl_id)
            
            print(f"✓ Servo {dxl_id} connecté")
        
        self.connected = True
        print("\n[INFO] Tous les servomoteurs sont connectés!\n")
        return True
    
    def disconnect(self):
        """Déconnecte proprement les servomoteurs"""
        print("\n[INFO] Déconnexion...")
        
        if not self.connected:
            return
            
        # Désactiver le torque de tous les servos
        all_servos = LIFT_SERVOS + ROTATE_SERVOS
        for dxl_id in all_servos:
            self.packet_handler.write1ByteTxRx(
                self.port_handler, dxl_id, ADDR_TORQUE_ENABLE, TORQUE_DISABLE
            )
        
        # Fermer le port
        self.port_handler.closePort()
        self.connected = False
        print("✓ Déconnexion terminée")
    
    def coeff_to_position(self, dxl_id, coeff):
        """Convertit un coefficient [0-1] en position absolue"""
        if dxl_id in LIFT_SERVOS:
            return round(LIFT_MIN + (LIFT_MAX - LIFT_MIN) * coeff)
        elif dxl_id in ROTATE_SERVOS:
            min_pos, max_pos = ROTATE_POSITIONS[dxl_id]
            return round(min_pos + (max_pos - min_pos) * coeff)
        return 0
    
    def execute_keyframe(self, keyframe):
        """Exécute un keyframe (une étape du mouvement)"""
        if not self.connected:
            return
        
        goal_positions = {}
        
        # Préparer les positions
        for dxl_id, coeff in keyframe.items():
            goal_pos = self.coeff_to_position(dxl_id, coeff)
            goal_positions[dxl_id] = goal_pos
            
            # Encoder la position en bytes
            param = [
                dynamixel_sdk.DXL_LOBYTE(dynamixel_sdk.DXL_LOWORD(goal_pos)),
                dynamixel_sdk.DXL_HIBYTE(dynamixel_sdk.DXL_LOWORD(goal_pos)),
                dynamixel_sdk.DXL_LOBYTE(dynamixel_sdk.DXL_HIWORD(goal_pos)),
                dynamixel_sdk.DXL_HIBYTE(dynamixel_sdk.DXL_HIWORD(goal_pos))
            ]
            self.group_sync_write.addParam(dxl_id, param)
        
        # Envoyer les commandes
        self.group_sync_write.txPacket()
        self.group_sync_write.clearParam()
        
        # Attendre que les servos atteignent leur position (avec timeout)
        max_wait = 50  # Maximum 50 itérations (~500ms)
        wait_count = 0
        
        while wait_count < max_wait:
            self.group_sync_read.txRxPacket()
            
            all_reached = True
            for dxl_id, goal_pos in goal_positions.items():
                present_pos = self.group_sync_read.getData(
                    dxl_id, ADDR_PRESENT_POSITION, LEN_PRESENT_POSITION
                )
                if present_pos is None:
                    continue
                if abs(goal_pos - present_pos) > DXL_MOVING_STATUS_THRESHOLD:
                    all_reached = False
                    break
            
            if all_reached:
                break
            
            wait_count += 1
            time.sleep(0.01)
        
        # Petit délai pour stabiliser
        time.sleep(0.02)
    
    def execute_movement(self, movement_name):
        """Exécute un mouvement complet"""
        if movement_name not in MOVEMENTS:
            print(f"[ERREUR] Mouvement '{movement_name}' inconnu!")
            return
        
        # Marquer le mouvement en cours
        self.movement_in_progress = True
        
        try:
            keyframes = MOVEMENTS[movement_name]
            for keyframe in keyframes:
                if not self.running:
                    break
                self.execute_keyframe(keyframe)
        finally:
            self.movement_in_progress = False
    
    def display_help(self):
        """Affiche l'aide"""
        print("\n" + "="*60)
        print("🤖 HEXAPODE ROBOTIS ENGINEER KIT 1 - CONTRÔLE INTERACTIF")
        print("="*60)
        print("\n📋 Commandes disponibles:")
        print("   z      - Avancer")
        print("   s      - Reculer")
        print("   q      - Déplacement latéral gauche")
        print("   d      - Déplacement latéral droite")
        print("   a      - Rotation sur place (anti-horaire)")
        print("   e      - Rotation sur place (horaire)")
        print("   r      - Remise en position initiale")
        print("   x/ESPACE - Arrêter (position stable)")
        print("   h      - Afficher cette aide")
        print("   quit   - Quitter le programme")
        print("\n💡 Tapez une commande puis Entrée")
        print("="*60 + "\n")
    
    def input_listener(self):
        """Thread d'écoute des commandes utilisateur"""
        try:
            while self.running:
                try:
                    command = input(">>> ").strip().lower()
                    
                    if not command:
                        continue
                    
                    if command == 'z':
                        with self.movement_lock:
                            self.current_movement = "forward"
                        print("⬆️  Avancer")
                    
                    elif command == 's':
                        with self.movement_lock:
                            self.current_movement = "backward"
                        print("⬇️  Reculer")
                    
                    elif command == 'q':
                        with self.movement_lock:
                            self.current_movement = "strafe_left"
                        print("⬅️  Déplacement latéral gauche")
                    
                    elif command == 'd':
                        with self.movement_lock:
                            self.current_movement = "strafe_right"
                        print("➡️  Déplacement latéral droite")
                    
                    elif command == 'a':
                        with self.movement_lock:
                            self.current_movement = "rotate_left"
                        print("↺  Rotation anti-horaire")
                    
                    elif command == 'e':
                        with self.movement_lock:
                            self.current_movement = "rotate_right"
                        print("↻  Rotation horaire")
                    
                    elif command == 'r':
                        with self.movement_lock:
                            self.current_movement = "still"
                        print("🔄 Remise en position initiale...")
                        self.execute_movement("still")
                        print("✓ Position initiale atteinte")
                    
                    elif command in ['x', ' ', 'space', 'stop']:
                        with self.movement_lock:
                            self.current_movement = "still"
                        print("⏸️  Arrêt")
                    
                    elif command in ['h', 'help', '?']:
                        self.display_help()
                    
                    elif command in ['quit', 'exit', 'q!']:
                        self.running = False
                        print("[INFO] Arrêt demandé...")
                    
                    else:
                        print(f"❌ Commande inconnue: '{command}'. Tapez 'h' pour l'aide.")
                
                except EOFError:
                    self.running = False
                except Exception as e:
                    print(f"[ERREUR] {e}")
        
        except KeyboardInterrupt:
            self.running = False
    
    def run(self):
        """Boucle principale"""
        # Connexion
        if not self.connect():
            print("[ERREUR] Impossible de se connecter à l'hexapode!")
            return
        
        # Afficher l'aide
        self.display_help()
        
        # Position initiale
        print("[INFO] Mise en position stable...")
        self.execute_movement("still")
        
        # Lancer le thread d'écoute
        listener_thread = threading.Thread(target=self.input_listener, daemon=True)
        listener_thread.start()
        
        print("[INFO] Prêt! En attente de commandes...\n")
        
        try:
            frame_count = 0
            last_movement = "still"
            
            while self.running:
                frame_count += 1
                
                with self.movement_lock:
                    movement = self.current_movement
                
                # N'exécuter le mouvement que s'il n'y a pas déjà un mouvement en cours
                if not self.movement_in_progress:
                    self.execute_movement(movement)
                
                # Afficher le statut quand le mouvement change
                if movement != last_movement:
                    if movement != "still":
                        print(f"   [Mouvement: {movement}]")
                    last_movement = movement
                
                # Petit délai pour éviter de surcharger le CPU
                time.sleep(0.05)
        
        except KeyboardInterrupt:
            print("\n[INFO] Interruption clavier détectée")
        
        except Exception as e:
            print(f"[ERREUR] Exception: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.running = False
            print("\n[INFO] Retour en position stable...")
            try:
                self.execute_movement("still")
            except:
                pass
            self.disconnect()
            print("[INFO] Programme terminé")
            print("="*60)


# =============================================================================
# POINT D'ENTRÉE
# =============================================================================

def main():
    print("\n" + "="*60)
    print("🚀 HEXAPODE ROBOTIS ENGINEER KIT 1")
    print("   Contrôle Interactif v1.0")
    print("="*60 + "\n")
    
    controller = HexapodController()
    controller.run()


if __name__ == '__main__':
    main()
