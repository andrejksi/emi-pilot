"""Rules the task adds: last() works on iterables whose __reversed__ is None."""

import tempfile
from collections.abc import Mapping
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.configuration import set_hypothesis_home_dir

from more_itertools import last

# Keep Hypothesis' storage out of the repository.
set_hypothesis_home_dir(Path(tempfile.gettempdir()) / "emi-laws-hypothesis")


class MyMapping(Mapping):
    def __getitem__(self, key):
        return 1

    def __iter__(self):
        return iter([1])

    def __len__(self):
        return 1


class NotReversible:
    """An iterable that sets __reversed__ to None, as Mapping does."""

    __reversed__ = None

    def __init__(self, items):
        self.items = list(items)

    def __iter__(self):
        return iter(self.items)


def test_last_of_the_task_mapping_is_its_last_key():
    """New: last(MyMapping()) for the Mapping subclass in the task returns 1 instead of raising ValueError."""
    assert last(MyMapping()) == 1


def test_last_of_a_class_with_reversed_none_is_its_last_item():
    """New: last() of a custom iterable whose __reversed__ is None yielding 'a', 'b', 'c' returns 'c'."""
    assert last(NotReversible(["a", "b", "c"])) == "c"


def test_default_is_not_returned_for_a_non_empty_reversed_none_iterable():
    """New: last() of a non-empty iterable whose __reversed__ is None returns its last item, not the default given."""
    assert last(NotReversible([1, 2, 3]), "default") == 3


@settings(database=None)
@given(st.lists(st.integers(), min_size=1))
def test_last_of_any_non_empty_reversed_none_iterable(items):
    """New: for any non-empty iterable whose __reversed__ is None, last() returns the item it yields last."""
    assert last(NotReversible(items)) == items[-1]
