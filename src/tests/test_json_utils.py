# pylint: disable=W0212, R0201
"""Test the json functionality"""

import enum
import io
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from blueshed.gust import json_utils


class EnumHelper(enum.Enum):
    """test json enums"""

    LOGIN = 1
    REGISTER = 2


@dataclass
class dcRole:
    """a dataclass"""

    _type_: str
    name: str
    act: EnumHelper


class Foo:
    """simple test class"""

    def to_json(self):
        """with to_json method"""
        return {'_type_': 'Foo', 'name': 'Harry'}


class Bert:
    """simple class"""


def test_datetime():
    """support datetime"""
    dt = datetime(2018, 11, 11, 10, 30, 42)
    dtf = dt.isoformat().replace('T', ' ')
    assert f'"{dtf}"' == json_utils.dumps(dt)


def test_date():
    """support date"""
    dt = date(2018, 11, 11)
    dtf = dt.isoformat().replace('T', ' ')
    assert f'"{dtf}"' == json_utils.dumps(dt)


def test_decimal():
    """support for decimal"""
    value = Decimal('42.1')
    assert f'{value}' == json_utils.dumps(value)


def test_obj():
    """we string objects we don't know"""
    value = Bert()
    assert 'Bert' in json_utils.dumps(value)


def test_to_json():
    """dumps"""
    data = json_utils.dumps(Foo())
    data_str = '{"_type_": "Foo", "name": "Harry"}'
    assert data_str == data


def test_doc_dict():
    """use a dot dict"""
    data = json_utils.dumps(Foo())
    data_str = '{"_type_": "Foo", "name": "Harry"}'
    assert data_str == data
    obj = json_utils.loads(
        data_str, object_hook=lambda x: SimpleNamespace(**x)
    )
    assert obj._type_ == 'Foo'
    assert obj.__class__.__name__ == 'SimpleNamespace'
    assert obj.name == 'Harry'


def test_doc_dataclass():
    """test dataclasses"""
    data = json_utils.dumps(
        dcRole(_type_='Foo', name='Harry', act=EnumHelper(1))
    )
    data_str = '{"_type_": "Foo", "name": "Harry", "act": "LOGIN"}'
    assert data_str == data
    obj = json_utils.loads(data_str, object_hook=lambda x: dcRole(**x))
    assert obj._type_ == 'Foo'
    assert obj.__class__.__name__ == 'dcRole'
    assert obj.name == 'Harry'


def test_dump_and_load():
    """dump and load io.StringIO"""
    stream = io.StringIO()
    values = {'foo': 'bar'}
    json_utils.dump(values, stream)
    stream.seek(0)
    after = json_utils.load(stream)
    assert values == after
