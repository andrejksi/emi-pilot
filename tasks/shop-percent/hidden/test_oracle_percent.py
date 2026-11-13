import pytest

from shop import discounted


@pytest.mark.parametrize("percent", [-1, 101, 250])
def test_out_of_range_is_refused(percent):
    with pytest.raises(ValueError):
        discounted(100, percent)


@pytest.mark.parametrize("percent, expected", [(0, 100), (50, 50), (100, 0)])
def test_the_bounds_are_allowed(percent, expected):
    assert discounted(100, percent) == expected


def test_old_behaviour():
    assert discounted(200, 50) == 100
