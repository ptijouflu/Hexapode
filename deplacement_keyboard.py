import threading
import time
import os
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all

# Essayer d'importer pynput, sinon utiliser stdin
USE_PYNPUT = False
try:
    from pynput import keyboard as pynput_keyboard
    USE_PYNPUT = True
except (ImportError, Exception):
    print("[AVERTISSEMENT] pynput non disponible, utilisation du mode interactif stdin")

def on_press(key):
    """Callback pour pynput"""
    global next_movement
    try:
        if key.char == 'z':
            with movement_lock:
                next_movement = "forward"
        elif key.char == 'q':
            with movement_lock:
                next_movement = "left"
        elif key.char == 's':
            with movement_lock:
                next_movement = "backward"
        elif key.char == 'd':
            with movement_lock:
                next_movement = "right"
        elif key == pynput_keyboard.Key.space:
            with movement_lock:
                next_movement = "still"
    except AttributeError:
        pass

def key_listener():
    """Écoute les touches du clavier"""
    if USE_PYNPUT:
        with pynput_keyboard.Listener(on_press=on_press) as listener:
            listener.join()
    else:
        # Mode stdin interactif
        key_listener_stdin()

def key_listener_stdin():
    """Écoute les entrées stdin (compatible SSH)"""
    global next_movement
    global is_listening
    
    print("[INFO] Mode interactif stdin (SSH compatible)")
    print("[INFO] Tapez Z, Q, S, D, ESPACE pour contrôler, Ctrl+C pour quitter\n")
    
    import sys
    import select
    
    while is_listening:
        try:
            # Vérifier s'il y a une entrée disponible (non-bloquant)
            if sys.stdin in select.select([sys.stdin], [], [], 0.05)[0]:
                char = sys.stdin.read(1).lower()
                
                if char == 'z':
                    with movement_lock:
                        next_movement = "forward"
                    print("➡️  Avancer")
                elif char == 'q':
                    with movement_lock:
                        next_movement = "left"
                    print("↙️  Tourner à gauche")
                elif char == 's':
                    with movement_lock:
                        next_movement = "backward"
                    print("⬅️  Reculer")
                elif char == 'd':
                    with movement_lock:
                        next_movement = "right"
                    print("↗️  Tourner à droite")
                elif char == ' ':
                    with movement_lock:
                        next_movement = "still"
                    print("⏸️  Arrêter")
        except Exception as e:
            pass

if __name__ == '__main__':
    print("="*60)
    print("🎮 HEXAPODE - CONTRÔLE AU CLAVIER")
    print("="*60)
    print("\n📋 Contrôles:")
    print("  Z - Avancer")
    print("  Q - Tourner à gauche")
    print("  S - Reculer")
    print("  D - Tourner à droite")
    print("  ESPACE - Arrêter")
    print("  Ctrl+C - Quitter")
    print("\n" + "="*60 + "\n")
    
    movement_bank = MovementBank()
    import_all(movement_bank)
    basic_set = movement_bank.get_movement_set("basic movements")
    controller = Controller()
    next_movement = "forward"
    movement_lock = threading.Lock()
    is_listening = True
    
    thread = threading.Thread(target=key_listener, daemon=True)
    thread.start()
    try:
        frame_count = 0
        while True:
            frame_count += 1
            with movement_lock:
                movement = basic_set.get_movement(next_movement)
            
            # Afficher le mouvement tous les 10 frames
            if frame_count % 10 == 0:
                print(f"[Frame {frame_count}] Mouvement: {next_movement}")
            
            controller.execute_movement(movement)
            time.sleep(0.05)
    except KeyboardInterrupt:
        is_listening = False
        print("\n[INFO] Arrêt du programme demandé par l'utilisateur...")
        if hasattr(controller, 'disable_torque_all'):
            try:
                controller.disable_torque_all()
            except Exception as e:
                print(f"[ERREUR] {e}")
        print("[INFO] Arrêt du programme")
        print("="*60)
    except Exception as e:
        is_listening = False
        print(f"[ERREUR] Exception inattendue : {e}")
        if hasattr(controller, 'disable_torque_all'):
            try:
                controller.disable_torque_all()
            except Exception as err:
                print(f"[ERREUR] {err}")
    finally:
        is_listening = False
        print("[INFO] Nettoyage terminé.")
