import threading
import time
import keyboard
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all

def on_press(key):
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
        elif key == keyboard.Key.space:
            with movement_lock:
                next_movement = "still"
    except AttributeError:
        pass

def key_listener():
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()

if __name__ == '__main__':
    movement_bank = MovementBank()
    import_all(movement_bank)
    basic_set = movement_bank.get_movement_set("basic movements")
    controller = Controller()
    next_movement = "forward"
    movement_lock = threading.Lock()
    thread = threading.Thread(target=key_listener, daemon=True)
    thread.start()
    try:
        while True:
            with movement_lock:
                movement = basic_set.get_movement(next_movement)
            controller.execute_movement(movement)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nArrêt du programme demandé par l'utilisateur...")
        if hasattr(controller, 'disable_torque_all'):
            controller.disable_torque_all()
        else:
            print("Erreur : la méthode 'disable_torque_all' n'existe pas dans Controller.")
    except Exception as e:
        print(f"Erreur inattendue : {e}")
        if hasattr(controller, 'disable_torque_all'):
            controller.disable_torque_all()
    finally:
        print("Nettoyage terminé.")
