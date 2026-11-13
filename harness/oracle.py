"""Judge one run's final change with the task's hidden tests, which neither
the agent nor EMI ever saw.

The change is rebuilt from its diff on a fresh baseline, so the oracle needs
nothing from the agent's machine. Runner configuration the change edited
(conftest.py, pytest.ini, ...) is put back as the baseline had it: the hidden
tests run under the project's settings, not under settings the agent wrote.

  dir task  tasks/<id>/hidden/ is copied in and run whole.
  git task  the hidden test patch is applied over the baseline's versions of
            the test files it touches, and every FAIL_TO_PASS and
            PASS_TO_PASS test must pass.

    python3 harness/oracle.py --run runs/<run>... [--venv VENV]
"""

import argparse
import json
import re
import shutil
import tempfile
from pathlib import Path

from common import GIT_ENV, PILOT, git, load_task, run, write_json
from trees import baseline_tree, environment

RUNNER_CONFIG = ("pytest.ini", "tox.ini", "setup.cfg", "pyproject.toml", "conftest.py")
STATUSES = ("PASSED", "FAILED", "ERROR", "XFAIL", "XPASS", "SKIPPED")
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def lay_out(task, run_dir, work):
    baseline_tree(task, work)
    git(work, "init", "-q", "-b", "main")
    git(work, "add", "-A")
    git(work, "commit", "-q", "--no-verify", "-m", "baseline")
    diff = run_dir / "candidate.diff"
    if diff.stat().st_size:
        code, out = run(["git", "apply", "--binary", str(diff.resolve())], cwd=work, env=GIT_ENV)
        if code != 0:
            return f"the diff does not apply: {out[-1000:]}"
    changed = git(work, "status", "--porcelain", "--untracked-files=all").splitlines()
    for line in changed:
        path = line[3:]
        if Path(path).name in RUNNER_CONFIG:
            put_back(work, path)
    return None


def put_back(work, path):
    """The baseline's version of a file, or no file if the baseline had none."""
    code, _ = run(["git", "cat-file", "-e", f"HEAD:{path}"], cwd=work)
    if code == 0:
        git(work, "checkout", "HEAD", "--", path)
    else:
        (Path(work) / path).unlink(missing_ok=True)


def judge_dir(task, work, venv):
    for p in list(work.rglob("conftest.py")):
        p.unlink()
    shutil.copytree(PILOT / "tasks" / task["id"] / "hidden", work / "_oracle")
    cmd = [str(venv / "bin" / "python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", "_oracle"]
    code, out = run(cmd, cwd=work, timeout=900)
    # pytest: 0 all passed, 1 some failed; anything else is not a verdict
    if code not in (0, 1):
        return {"passed": None, "exit": code, "error": out[-2000:]}
    return {"passed": code == 0, "exit": code, "output": out[-2000:]}


def judge_git(task, work, venv):
    patch = PILOT / "tasks" / task["id"] / "hidden" / "test.patch"
    touched = re.findall(r"^diff --git a/(\S+) b/", patch.read_text(), flags=re.M)
    for path in touched:
        put_back(work, path)
    code, out = run(["git", "apply", "--binary", str(patch)], cwd=work)
    if code != 0:
        return {"passed": None, "error": f"the hidden tests do not apply: {out[-1000:]}"}
    wanted = task["oracle"]["fail_to_pass"] + task["oracle"]["pass_to_pass"]
    cmd = [str(venv / "bin" / "python"), "-m", "pytest", "-rA", "--no-header", "--tb=short",
           "--color=no", "-p", "no:cacheprovider", "-W", "ignore::DeprecationWarning",
           *task["test_files"]]
    code, out = run(cmd, cwd=work, timeout=1800)
    out = ANSI.sub("", out)
    seen = outcomes(out)
    if not seen:
        return {"passed": None, "exit": code, "error": out[-3000:]}
    failing = [t for t in wanted if seen.get(t) != "PASSED"]
    f2p = task["oracle"]["fail_to_pass"]
    verdict = {"passed": not failing, "exit": code,
               "fail_to_pass_passed": sum(seen.get(t) == "PASSED" for t in f2p),
               "fail_to_pass": len(f2p),
               "not_passing": failing[:20], "not_passing_count": len(failing)}
    if failing:
        # why, for whoever checks that the task itself is sound
        verdict["failure_lines"] = [l for l in out.splitlines()
                                    if l.startswith(("FAILED", "ERROR"))][:20]
        verdict["output_tail"] = out[-4000:]
    return verdict


def outcomes(out):
    """Each test's outcome from pytest's -rA summary, keyed as the dataset
    keys it: the id up to its first space (an id with a space in a parameter
    is cut there). Tests that share such a key pass only if all of them do."""
    seen = {}
    for line in out.splitlines():
        words = line.split()
        if len(words) < 2 or words[0] not in STATUSES:
            continue
        key, status = words[1], words[0]
        if seen.get(key, "PASSED") != "PASSED":
            continue
        seen[key] = status
    return seen


def judge(run_dir, venv):
    record = json.loads((run_dir / "run.json").read_text())
    task = load_task(record["task"])
    env = environment(task, venv)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "work"
        problem = lay_out(task, run_dir, work)
        if problem:
            return {"passed": None, "error": problem}
        (work / ".venv").symlink_to(env)
        if task.get("kind", "dir") == "dir":
            return judge_dir(task, work, env)
        return judge_git(task, work, env)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--run", required=True, nargs="+", help="run directories")
    a.add_argument("--venv", help="the virtualenv for dir tasks")
    args = a.parse_args()
    for d in args.run:
        d = Path(d)
        if not (d / "run.json").exists():
            print(f"{d.name}: no run record (the run failed); not judged")
            continue
        verdict = judge(d, args.venv)
        write_json(d / "oracle.json", verdict)
        print(f"{d.name}: {verdict['passed']}")


if __name__ == "__main__":
    main()
