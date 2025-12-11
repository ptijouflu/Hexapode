#!/usr/bin/env python3
"""
Script de déplacement contrôlé par stdin - Version interactive
Fonctionne parfaitement en SSH sans aucune dépendance spéciale

Contrôles:
  z - Avancer
  q - Tourner à gauche
  s - Reculer
  d - Tourner à droite
  ESPACE - Arrêter
  h - Afficher l'aide
  q - Quitter
"""

import sys
import threading
import time
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all

class HexapodeController:
    def __init__(self):
        self.movement_bank = MovementBank()
        import_all(self.movement_bank)
        self.basic_set = self.movement_bank.get_movement_set("basic movements")
        self.controller = Controller()
        
        self.next_movement = "still"
        self.movement_lock = threading.Lock()
        self.running = True
        
    def display_help(self):
        """Affiche l'aide"""
        print("\n" + "="*60)
        print("🎮 HEXAPODE - CONTRÔLE INTERACTIF (SSH Compatible)")
        print("="*60)
        print("\n📋 Commandes disponibles:")
        print("  z - Avancer")
        print("  q - Tourner à gauche")
        print("  s - Reculer")
        print("  d - Tourner à droite")
        print("  (ESPACE) - Arrêter")
        print("  h - Afficher cette aide")
        print("  quit/exit - Quitter le programme")
        print("\n" + "="*60 + "\n")
        
    def input_listener(self):
        """Thread qui écoute les entrées utilisateur"""
        print("[INFO] En écoute des commandes...")
        try:
            while self.running:
                try:
                    # Lire une commande avec timeout
                    command = input(">>> ").strip().lower()
                    
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
                    elif command == ' ' or command == 'space':
                        with self.movement_lock:
                            self.next_movement = "still"
                        print("⏸️  Arrêter")
                    elif command == 'h' or command == 'help':
                        self.display_help()
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
                    
        except KeyboardInterrupt:
            self.running = False
            
    def run(self):
        """Boucle principale"""
        self.display_help()
        
        # Lancer le thread d'écoute
        listener_thread = threading.Thread(target=self.input_listener, daemon=False)
        listener_thread.start()
        
        try:
            frame_count = 0
            while self.running:
                frame_count += 1
                
                with self.movement_lock:
                    current_movement = self.next_movement
                
                # Afficher le mouvement tous les 20 frames
                if frame_count % 20 == 0:
                    print(f"[Frame {frame_count}] Mouvement actuel: {current_movement}")
                
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
            listener_thread.join(timeout=1)
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
    print("\n🚀 Démarrage du contrôleur Hexapode (SSH compatible)\n")
    controller = HexapodeController()
    controller.run()

if __name__ == '__main__':
    main()
