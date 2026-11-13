import pytest

from shop import discounted


def test_negative_percent_is_refused():
    with pytest.raises(ValueError):
        discounted(100, -1)


def test_percent_above_100_is_refused():
    with pytest.raises(ValueError):
        discounted(100, 101)
