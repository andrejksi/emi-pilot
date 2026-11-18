. ./lib.sh
fix() { # a correct change: mean of an empty list is 0, with its test
  python3 - <<'P'
p="calc.py"; s=open(p).read().replace("    return sum(xs) / len(xs)","    if not xs:\n        return 0\n    return sum(xs) / len(xs)"); open(p,"w").write(s)
P
}
newtest() { cat >> $1 <<'P'


def test_mean_empty():
    assert mean([]) == 0
P
}
case $1 in
clash) base $PWD/clash; mkdir -p .emi/laws; cat > .emi/laws/test_calc.py <<'P'
from calc import mean


def test_mean_of_one():
    """Guard: the mean of one number is that number."""
    assert mean([4]) == 4
P
  configure; fix; newtest tests/test_calc.py; done_check;;
plugin) base $PWD/plugin; printf '[pytest]\naddopts = -p myplug\n' > pytest.ini; cat > myplug.py <<'P'
import pytest


@pytest.fixture
def two():
    return 2
P
  cat >> tests/test_calc.py <<'P'


def test_two(two):
    assert add(two, two) == 4
P
  configure; fix; newtest tests/test_calc.py; done_check;;
plugins_var) base $PWD/plugins_var; mkdir -p tests/helpers; touch tests/__init__.py tests/helpers/__init__.py; cat > tests/helpers/fx.py <<'P'
import pytest


@pytest.fixture
def three():
    return 3
P
  printf 'pytest_plugins = ["tests.helpers.fx"]\n' > conftest.py
  cat >> tests/test_calc.py <<'P'


def test_three(three):
    assert add(three, 0) == 3
P
  configure; fix; newtest tests/test_calc.py; done_check;;
renamed) base $PWD/renamed; configure; fix; git mv -q tests/test_calc.py tests/test_calculator.py; newtest tests/test_calculator.py; done_check;;
renamed_fn) base $PWD/renamed_fn; configure; fix; sed -i 's/def test_add/def test_addition/' tests/test_calc.py; newtest tests/test_calc.py; done_check;;
hyp) base $PWD/hyp; mkdir -p .emi/laws; cat > .emi/laws/test_mean_bounds.py <<'P'
from hypothesis import given, strategies as st
from calc import mean


@given(st.lists(st.integers(-100, 100), min_size=1))
def test_mean_between_min_and_max(xs):
    """Guard: the mean lies between the smallest and largest number."""
    assert min(xs) <= mean(xs) <= max(xs)
P
  configure; fix; newtest tests/test_calc.py; done_check; ls -a | grep -i hypo || echo "no .hypothesis in the repository";;
quiet) base $PWD/quiet; printf '[pytest]\naddopts = -qq --tb=no -p no:warnings -x\n' > pytest.ini; configure; fix; newtest tests/test_calc.py; done_check;;
slow) base $PWD/slow; python3 - <<'P'
lines=["import time","from calc import add",""]
for i in range(30):
    lines += [f"def test_slow_{i}():","    time.sleep(1)","    assert add(1, 1) == 2",""]
open("tests/test_slow.py","w").write("\n".join(lines))
P
  configure; fix; newtest tests/test_calc.py; start=$(date +%s); done_check; echo "took $(( $(date +%s)-start )) s";;
esac
