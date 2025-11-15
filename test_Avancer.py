import time
from controller import Controller
from movementbank import MovementBank
from movementimport import import_all

def main():
    # Crée une nouvelle instance de MovementBank
    movement_bank = MovementBank()

    # Importe les mouvements (même s'ils existent déjà, on recrée tout)
    import_all(movement_bank)

    # Récupère l'ensemble "basic movements"
    basic_set = movement_bank.get_movement_set("basic movements")
    if basic_set is None:
        print("Erreur : L'ensemble de mouvements 'basic movements' n'a pas été chargé.")
        return

    # Récupère le mouvement "forward_stable"
    forward_stable = basic_set.get_movement("forward_stable")
    if forward_stable is None:
        print("Erreur : Le mouvement 'forward_stable' n'existe pas.")
        return

    controller = Controller()

    try:
        print("Exécution du mouvement 'forward_stable'... Appuyez sur Ctrl+C pour arrêter.")
        while True:
            controller.execute_movement(forward_stable)
            time.sleep(0.1)  # Ajuste ce délai pour changer la vitesse

    except KeyboardInterrupt:
        print("\nArrêt du programme demandé par l'utilisateur...")
    except Exception as e:
        print(f"Erreur inattendue : {e}")
    finally:
        if hasattr(controller, 'disable_torque_all'):
            controller.disable_torque_all()
        print("Nettoyage terminé.")

if __name__ == '__main__':
    main()
