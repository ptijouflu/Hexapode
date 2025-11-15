import json
import os

from movement import Movement
from movementset import MovementSet
from movementbank import MovementBank


def import_one(movementbank, filename):
    """ Import one movement set file to a movement bank

    :param movementbank: a bank of movement sets
    :type movementbank: MovementBank
    :param filename: the full name of the movement set file
    :type filename: str
    :return:
    """
    with open(filename, 'r') as file:
        data = json.load(file)
        movement_set = MovementSet(data['name'])
        for json_movement in data['movements']:
            movement = Movement(json_movement['name'])
            for json_keyframe in json_movement['keyframes']:
                keyframe = {int(key): value for key, value in json_keyframe.items()}
                movement.add_keyframe(keyframe)
            movement_set.add_movement(movement)
        movementbank.add_movement_set(movement_set)


def import_all(movementbank, folder='movementbank'):
    """ Import all movement sets files in a folder

    :param movementbank: a bank of movement sets
    :type movementbank: MovementBank
    :param folder: the folder containing the movement sets
    :type folder: str
    :return:
    """
    for filename in os.listdir(folder):
        import_one(movementbank, os.path.join(folder, filename))
