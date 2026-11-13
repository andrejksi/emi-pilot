from hypothesis import given, strategies as st

from calc import add, clamp


@given(st.integers(), st.integers())
def test_add_is_the_sum(a, b):
    assert add(a, b) == a + b


@given(st.integers(), st.integers(), st.integers())
def test_clamp_stays_in_range(x, low, high):
    if low <= high:
        assert low <= clamp(x, low, high) <= high
