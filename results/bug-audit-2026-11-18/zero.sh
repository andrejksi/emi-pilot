. ./lib.sh
base $PWD/zero; configure
mkdir -p .emi/laws; cat > .emi/laws/test_vacuous.py <<'P'
import pytest
from hypothesis import Phase, assume, given, settings, strategies as st
from calc import mean


@settings(phases=[Phase.explicit])
@given(st.lists(st.integers(), min_size=1))
def test_new_explicit_only_runs_nothing(xs):
    """New: the mean of numbers lies between their smallest and largest (A1)."""
    assert min(xs) <= mean(xs) <= max(xs)


@pytest.mark.parametrize("xs", [])
def test_new_empty_parametrize(xs):
    """New: the mean of an empty-free list is a number (A1)."""
    assert mean(xs) == mean(xs)


@given(st.integers())
def test_new_assume_everything_away(x):
    """New: the mean of one number is that number (A1)."""
    assume(x != x)
    assert mean([x]) == x


def test_new_skipped():
    """New: the mean of two equal numbers is that number (A1)."""
    pytest.skip("not today")
P
printf 'A1 written: the mean is between the smallest and largest\n' > .emi/laws/ANSWERS
XDG_STATE_HOME=$PWD/../state-zero $EMI rules check --format text > ../zero.out 2>&1; echo "rules check exit $?"
