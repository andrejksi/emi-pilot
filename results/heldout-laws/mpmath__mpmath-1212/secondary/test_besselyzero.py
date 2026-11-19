import pytest

from mpmath import fp, mp


def test_fp_besselyzero_returns_first_positive_zero_for_order_two():
    """New: fp.besselyzero(2, 1) returns 3.3842417671495935, the "1st positive zero of the 2nd degree Bessel function of the second kind" (A1)."""
    assert fp.besselyzero(2, 1) == pytest.approx(3.3842417671495935, rel=1e-12)


def test_mp_besselyzero_preserves_first_positive_zero_for_order_two():
    """Guard: mp.besselyzero(2, 1) still "returns the proper result" of 3.3842417671495935 (A2)."""
    assert mp.besselyzero(2, 1) == pytest.approx(3.3842417671495935, rel=1e-12)
