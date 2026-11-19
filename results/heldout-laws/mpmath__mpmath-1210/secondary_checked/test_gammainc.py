from hypothesis import given, settings, strategies as st

from mpmath import almosteq, exp, gammainc, quad


def test_reported_negative_limit():
    """New: gammainc(3, 0, -0.1) evaluates the incomplete gamma integral without a recursion error (A1)."""
    assert almosteq(
        gammainc(3, 0, -0.1),
        quad(lambda t: t**2 * exp(-t), [0, -0.1]),
        abs_eps=0,
        rel_eps=1e-12,
    )


@settings(database=None, deadline=None, derandomize=True, max_examples=20)
@given(st.floats(min_value=-0.21518225944126573, max_value=0, exclude_max=True))
def test_negative_limits_in_reported_interval(upper_limit):
    """New: gammainc(3, 0, b) evaluates the incomplete gamma integral for negative b in the reported failure interval (A2)."""
    assert almosteq(
        gammainc(3, 0, upper_limit),
        quad(lambda t: t**2 * exp(-t), [0, upper_limit]),
        abs_eps=0,
        rel_eps=1e-12,
    )
