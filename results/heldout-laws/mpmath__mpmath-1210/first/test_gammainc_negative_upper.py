from hypothesis import given, settings, strategies as st

from mpmath import mp, mpf, exp, gammainc


def _closed_form(b):
    # integral_0^b t^2 e^-t dt = 2 - e^-b (b^2 + 2 b + 2)
    b = mpf(b)
    return 2 - exp(-b) * (b * b + 2 * b + 2)


def test_gammainc_3_0_minus_0_1_returns_the_integral():
    """New: gammainc(3, 0, -0.1) returns the integral of t^2 e^-t from 0 to -0.1 instead of raising RecursionError (A1)."""
    mp.dps = 15
    assert abs(gammainc(3, 0, -0.1) - _closed_form(-0.1)) < mpf(10) ** -14


@settings(max_examples=30, deadline=None)
@given(st.floats(min_value=-0.21518225944126573, max_value=-1e-6))
def test_gammainc_3_0_b_in_failure_region(b):
    """New: for any upper limit b between -0.21518225944126573 and 0, gammainc(3, 0, b) returns the integral of t^2 e^-t from 0 to b (A2)."""
    mp.dps = 15
    expected = _closed_form(b)
    assert abs(gammainc(3, 0, b) - expected) <= mpf(10) ** -12 * max(1, abs(expected))
