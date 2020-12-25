"""
    test_util_typing
    ~~~~~~~~~~~~~~~~

    Tests util.typing functions.

    :copyright: Copyright 2007-2019 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import sys
from numbers import Integral
from typing import (Any, Callable, Dict, Generator, List, NewType, Optional, Tuple, TypeVar,
                    Union)

import pytest

from sphinx.util.typing import restify, stringify


class MyClass1:
    pass


class MyClass2(MyClass1):
    __qualname__ = '<MyClass2>'


T = TypeVar('T')
MyInt = NewType('MyInt', int)


class MyList(List[T]):
    pass


class BrokenType:
    __args__ = int


def test_restify():
    assert restify(int) == ":class:`int`"
    assert restify(str) == ":class:`str`"
    assert restify(None) == ":obj:`None`"
    assert restify(Integral) == ":class:`numbers.Integral`"
    assert restify(Any) == ":obj:`Any`"


def test_restify_type_hints_containers():
    assert restify(List) == ":class:`List`"
    assert restify(Dict) == ":class:`Dict`"
    assert restify(List[int]) == ":class:`List`\\ [:class:`int`]"
    assert restify(List[str]) == ":class:`List`\\ [:class:`str`]"
    assert restify(Dict[str, float]) == ":class:`Dict`\\ [:class:`str`, :class:`float`]"
    assert restify(Tuple[str, str, str]) == ":class:`Tuple`\\ [:class:`str`, :class:`str`, :class:`str`]"
    assert restify(Tuple[str, ...]) == ":class:`Tuple`\\ [:class:`str`, ...]"
    assert restify(List[Dict[str, Tuple]]) == ":class:`List`\\ [:class:`Dict`\\ [:class:`str`, :class:`Tuple`]]"
    assert restify(MyList[Tuple[int, int]]) == ":class:`tests.test_util_typing.MyList`\\ [:class:`Tuple`\\ [:class:`int`, :class:`int`]]"
    assert restify(Generator[None, None, None]) == ":class:`Generator`\\ [:obj:`None`, :obj:`None`, :obj:`None`]"


def test_restify_type_hints_Callable():
    assert restify(Callable) == ":class:`Callable`"

    if sys.version_info >= (3, 7):
        assert restify(Callable[[str], int]) == ":class:`Callable`\\ [[:class:`str`], :class:`int`]"
        assert restify(Callable[..., int]) == ":class:`Callable`\\ [[...], :class:`int`]"
    else:
        assert restify(Callable[[str], int]) == ":class:`Callable`\\ [:class:`str`, :class:`int`]"
        assert restify(Callable[..., int]) == ":class:`Callable`\\ [..., :class:`int`]"


def test_restify_type_hints_Union():
    assert restify(Optional[int]) == ":obj:`Optional`\\ [:class:`int`]"
    assert restify(Union[str, None]) == ":obj:`Optional`\\ [:class:`str`]"
    assert restify(Union[int, str]) == ":obj:`Union`\\ [:class:`int`, :class:`str`]"

    if sys.version_info >= (3, 7):
        assert restify(Union[int, Integral]) == ":obj:`Union`\\ [:class:`int`, :class:`numbers.Integral`]"
        assert (restify(Union[MyClass1, MyClass2]) ==
                ":obj:`Union`\\ [:class:`tests.test_util_typing.MyClass1`, :class:`tests.test_util_typing.<MyClass2>`]")
    else:
        assert restify(Union[int, Integral]) == ":class:`numbers.Integral`"
        assert restify(Union[MyClass1, MyClass2]) == ":class:`tests.test_util_typing.MyClass1`"


@pytest.mark.skipif(sys.version_info < (3, 7), reason='python 3.7+ is required.')
def test_restify_type_hints_typevars():
    T = TypeVar('T')
    T_co = TypeVar('T_co', covariant=True)
    T_contra = TypeVar('T_contra', contravariant=True)

    assert restify(T) == ":obj:`tests.test_util_typing.T`"
    assert restify(T_co) == ":obj:`tests.test_util_typing.T_co`"
    assert restify(T_contra) == ":obj:`tests.test_util_typing.T_contra`"
    assert restify(List[T]) == ":class:`List`\\ [:obj:`tests.test_util_typing.T`]"
    assert restify(MyInt) == ":class:`MyInt`"


def test_restify_type_hints_custom_class():
    assert restify(MyClass1) == ":class:`tests.test_util_typing.MyClass1`"
    assert restify(MyClass2) == ":class:`tests.test_util_typing.<MyClass2>`"


def test_restify_type_hints_alias():
    MyStr = str
    MyTuple = Tuple[str, str]
    assert restify(MyStr) == ":class:`str`"
    assert restify(MyTuple) == ":class:`Tuple`\\ [:class:`str`, :class:`str`]"  # type: ignore


@pytest.mark.skipif(sys.version_info < (3, 7), reason='python 3.7+ is required.')
def test_restify_type_ForwardRef():
    from typing import ForwardRef  # type: ignore
    assert restify(ForwardRef("myint")) == ":class:`myint`"


def test_restify_broken_type_hints():
    assert restify(BrokenType) == ':class:`tests.test_util_typing.BrokenType`'


def test_stringify():
    assert stringify(int) == "int"
    assert stringify(str) == "str"
    assert stringify(None) == "None"
    assert stringify(Integral) == "numbers.Integral"
    assert stringify(Any) == "Any"


def test_stringify_type_hints_containers():
    assert stringify(List) == "List"
    assert stringify(Dict) == "Dict"
    assert stringify(List[int]) == "List[int]"
    assert stringify(List[str]) == "List[str]"
    assert stringify(Dict[str, float]) == "Dict[str, float]"
    assert stringify(Tuple[str, str, str]) == "Tuple[str, str, str]"
    assert stringify(Tuple[str, ...]) == "Tuple[str, ...]"
    assert stringify(List[Dict[str, Tuple]]) == "List[Dict[str, Tuple]]"
    assert stringify(MyList[Tuple[int, int]]) == "tests.test_util_typing.MyList[Tuple[int, int]]"
    assert stringify(Generator[None, None, None]) == "Generator[None, None, None]"


@pytest.mark.skipif(sys.version_info < (3, 9), reason='python 3.9+ is required.')
def test_stringify_Annotated():
    from typing import Annotated  # type: ignore
    assert stringify(Annotated[str, "foo", "bar"]) == "str"  # NOQA


def test_stringify_type_hints_string():
    assert stringify("int") == "int"
    assert stringify("str") == "str"
    assert stringify(List["int"]) == "List[int]"
    assert stringify("Tuple[str]") == "Tuple[str]"
    assert stringify("unknown") == "unknown"


def test_stringify_type_hints_Callable():
    assert stringify(Callable) == "Callable"

    if sys.version_info >= (3, 7):
        assert stringify(Callable[[str], int]) == "Callable[[str], int]"
        assert stringify(Callable[..., int]) == "Callable[[...], int]"
    else:
        assert stringify(Callable[[str], int]) == "Callable[str, int]"
        assert stringify(Callable[..., int]) == "Callable[..., int]"


def test_stringify_type_hints_Union():
    assert stringify(Optional[int]) == "Optional[int]"
    assert stringify(Union[str, None]) == "Optional[str]"
    assert stringify(Union[int, str]) == "Union[int, str]"

    if sys.version_info >= (3, 7):
        assert stringify(Union[int, Integral]) == "Union[int, numbers.Integral]"
        assert (stringify(Union[MyClass1, MyClass2]) ==
                "Union[tests.test_util_typing.MyClass1, tests.test_util_typing.<MyClass2>]")
    else:
        assert stringify(Union[int, Integral]) == "numbers.Integral"
        assert stringify(Union[MyClass1, MyClass2]) == "tests.test_util_typing.MyClass1"


def test_stringify_type_hints_typevars():
    T = TypeVar('T')
    T_co = TypeVar('T_co', covariant=True)
    T_contra = TypeVar('T_contra', contravariant=True)

    if sys.version_info < (3, 7):
        assert stringify(T) == "T"
        assert stringify(T_co) == "T_co"
        assert stringify(T_contra) == "T_contra"
        assert stringify(List[T]) == "List[T]"
    else:
        assert stringify(T) == "tests.test_util_typing.T"
        assert stringify(T_co) == "tests.test_util_typing.T_co"
        assert stringify(T_contra) == "tests.test_util_typing.T_contra"
        assert stringify(List[T]) == "List[tests.test_util_typing.T]"

    assert stringify(MyInt) == "MyInt"


def test_stringify_type_hints_custom_class():
    assert stringify(MyClass1) == "tests.test_util_typing.MyClass1"
    assert stringify(MyClass2) == "tests.test_util_typing.<MyClass2>"


def test_stringify_type_hints_alias():
    MyStr = str
    MyTuple = Tuple[str, str]
    assert stringify(MyStr) == "str"
    assert stringify(MyTuple) == "Tuple[str, str]"  # type: ignore


def test_stringify_broken_type_hints():
    assert stringify(BrokenType) == 'tests.test_util_typing.BrokenType'
