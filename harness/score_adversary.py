"""Score an adversary's tries (emi-drafting ADVERSARY.md): each is a fix
claimed to pass the drafted rules while still being wrong.

For each try, the fix is rebuilt on a fresh baseline, and:

  rules     the drafted rules run twice; a try counts only if both pass
            (two different outcomes are evidence for neither side)
  tests     the existing tests that passed on the baseline still pass
  hidden    the task's hidden tests (oracle.py), which nobody in the loop saw
  example   what the try's example() returns on the fix and on the baseline

and gets one verdict:

  gap         valid, and the hidden tests fail: the rules let a wrong fix through
  not_wrong   valid, and the hidden tests pass: the claim is not borne out by them
  invalid     touches tests, rules or settings; does not apply; or fails a rule or test
  unclear     the rules gave different outcomes on the two runs, or a step could not run
  none        the adversary found nothing (none.md)

    python3 harness/score_adversary.py --task TASK --tries DIR [--rules DIR] [--out FILE]

DIR for --tries is emi-drafting's adversary/<task>/, whose about.json names
the rules the adversary was given; --rules overrides it.
"""

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from common import TEST_PATH, files_in, load_task, run, write_json
from oracle import RUNNER_CONFIG, judge, lay_out
from trees import code_env, environment

PYTEST = ["-m", "pytest", "-q", "-rfE", "-p", "no:cacheprovider", "-o", "addopts="]
EXAMPLE = """
import json, runpy, sys
sys.path[:0] = [".", ".emi/laws"]
print("EXAMPLE " + repr(runpy.run_path(sys.argv[1])["example"]()))
"""


def forbidden(path):
    return path.startswith(".emi/") or Path(path).name in RUNNER_CONFIG or TEST_PATH.search(path)


def failed_ids(out):
    return sorted(line.split(" ", 1)[1].split(" - ", 1)[0] for line in out.splitlines()
                  if line.startswith(("FAILED ", "ERROR ")))


class Tree:
    """The baseline, with a diff applied, the rules beside it and the task's
    environment linked in, in a directory removed afterwards."""

    def __init__(self, task, diff, rules):
        self.task, self.diff, self.rules = task, diff, rules

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        tmp = Path(self._tmp.name)
        (tmp / "run").mkdir()
        shutil.copy(self.diff, tmp / "run" / "candidate.diff")
        self.work, self.venv = tmp / "work", environment(self.task)
        self.problem = lay_out(self.task, tmp / "run", self.work)
        if not self.problem:
            (self.work / ".venv").symlink_to(self.venv)
            shutil.copytree(self.rules, self.work / ".emi" / "laws")
        return self

    def __exit__(self, *exc):
        self._tmp.cleanup()

    def python(self, args, timeout=1800):
        return run([str(self.venv / "bin" / "python"), *args], cwd=self.work,
                   env=code_env(self.task, self.work), timeout=timeout)

    def tests(self, skip=()):
        deselect = [a for t in skip for a in ("--deselect", t)]
        code, out = self.python(PYTEST + deselect + self.task["test_files"])
        return code, failed_ids(out), out[-2000:]

    def example(self, path):
        code, out = self.python(["-c", EXAMPLE, str(path.resolve())], timeout=120)
        shown = [l[len("EXAMPLE "):] for l in out.splitlines() if l.startswith("EXAMPLE ")]
        return shown[-1] if code == 0 and shown else {"raised": out[-1500:]}


def baseline(task, rules):
    """What the baseline does: which existing tests fail, and the rules' exit."""
    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / "empty.diff"
        empty.write_text("")
        with Tree(task, empty, rules) as t:
            code, failing, out = t.tests()
            if code not in (0, 1):
                raise SystemExit(f"the existing tests do not run on the baseline:\n{out}")
            rules_code, _ = t.python(PYTEST + [".emi/laws"])
            return {"failing_tests": failing, "rules_exit": rules_code}


def on_baseline(task, rules, example):
    with tempfile.TemporaryDirectory() as tmp:
        empty = Path(tmp) / "empty.diff"
        empty.write_text("")
        with Tree(task, empty, rules) as t:
            return t.example(example)


def hidden(task_id, diff):
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(diff, Path(tmp) / "candidate.diff")
        (Path(tmp) / "run.json").write_text(json.dumps({"task": task_id}))
        return judge(Path(tmp), None)


def check(task, diff, rules, before):
    """The fix's own checks: rules twice, the existing tests, its example."""
    with Tree(task, diff, rules) as t:
        if t.problem:
            return {"problem": t.problem}
        exits = [t.python(PYTEST + [".emi/laws"])[0] for _ in range(2)]
        code, failing, out = t.tests(skip=before["failing_tests"])
        example = diff.parent / "example.py"
        shown = t.example(example) if example.exists() else None
    return {"rules_exits": exits, "tests_exit": code, "tests_failing": failing,
            "tests_tail": out if code else "", "example_on_fix": shown}


def verdict(s):
    if s.get("problem") or s["bad_files"]:
        return "invalid"
    if s["rules_exits"][0] != s["rules_exits"][1]:
        return "unclear"
    if s["rules_exits"][0] != 0 or s["tests_exit"] != 0:
        return "invalid" if s["rules_exits"][0] in (0, 1) and s["tests_exit"] in (0, 1) else "unclear"
    if s["hidden"].get("passed") is None:
        return "unclear"
    return "not_wrong" if s["hidden"]["passed"] else "gap"


def score_try(task, d, rules, before):
    if (d / "none.md").exists() and not (d / "fix.diff").exists():
        return {"verdict": "none", "said": (d / "none.md").read_text()[:2000]}
    diff = d / "fix.diff"
    if not diff.exists():
        return {"verdict": "invalid", "problem": "neither fix.diff nor none.md"}
    s = {"bad_files": [p for p in files_in(diff.read_text()) if forbidden(p)]}
    s.update(check(task, diff, rules, before))
    if "problem" not in s:
        s["hidden"] = hidden(task["id"], diff)
        if (d / "example.py").exists():
            s["example_on_baseline"] = on_baseline(task, rules, d / "example.py")
    s["claim"] = (d / "claim.md").read_text()[:2000] if (d / "claim.md").exists() else None
    s["verdict"] = verdict(s)
    return s


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--task", required=True)
    a.add_argument("--tries", required=True, type=Path)
    a.add_argument("--rules", type=Path, help="default: about.json's, in the emi-drafting "
                   "checkout that holds --tries")
    a.add_argument("--out", type=Path)
    args = a.parse_args()
    task = load_task(args.task)
    rules = args.rules or (args.tries.parent.parent
                           / json.loads((args.tries / "about.json").read_text())["rules"])
    before = baseline(task, rules)
    tries = {d.name: score_try(task, d, rules, before)
             for d in sorted(p for p in args.tries.iterdir() if p.is_dir())}
    result = {"task": args.task, "rules": str(rules), "baseline": before, "tries": tries}
    write_json(args.out or args.tries / "score.json", result)
    for name, s in tries.items():
        print(f"{args.task} try {name}: {s['verdict']}"
              + (f"  example: fix {s.get('example_on_fix')} / baseline {s.get('example_on_baseline')}"
                 if s.get("example_on_fix") is not None else ""))


if __name__ == "__main__":
    main()
