import dataclasses
from json import JSONEncoder


class SaveEncoder(JSONEncoder):
    def default(self, o):
        if dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, set):
            return list(o)
        elif isinstance(o, ObjectConverter):
            return o.__dict__
        return super().default(o)


class ObjectConverter(object):
    def __init__(self, dictionary):
        self.__dict__.update(dictionary)
