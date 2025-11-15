from movement import Movement


class MovementSet:
    def __init__(self, name):
        """

        :param name: name of the movementset
        :type name: str
        """
        self.__name = name
        self.__movements = []

    def add_movement(self, movement):
        """ Add a movement to the movement set

        :param movement: movement to be added to the movement set
        :type movement: Movement
        :rtype: None
        :exception NameError: If a movement with the same name already exists in the movement set
        """
        for current_movement_set in self.__movements:
            if current_movement_set.get_name() == movement.get_name():
                raise NameError(f'Movement \'{movement.get_name()}\' already exists in moveset \'{self.get_name()}\'')
        self.__movements.append(movement)

    def remove_movement(self, movement_name):
        """ Remove a movement from the movement set

        :param movement_name: name of the movement to be removed from the movement set
        :type movement_name: str
        :rtype: None
        """
        for movement in self.__movements:
            if movement.get_name() == movement_name:
                self.__movements.remove(movement)

    def get_movement(self, movement_name):
        """ Get a movement from the movement set

        :param movement_name: name of the movement to be retrieved from the movement set
        :type movement_name: str
        :return: movement from the movement set
        :rtype: Movement
        :exception NameError: If no movement with such name exists in the movement set
        """
        for movement in self.__movements:
            if movement.get_name() == movement_name:
                return movement
        raise NameError(f'Movement \'{movement_name}\' not found')

    def get_name(self):
        """ Get the name of the movement set

        :return: name of the movement set
        :rtype: str
        """
        return self.__name
