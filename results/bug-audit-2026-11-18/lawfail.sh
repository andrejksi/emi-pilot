. ./lib.sh
base $PWD/lawfail; mkdir -p .emi/laws; cat > .emi/laws/test_bounds.py <<'P'
from hypothesis import given, strategies as st
from calc import mean


@given(st.lists(st.integers(-100, 100), min_size=1))
def test_mean_between_min_and_max(xs):
    """Guard: the mean lies between the smallest and largest number."""
    assert min(xs) <= mean(xs) <= max(xs)
P
configure
sed -i 's|    return sum(xs) / len(xs)|    return sum(xs) / (len(xs) - 1 or 1)|' calc.py
done_check
