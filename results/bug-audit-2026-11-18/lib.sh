S=/tmp/claude-0/-home-user/5eb0ad45-fb5d-502b-baac-1e9e75db553c/scratchpad
EMI=/home/user/EMI/target/release/emi
G="git -c user.name=t -c user.email=t@t -c commit.gpgsign=false"
base() { # $1 dir
  mkdir -p $1/tests && cd $1 && git init -q -b main
  cat > calc.py <<'P'
def add(a, b):
    return a + b


def mean(xs):
    return sum(xs) / len(xs)
P
  cat > tests/test_calc.py <<'P'
from calc import add, mean


def test_add():
    assert add(2, 3) == 5


def test_mean():
    assert mean([1, 2, 3]) == 2
P
  ln -s $S/pyenv .venv; echo "/.venv" >> .git/info/exclude
}
configure() { # after project files written
  $G add -A && $G commit -qm base
  XDG_STATE_HOME=$PWD/../state-$(basename $PWD) $EMI init --yes >/dev/null 2>&1 || echo "init failed"
  python3 - <<'P'
import json; p=".emi/config.json"; c=json.load(open(p))
c["tests"]["command"]=[".venv/bin/python","-m","pytest","-q","tests"]; c["link"]=[".venv"]; c["python_path"]=["."]
json.dump(c,open(p,"w"),indent=2)
P
  $G add -A && $G commit -qm emi && $G switch -qc task
}
done_check() {
  XDG_STATE_HOME=$PWD/../state-$(basename $PWD) timeout 900 $EMI done --format text > ../$(basename $PWD).out 2>&1; echo "$(basename $PWD): exit $?"
  grep -m1 -E "^Action:" ../$(basename $PWD).out
}
