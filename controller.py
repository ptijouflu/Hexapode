from hexapodinterface import HexapodInterface
from movement import Movement


class Controller:
    def __init__(self):
        self._interface = HexapodInterface()

    def execute_movement(self, movement):
        """ Execute a movement

        :param movement: Movement to execute
        :type movement: Movement
        :rtype: None
        """
        for keyframe in movement:
            self._update(keyframe)

    def _update(self, keyframe):
        """ Move the robot to a specific Keyframe

        :param keyframe: Keyframe to move
        :type keyframe: typing.Dict[int, float]
        :return:
        """
        self._interface.set_position_servos(keyframe)
        self._interface.update_position()

    def disable_torque_all(self):
        """
        Désactive le torque de tous les servos et ferme le port série.
        """
        # Liste des IDs de tes servos (exemple)
        dxl_ids = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]
        for dxl_id in dxl_ids:
            # Désactive le torque pour chaque servo
            self._interface.set_torque_enable(dxl_id, 0)
        # Ferme le port série
        self._interface.close_port()
