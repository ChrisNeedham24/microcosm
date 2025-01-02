import dataclasses
from json import JSONEncoder


class SaveEncoder(JSONEncoder):
    """
    The encoder used to encode game state to a JSON file.
    """
    def default(self, o):
        """
        Returns the JSON representation of the given object.
        :param o: The object to JSON-ify.
        :return: The JSON representation of the object.
        """
        # Data classes have their own dictionary representations.
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        # Sets must be represented as lists, no real difference anyway. We sort the resulting lists to ensure that
        # encoding is stable.
        if isinstance(o, set):
            set_as_list: list = list(o)
            set_as_list.sort()
            return set_as_list
        # ObjectConvertors, which are defined below, are essentially dicts with attributes anyway, so just return their
        # dict.
        if isinstance(o, ObjectConverter):
            return o.__dict__
        return {}


class ObjectConverter:
    """
    A convenience class that allows attribute access to dictionary objects.
    """
    def __init__(self, dictionary):
        """
        Initialises the object.
        :param dictionary: The dictionary to use to populate attributes.
        """
        self.__dict__.update(dictionary)
