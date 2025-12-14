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
        Désactive le torque de tous les servos en supprimant l'objet interface
        (appelle automatiquement __del__ de HexapodSetup qui désactive les servos)
        """
        if hasattr(self, '_interface'):
            del self._interface
