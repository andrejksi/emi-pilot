"""The plain check: what EMI is compared against, with nothing but git and
pytest. It is the advisor's script plus the one thing a real project needs
beyond it, comparing with the tests that passed before the change.

On a candidate tree whose HEAD is the baseline (laws committed in it):
  1. put the baseline's tests, runner configuration and laws back, except
     the old tests the person listed in EXPECTED-CHANGES;
  2. run the project's tests: every test that passed at the baseline must
     pass now;
  3. run the laws with pytest: every one must pass.
"""

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from common import TEST_PATH, git, run
from oracle import RUNNER_CONFIG, put_back
from trees import code_env, test_command

LAWS = ".emi/laws"


def outcomes(task, work, args):
    """Each test's outcome ("passed", "failed", "skipped") from a pytest run,
    or None and why, when the run gave no readable result."""
    with tempfile.TemporaryDirectory() as tmp:
        report = Path(tmp) / "report.xml"
        code, out = run([*args, "--junitxml", str(report)], cwd=work,
                        env=code_env(task, work), timeout=1800)
        if code not in (0, 1) or not report.exists():
            return None, f"pytest exited {code}: {out[-1500:]}"
        seen = {}
        for case in ET.parse(report).iter("testcase"):
            kinds = {child.tag for child in case}
            state = ("failed" if kinds & {"failure", "error"} else
                     "skipped" if "skipped" in kinds else "passed")
            seen[f"{case.get('classname')}::{case.get('name')}"] = state
        return seen, out[-1500:]


def expected_changes(work):
    path = Path(work) / LAWS / "EXPECTED-CHANGES"
    lines = path.read_text().splitlines() if path.exists() else []
    return {line.strip().split("::")[0] for line in lines if line.strip()}


def restore(work):
    expected = expected_changes(work)
    changed = git(work, "status", "--porcelain", "--untracked-files=all").splitlines()
    for line in changed:
        path = line[3:].split(" -> ")[-1]
        guarded = (TEST_PATH.search(path) or Path(path).name in RUNNER_CONFIG
                   or path.startswith(".emi/"))
        if guarded and path not in expected:
            put_back(work, path)


def check(task, work, before):
    """(accept, why). `before` is the baseline's outcomes(test_command)."""
    restore(work)
    now, why = outcomes(task, work, test_command(task, work))
    if now is None:
        return False, f"the tests gave no result: {why}"
    expected = expected_changes(work)
    broken = [t for t, s in before.items() if s == "passed" and now.get(t) != "passed"
              and not any(t.startswith(e.replace("/", ".").removesuffix(".py")) for e in expected)]
    if broken:
        return False, f"{len(broken)} test(s) that passed before do not: {broken[:5]}"
    if not any(p.suffix == ".py" for p in (Path(work) / LAWS).rglob("test_*.py")):
        return True, "the tests that passed before still pass; no laws"
    laws, why = outcomes(task, work, [".venv/bin/python", "-m", "pytest", "-q",
                                      "-p", "no:cacheprovider", LAWS])
    if laws is None:
        return False, f"the laws gave no result: {why}"
    failing = [t for t, s in laws.items() if s != "passed"]
    if failing or not laws:
        return False, f"laws not passing: {failing[:5] or 'none ran'}"
    return True, f"the tests that passed before still pass, and {len(laws)} laws pass"
