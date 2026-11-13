import pytest

from calc import median


def test_odd_count():
    assert median([3, 1, 2]) == 2


def test_even_count():
    assert median([4, 1, 3, 2]) == 2.5


def test_one_value():
    assert median([5]) == 5


def test_empty_is_refused():
    with pytest.raises(ValueError):
        median([])


def test_the_input_is_left_alone():
    values = [3, 1, 2]
    median(values)
    assert values == [3, 1, 2]
