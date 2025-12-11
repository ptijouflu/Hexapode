#!/usr/bin/env python3
"""
Script de déplacement contrôlé - Version entièrement SSH compatible
Utilise STDIN sans dépendance clavier système

Contrôles (tapez et appuyez sur ENTRÉE):
  z - Avancer
  q - Tourner à gauche
  s - Reculer
  d - Tourner à droite
  ESPACE - Arrêter
  h - Aide
  quit - Quitter
"""

import threading
import time
import sys
import select
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all

class HexapodeMovementController:
    def __init__(self):
        """Initialise le contrôleur"""
        self.movement_bank = MovementBank()
        import_all(self.movement_bank)
        self.basic_set = self.movement_bank.get_movement_set("basic movements")
        self.controller = Controller()
        
        self.next_movement = "still"
        self.movement_lock = threading.Lock()
        self.running = True
        self.frame_count = 0
        
    def display_banner(self):
        """Affiche la bannière"""
        print("\n" + "="*60)
        print("🎮 HEXAPODE - CONTRÔLE AU CLAVIER (SSH Compatible)")
        print("="*60)
        print("\n📋 Contrôles (tapez et appuyez sur ENTRÉE):")
        print("  z - Avancer")
        print("  q - Tourner à gauche")
        print("  s - Reculer")
        print("  d - Tourner à droite")
        print("  (ESPACE) - Arrêter")
        print("  h - Aide")
        print("  quit - Quitter")
        print("\n" + "="*60 + "\n")
        print("[INFO] En attente de commandes...\n")
        
    def input_listener(self):
        """Thread qui écoute les entrées utilisateur"""
        while self.running:
            try:
                # Lire une commande avec timeout (non-bloquant)
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    command = sys.stdin.readline().strip().lower()
                    
                    if not command:
                        continue
                    
                    if command == 'z':
                        with self.movement_lock:
                            self.next_movement = "forward"
                        print("➡️  Avancer")
                    elif command == 'q':
                        with self.movement_lock:
                            self.next_movement = "left"
                        print("↙️  Tourner à gauche")
                    elif command == 's':
                        with self.movement_lock:
                            self.next_movement = "backward"
                        print("⬅️  Reculer")
                    elif command == 'd':
                        with self.movement_lock:
                            self.next_movement = "right"
                        print("↗️  Tourner à droite")
                    elif command == 'space' or command == ' ':
                        with self.movement_lock:
                            self.next_movement = "still"
                        print("⏸️  Arrêter")
                    elif command == 'h' or command == 'help':
                        self.display_banner()
                    elif command in ['quit', 'exit']:
                        self.running = False
                        print("[INFO] Arrêt demandé...")
                    else:
                        print(f"❌ Commande inconnue: '{command}'. Tapez 'h' pour l'aide.")
            except EOFError:
                # Fin d'entrée (Ctrl+D)
                self.running = False
            except Exception as e:
                print(f"[ERREUR] {e}")
                time.sleep(0.1)
    
    def run(self):
        """Boucle principale"""
        self.display_banner()
        
        # Lancer le thread d'écoute
        listener_thread = threading.Thread(target=self.input_listener, daemon=True)
        listener_thread.start()
        
        try:
            while self.running:
                self.frame_count += 1
                
                with self.movement_lock:
                    current_movement = self.next_movement
                
                # Afficher le mouvement tous les 20 frames
                if self.frame_count % 20 == 0:
                    print(f"[Frame {self.frame_count}] Mouvement actuel: {current_movement}")
                
                # Exécuter le mouvement
                movement = self.basic_set.get_movement(current_movement)
                if movement:
                    self.controller.execute_movement(movement)
                
                time.sleep(0.05)
                
        except KeyboardInterrupt:
            print("\n[INFO] Interruption clavier détectée")
        except Exception as e:
            print(f"[ERREUR] Exception: {e}")
        finally:
            self.running = False
            self.cleanup()
            
    def cleanup(self):
        """Nettoie les ressources"""
        print("\n[INFO] Désactivation du couple des servomoteurs...")
        if hasattr(self.controller, 'disable_torque_all'):
            try:
                self.controller.disable_torque_all()
            except Exception as e:
                print(f"[ERREUR] {e}")
        print("[INFO] Arrêt du programme")
        print("="*60)

def main():
    """Fonction principale"""
    print("\n🚀 Démarrage du contrôleur Hexapode (SSH compatible)\n")
    controller = HexapodeMovementController()
    controller.run()

if __name__ == '__main__':
    main()
