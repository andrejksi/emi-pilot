import pytest

from calc import median


def test_median_odd():
    assert median([1, 2, 3]) == 2


def test_median_even():
    assert median([1, 2, 3, 4]) == 2.5


def test_median_empty():
    with pytest.raises(ValueError):
        median([])
