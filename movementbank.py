from movementset import MovementSet


class MovementBank:
    def __init__(self):
        self.__movement_sets = []

    def add_movement_set(self, movement_set: MovementSet):
        """ Add a movement set to the movement bank

        :param movement_set: movement set to be added to the movement bank
        :type movement_set: MovementSet
        :rtype: None
        :exception: NameError : If a movement set with the same name already exists
        """
        for current_movement_set in self.__movement_sets:
            if current_movement_set.get_name() == movement_set.get_name():
                raise NameError(f'Move set \'{movement_set.get_name()}\' already exists')
        self.__movement_sets.append(movement_set)

    def remove_movement_set(self, movement_set: MovementSet):
        """ Remove a movement set from the movement bank

        :param movement_set: movement set to be removed from the movement bank
        :rtype: None
        """
        self.__movement_sets.remove(movement_set)

    def get_movement_set(self, movement_set_name: str) -> MovementSet:
        """ Get a movement set from the movement bank

        :param movement_set_name: name of the movement set
        :return: movement set of the movement bank
        :rtype: MovementSet
        :raise: NameError: If no movement set with such name exists in the movement bank
        """
        for movement_set in self.__movement_sets:
            if movement_set.get_name() == movement_set_name:
                return movement_set
        raise NameError(f'Move set \'{movement_set_name}\' not found')
    
    def clear(self):
        """Supprime tous les ensembles de mouvements."""
        self._movement_sets = {}  # Supposons que les ensembles sont stockés dans un dictionnaire _movement_sets

