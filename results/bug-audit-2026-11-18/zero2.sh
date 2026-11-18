. ./lib.sh
base $PWD/zero2; mkdir -p .emi/laws; cat > .emi/laws/test_vacuous.py <<'P'
from hypothesis import Phase, given, settings, strategies as st
from calc import mean


@settings(phases=[Phase.explicit])
@given(st.lists(st.integers(), min_size=1))
def test_mean_bounds_runs_nothing(xs):
    """Guard: the mean lies between the smallest and largest number."""
    assert min(xs) <= mean(xs) <= max(xs)
P
configure
# a wrong change: the mean is off by one
sed -i 's|    return sum(xs) / len(xs)|    return sum(xs) / len(xs) + 1|' calc.py
done_check
