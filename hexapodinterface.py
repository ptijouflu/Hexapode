import typing
from hexapodsetup import *


class HexapodInterface:
    """
    Class that control each servo of the Hexapod.
    """

    def __init__(self):
        self.__setup = HexapodSetup()
        self.__goal_positions = {}
        self.__current_positions = {}

    def set_position_servos(self, goal_positions):
        """Set a new goal position for each specified servo

        :param goal_positions: a dictionary with servo id as key and servo goal position (between 0 and 1) as value
        :type goal_pxositions: typing.Dict[int, float]
        """

        for dxl_id, goal_position in goal_positions.items():
            self.set_position_servo(dxl_id, goal_position)

    def set_position_servo(self, servo_id, goal_position):
        """Set a new goal position for a servo

        :param servo_id:
        :type servo_id: int
        :param goal_position: a value between 0 and 100, where 0 denotes the minimum movement and
        100 denotes the maximum movement
        :type goal_position:
        :rtype: None
        :raise KeyError: If servo_id is out of range [1,12]
        """

        if servo_id in (constants.LIFT_SERVOS + constants.ROTATE_SERVOS):
            self.__goal_positions[servo_id] = goal_position
        else:
            raise KeyError(f"Servo ID \'{servo_id}\' not found.")

    def set_position_legs(self, goal_positions):
        """Set a new goal position for each specified leg

        :param goal_positions: a dictionary with leg id as key and a tuple of servo goal rotation and lift
                (between 0 and 1) as value.
                leg id is defined as the odd id between the two servos id of the leg
                (i.e. if a leg a two servos with id 1 and 2, leg id is 1)
        :type goal_positions: typing.Dict[int, typing.Tuple[float, float]]
        :rtype: None
        """

        for leg_id, (goal_rotation, goal_lift) in goal_positions.items():
            self.set_position_leg(leg_id, goal_rotation, goal_lift)

    def set_position_leg(self, leg_id, goal_rotation, goal_lift):
        """Set a new goal position for a leg

        :param leg_id:
        :type leg_id: int
        :param goal_rotation: a value between 0 and 1, where 0 denotes a full rotation clockwise and
        1 denotes a full rotation counter-clockwise
        :type goal_rotation: float
        :param goal_lift: a value between 0 and 1, where 0 denotes a full retractation and
        1 denotes a full extension
        :type goal_lift: float
        :rtype: None

        :raise: 
        """

        if leg_id % 2 == 0:
            raise ValueError(f"Leg ID \'{leg_id}\' must be an odd number.")

        self.set_position_servo(leg_id, goal_rotation)
        self.set_position_servo(leg_id + 1, goal_lift)

    def update_position(self):
        """Move each servo according to its goal position

        Block the programm until the robot has reached the goal position

        :rtype: None
        """

        self.__setup.write_position(self.__goal_positions)
        for dxl_id in self.__goal_positions.keys():
            self.__current_positions[dxl_id] = self.__goal_positions[dxl_id]
        self.__goal_positions = {}
