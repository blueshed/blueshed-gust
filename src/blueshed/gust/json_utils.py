"""
We want our own DateTimeEncoder
"""

import dataclasses
import enum
import json
from collections.abc import Callable
from decimal import Decimal


class Encoder(json.JSONEncoder):
    """
    Encodes datetimes and Decimals
    calls to_json on object if it has that method
    """

    def default(self, obj):
        """check for our types"""
        if hasattr(obj, 'to_json') and isinstance(
            getattr(obj, 'to_json'), Callable
        ):
            return obj.to_json()
        if dataclasses.is_dataclass(obj):
            return dataclasses.asdict(obj)
        if isinstance(obj, enum.Enum):
            return obj.name
        if hasattr(obj, 'isoformat'):
            return obj.isoformat().replace('T', ' ')
        if isinstance(obj, Decimal):
            return float(obj)
        return self.dont_know_this(obj)

    @classmethod
    def dont_know_this(cls, obj):
        """so a subclass can do the right thing"""
        return str(obj)


def load(*args, **kwargs):
    """calls json.load"""
    return json.load(*args, **kwargs)


def loads(*args, **kwargs):
    """calls json.loads"""
    return json.loads(*args, **kwargs)


def dump(obj, *args, **kwargs):
    """calls json.load"""
    return json.dump(obj, cls=Encoder, *args, **kwargs)


def dumps(obj, **kwargs):
    """calls json.dumps using our Encoder"""
    return json.dumps(obj, cls=Encoder, **kwargs).replace('</', '<\\/')
