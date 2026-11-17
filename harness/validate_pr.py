"""Turn mined pull requests into pilot tasks, by running them: which tests
the fix makes pass (FAIL_TO_PASS) and which pass with and without it
(PASS_TO_PASS) is read from four test runs, never assumed.

    python3 harness/validate_pr.py candidates.jsonl --out mined/ [--ids ID...]

For each candidate, the environment is built at the pull request's base
with the install steps and Python of the pilot's newest task from the same
repository. The tests the pull request adds or changes run twice with its
test changes applied and twice more with the fix applied too. A test whose
two runs disagree is no evidence and is left out of both lists. A candidate
becomes a task when 1 to 10 tests go from failing to passing and at least 5
pass throughout, the same limits import_swe.py applies to the dataset.

Each task is written in import_swe.py's layout, so plan, prepare, the
oracle and check_tasks.py read it unchanged. A replay run is still what
shows a task is sound. Every candidate gets a line in <out>/report.jsonl
saying what happened, without the fix in it.
"""

import argparse
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from common import GIT_ENV, PILOT, TEST_PATH, files_in, git, run, write_json
from oracle import ANSI, outcomes
from trees import baseline_tree, code_env, environment, mirror

RUNS = 2
TEST_FILE = re.compile(r"(^|/)test_[^/]*\.py$|_test\.py$")
# the oldest Python a project accepts, as pyproject.toml, setup.cfg or
# setup.py state it
REQUIRES_PYTHON = {
    "pyproject.toml": re.compile(r"""^\s*requires-python\s*=\s*["']\s*>=\s*3\.(\d+)""", re.M),
    "setup.cfg": re.compile(r"""^\s*python_requires\s*=\s*>=\s*3\.(\d+)""", re.M),
    "setup.py": re.compile(r"""python_requires\s*=\s*["']\s*>=\s*3\.(\d+)"""),
}


def template(repo):
    """Python and install steps of the pilot's newest task from `repo` that
    was not itself mined: a mined task's steps are borrowed ones."""
    best = None
    for f in sorted((PILOT / "tasks").glob("*/task.json")):
        t = json.loads(f.read_text())
        if (t.get("kind") == "git" and t.get("source") != "github-pr"
                and t["repo"].lower() == repo.lower()):
            if best is None or t["created_at"] > best["created_at"]:
                best = {**t, "id": f.parent.name}
    return best


def python_for(c, tmpl):
    """The template's Python, raised to the minimum the project asks for at
    the base: a repository moves on, and the template task may be a year
    older than the pull request."""
    git_dir = mirror({"repo": c["repo"], "base_commit": c["base_commit"]})
    have = int(tmpl["python"].split(".")[1])
    for name, pattern in REQUIRES_PYTHON.items():
        code, text = run(["git", "--git-dir", str(git_dir), "show",
                          f"{c['base_commit']}:{name}"], cwd=PILOT, timeout=600)
        m = pattern.search(text) if code == 0 else None
        if m:
            return f"3.{max(have, int(m.group(1)))}"
    return tmpl["python"]


def as_task(c, tmpl):
    return {
        "id": c["instance_id"], "kind": "git", "source": "github-pr", "repo": c["repo"],
        "pull": c["pull"], "issue": c["issue"], "base_commit": c["base_commit"],
        "created_at": c["merged_at"], "python": python_for(c, tmpl), "install": tmpl["install"],
        "test_files": sorted(p for p in files_in(c["test_patch"]) if TEST_FILE.search(p)),
        "prompt": c["problem_statement"].strip(), "license": tmpl.get("license"),
        "install_from": tmpl.get("id"),
    }


def run_tests(task, work, venv):
    """Each test's outcome, from one run of the task's test files."""
    present = [p for p in task["test_files"] if (work / p).exists()]
    if not present:
        return None, "none of the test files exists"
    cmd = [str(venv / "bin" / "python"), "-m", "pytest", "-rA", "--no-header", "--tb=short",
           "--color=no", "-p", "no:cacheprovider", "-W", "ignore::DeprecationWarning", *present]
    code, out = run(cmd, cwd=work, env=code_env(task, work), timeout=1800)
    seen = outcomes(ANSI.sub("", out))
    if not seen:
        return None, f"pytest reported no tests (exit {code}): {out[-500:]}"
    return seen, None


def apply(work, patch, what):
    path = work.parent / f"{what}.patch"
    path.write_text(patch)
    code, out = run(["git", "apply", "--binary", str(path)], cwd=work, env=GIT_ENV)
    return None if code == 0 else f"the {what} patch does not apply: {out[-500:]}"


def observe(task, c, venv, tmp):
    """Outcomes before and after the fix, RUNS times each, or a reason."""
    work = Path(tmp) / "work"
    baseline_tree(task, work)
    git(work, "init", "-q", "-b", "main")
    (work / ".venv").symlink_to(venv)
    sides = {}
    for side, patch in (("before", c["test_patch"]), ("after", c["patch"])):
        problem = apply(work, patch, "tests" if side == "before" else "fix")
        if problem:
            return None, problem
        sides[side] = []
        for _ in range(RUNS):
            seen, problem = run_tests(task, work, venv)
            if problem:
                return None, f"{side}: {problem}"
            sides[side].append(seen)
    return sides, None


def classify(sides):
    """FAIL_TO_PASS, PASS_TO_PASS, and how many tests disagreed with themselves."""
    tests = set().union(*sides["before"], *sides["after"])
    f2p, p2p, unstable = [], [], 0
    # what the tests did with the fix in: when nothing passes, the
    # environment is the likelier cause than the fix
    with_fix = Counter(o for run in sides["after"][:1] for o in run.values())
    for t in sorted(tests):
        before = {s.get(t) for s in sides["before"]}
        after = {s.get(t) for s in sides["after"]}
        if len(before) > 1 or len(after) > 1:
            unstable += 1
        elif after == {"PASSED"} and before == {"PASSED"}:
            p2p.append(t)
        elif after == {"PASSED"}:
            f2p.append(t)
    return f2p, p2p, unstable, dict(sorted(with_fix.items()))


def write_task(task, c, out):
    d = Path(out) / task["id"]
    shutil.rmtree(d, ignore_errors=True)
    (d / "hidden").mkdir(parents=True)
    (d / "replay").mkdir()
    write_json(d / "task.json", {k: v for k, v in task.items() if k != "id"})
    (d / "hidden" / "test.patch").write_text(c["test_patch"])
    (d / "replay" / "gold.patch").write_text(c["patch"])
    (d / "replay" / "gold-with-tests.patch").write_text(c["patch"] + c["test_patch"])
    (d / "replay" / "nothing.patch").write_text("")


def validate(c, out):
    tmpl = template(c["repo"])
    if tmpl is None:
        return {"kept": False, "why": "no pilot task from this repository to take install steps from"}
    task = as_task(c, tmpl)
    if not task["test_files"]:
        return {"kept": False, "why": "the test changes add no test file"}
    try:
        venv = environment(task)
    except (SystemExit, RuntimeError, subprocess.TimeoutExpired) as e:
        return {"kept": False, "why": f"the environment did not build: {str(e)[:500]}"}
    try:
        with tempfile.TemporaryDirectory() as tmp:
            sides, problem = observe(task, c, venv, tmp)
    except subprocess.TimeoutExpired as e:
        return {"kept": False, "why": f"the tests ran over {e.timeout:.0f} s"}
    if problem:
        return {"kept": False, "why": problem}
    f2p, p2p, unstable, after = classify(sides)
    verdict = {"fail_to_pass": len(f2p), "pass_to_pass": len(p2p), "unstable": unstable,
               "after_fix": after}
    if "PASSED" not in after:
        return {**verdict, "kept": False, "why": "no test passes with the fix: the environment"
                " is likelier broken than the fix"}
    if not 1 <= len(f2p) <= 10:
        return {**verdict, "kept": False, "why": "FAIL_TO_PASS not 1..10"}
    if len(p2p) < 5:
        return {**verdict, "kept": False, "why": "fewer than 5 PASS_TO_PASS"}
    task["oracle"] = {"fail_to_pass": f2p, "pass_to_pass": p2p}
    write_task(task, c, out)
    return {**verdict, "kept": True}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("candidates")
    a.add_argument("--out", required=True)
    a.add_argument("--ids", nargs="*")
    args = a.parse_args()
    Path(args.out).mkdir(parents=True, exist_ok=True)
    report = Path(args.out) / "report.jsonl"
    for line in Path(args.candidates).read_text().splitlines():
        c = json.loads(line)
        if args.ids and c["instance_id"] not in args.ids:
            continue
        verdict = {"instance_id": c["instance_id"], "repo": c["repo"], **validate(c, args.out)}
        with report.open("a") as f:
            f.write(json.dumps(verdict, sort_keys=True) + "\n")
        print(json.dumps(verdict, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
