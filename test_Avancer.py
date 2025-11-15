import time
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all

def main():
    movement_bank = MovementBank()
    import_all(movement_bank)
    basic_set = movement_bank.get_movement_set("basic movements")
    forward_stable = basic_set.get_movement("forward_stable")

    if forward_stable is None:
        print("Erreur : Le mouvement 'forward_stable' n'existe pas.")
        return

    controller = Controller()

    try:
        print("Exécution du mouvement 'forward_stable'... Appuyez sur Ctrl+C pour arrêter.")
        while True:
            controller.execute_movement(forward_stable)
            time.sleep(0.2)  # Délai pour fluidifier le mouvement
    except KeyboardInterrupt:
        print("\nArrêt du programme demandé par l'utilisateur...")
    finally:
        if hasattr(controller, 'disable_torque_all'):
            controller.disable_torque_all()
        print("Nettoyage terminé.")

if __name__ == '__main__':
    main()
