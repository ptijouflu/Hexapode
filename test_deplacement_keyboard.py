import threading
import time
import curses
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all

# Variable globale pour le mouvement
next_movement = "forward"
movement_lock = threading.Lock()

def key_listener(stdscr):
    global next_movement
    stdscr.nodelay(True)  # Ne bloque pas l'attente de touche
    while True:
        key = stdscr.getch()
        if key != -1:  # Si une touche est pressée
            with movement_lock:
                if key == ord('z'):
                    print("Touche Z pressée : avancer")
                    next_movement = "forward"
                elif key == ord('q'):
                    print("Touche Q pressée : gauche")
                    next_movement = "left"
                elif key == ord('s'):
                    print("Touche S pressée : reculer")
                    next_movement = "backward"
                elif key == ord('d'):
                    print("Touche D pressée : droite")
                    next_movement = "right"
                elif key == ord(' '):  # Espace pour "still"
                    print("Touche Espace pressée : immobile")
                    next_movement = "still"
                elif key == ord('m'):  # 'm' pour quitter
                    return  # Sort de la fonction et arrête le thread

def main():
    global next_movement, movement_lock
    # Initialisation de curses
    stdscr = curses.initscr()
    curses.noecho()  # Désactive l'écho des touches
    curses.cbreak()  # Désactive le buffering des touches

    # Démarre le thread pour écouter le clavier
    listener_thread = threading.Thread(target=key_listener, args=(stdscr,), daemon=True)
    listener_thread.start()

    # Initialisation du contrôleur et des mouvements
    movement_bank = MovementBank()
    import_all(movement_bank)
    basic_set = movement_bank.get_movement_set("basic movements")
    controller = Controller()

    try:
        while listener_thread.is_alive():  # Tant que le thread écoute
            with movement_lock:
                movement = basic_set.get_movement(next_movement)
            controller.execute_movement(movement)
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nArrêt du programme demandé par l'utilisateur...")
    except Exception as e:
        print(f"Erreur inattendue : {e}")
    finally:
        if hasattr(controller, 'disable_torque_all'):
            controller.disable_torque_all()
        else:
            print("Erreur : la méthode 'disable_torque_all' n'existe pas dans Controller.")
        print("Nettoyage terminé.")
        curses.endwin()  # Restaure le terminal

if __name__ == '__main__':
    main()
