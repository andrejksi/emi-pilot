"""Rules a person approved with `emi rules approve` before an earlier task."""

import pytest

from shop import total


def test_an_empty_cart_totals_zero():
    """Guard: an empty cart totals zero."""
    assert total([]) == 0


def test_a_negative_price_is_refused():
    """Guard: a negative price is refused with ValueError."""
    with pytest.raises(ValueError):
        total([3, -1])
