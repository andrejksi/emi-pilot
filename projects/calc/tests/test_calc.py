import pytest

from calc import add, clamp, mean


def test_add():
    assert add(1, 2) == 3


def test_mean():
    assert mean([1, 2, 3]) == 2


def test_mean_of_nothing():
    with pytest.raises(ValueError):
        mean([])


def test_clamp():
    assert clamp(5, 0, 3) == 3
    assert clamp(-1, 0, 3) == 0
