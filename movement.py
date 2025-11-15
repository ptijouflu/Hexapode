class Movement:
    def __init__(self, name):
        """

        :param name: name of the movement
        :type name: str
        """
        self.__name = name
        self.__keyframes = []

    def __iter__(self):
        self.__current_idx = 0
        return self

    def __next__(self):
        if self.__current_idx >= len(self.__keyframes):
            raise StopIteration
        current_keyframe = self.__keyframes[self.__current_idx]
        self.__current_idx += 1
        return current_keyframe

    def add_keyframe(self, keyframe):
        """ Add a keyframe to the movement

        :param keyframe: keyframe to add
        :type keyframe: typing.Dict[int, float]
        :return:
        """
        for key in keyframe.keys():
            if not (1 <= key <= 12):
                raise ValueError(f'Invalid keyframe leg_id \'{key}\'')
            if not (0 <= keyframe[key] <= 1):
                raise ValueError(f'Invalid keyframe coeff \'{keyframe[key]}\' for leg_id \'{key}\'')
        self.__keyframes.append(keyframe)

    def get_name(self):
        """ Get the name of the movement

        :return: name of the movement
        :rtype: str
        """
        return self.__name
