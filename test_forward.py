import time
import os
from controller import Controller
from movementbank import MovementBank
from movementset import MovementSet
from movement import Movement
import json

def main():
    movement_bank = MovementBank()
    
    # Charger uniquement le fichier mis à jour
    with open('move_updated.json', 'r') as file:
        data = json.load(file)
        movement_set = MovementSet(data['name'])
        for movement_data in data['movements']:
            movement = Movement(movement_data['name'])
            for keyframe in movement_data['keyframes']:
                # Convertir les clés de str à int
                int_keyframe = {int(k): v for k, v in keyframe.items()}
                movement.add_keyframe(int_keyframe)
            movement_set.add_movement(movement)
        movement_bank.add_movement_set(movement_set)
    
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
            time.sleep(0.3)
    except KeyboardInterrupt:
        print("Arrêt du programme demandé par l'utilisateur...")
    finally:
        if hasattr(controller, 'disable_torque_all'):
            controller.disable_torque_all()
        print("Nettoyage terminé.")

if __name__ == '__main__':
    main()
