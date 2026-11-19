"""last() behaviour that already holds and must keep holding."""

from collections.abc import Mapping

import pytest

from more_itertools import last


class NotReversible:
    __reversed__ = None

    def __init__(self, items):
        self.items = list(items)

    def __iter__(self):
        return iter(self.items)


class OneItemMapping(Mapping):
    def __getitem__(self, key):
        return 1

    def __iter__(self):
        return iter([1])

    def __len__(self):
        return 1


def test_last_of_a_list():
    """Guard: last([0, 1, 2, 3]) returns 3."""
    assert last([0, 1, 2, 3]) == 3


def test_last_of_an_empty_list_with_default():
    """Guard: last([], 'some default') returns 'some default'."""
    assert last([], "some default") == "some default"


def test_last_of_an_empty_iterable_without_default_raises():
    """Guard: last([]) with no default raises ValueError."""
    with pytest.raises(ValueError):
        last([])


def test_last_of_an_iterator_over_the_mapping():
    """Guard: last(iter(MyMapping())) returns 1, as the task says it already does."""
    assert last(iter(OneItemMapping())) == 1


def test_last_of_a_reversible_non_sequence():
    """Guard: last() of a dict, which is reversible but not a sequence, returns its last key."""
    assert last({"a": 1, "b": 2, "c": 3}) == "c"


def test_last_of_a_generator():
    """Guard: last() of a generator returns the item it yields last."""
    assert last(x * x for x in range(5)) == 16


def test_an_empty_reversed_none_iterable_gives_the_default():
    """Guard: last() of an empty iterable whose __reversed__ is None returns the default given."""
    assert last(NotReversible([]), "d") == "d"


def test_an_empty_reversed_none_iterable_without_default_raises():
    """Guard: last() of an empty iterable whose __reversed__ is None, with no default, raises ValueError."""
    with pytest.raises(ValueError):
        last(NotReversible([]))
