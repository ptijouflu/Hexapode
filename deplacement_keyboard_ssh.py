#!/usr/bin/env python3
"""
Script de déplacement contrôlé au clavier - Version SSH compatible
Utilise le module 'keyboard' natif qui fonctionne en SSH

Contrôles:
  Z - Avancer
  Q - Tourner à gauche
  S - Reculer
  D - Tourner à droite
  ESPACE - Arrêter
  Ctrl+C - Quitter
"""

import threading
import time
import keyboard
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all

def key_listener(is_listening):
    """Écoute les touches du clavier"""
    global next_movement
    
    while is_listening[0]:
        try:
            # Vérifier les touches sans bloquer le programme
            if keyboard.is_pressed('z'):
                with movement_lock:
                    next_movement = "forward"
                time.sleep(0.1)
            elif keyboard.is_pressed('q'):
                with movement_lock:
                    next_movement = "left"
                time.sleep(0.1)
            elif keyboard.is_pressed('s'):
                with movement_lock:
                    next_movement = "backward"
                time.sleep(0.1)
            elif keyboard.is_pressed('d'):
                with movement_lock:
                    next_movement = "right"
                time.sleep(0.1)
            elif keyboard.is_pressed('space'):
                with movement_lock:
                    next_movement = "still"
                time.sleep(0.1)
            else:
                time.sleep(0.05)
        except Exception as e:
            print(f"[ERREUR] Erreur dans key_listener: {e}")
            time.sleep(0.1)

def main():
    global next_movement, movement_lock
    
    print("="*60)
    print("🎮 HEXAPODE - CONTRÔLE AU CLAVIER (SSH Compatible)")
    print("="*60)
    print("\n📋 Contrôles:")
    print("  Z - Avancer")
    print("  Q - Tourner à gauche")
    print("  S - Reculer")
    print("  D - Tourner à droite")
    print("  ESPACE - Arrêter")
    print("  Ctrl+C - Quitter")
    print("\n" + "="*60 + "\n")
    
    # Initialisation
    movement_bank = MovementBank()
    import_all(movement_bank)
    basic_set = movement_bank.get_movement_set("basic movements")
    controller = Controller()
    
    next_movement = "still"
    movement_lock = threading.Lock()
    is_listening = [True]
    
    # Lancer le thread d'écoute du clavier
    print("[INFO] Initialisation du thread d'écoute...")
    thread = threading.Thread(target=key_listener, args=(is_listening,), daemon=True)
    thread.start()
    
    print("[INFO] En écoute... Pressez les touches (Z,Q,S,D, ESPACE)\n")
    
    try:
        frame_count = 0
        while True:
            frame_count += 1
            
            with movement_lock:
                current_movement = next_movement
            
            # Afficher le mouvement tous les 10 frames
            if frame_count % 10 == 0:
                print(f"[Frame {frame_count}] Mouvement actuel: {current_movement}")
            
            # Exécuter le mouvement
            movement = basic_set.get_movement(current_movement)
            if movement:
                controller.execute_movement(movement)
            
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] Arrêt demandé par l'utilisateur...")
        is_listening[0] = False
        time.sleep(0.2)
    except Exception as e:
        print(f"\n[ERREUR] Exception non gérée: {e}")
        is_listening[0] = False
    finally:
        print("[INFO] Désactivation du couple des servomoteurs...")
        if hasattr(controller, 'disable_torque_all'):
            try:
                controller.disable_torque_all()
            except Exception as e:
                print(f"[ERREUR] Erreur lors de la désactivation: {e}")
        print("[INFO] Arrêt du programme")
        print("="*60)

if __name__ == '__main__':
    main()
