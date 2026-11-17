"""What every harness step shares: paths, processes, git, the arms."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

PILOT = Path(__file__).resolve().parent.parent
ARMS = ("control", "naive", "cooperative", "strict")
EMI_ARMS = ("cooperative", "strict")
# a path that is a test, or test configuration, rather than product code
TEST_PATH = re.compile(r"(^|/)(tests?|testing)(/|$)|(^|/)test_[^/]*\.py$|_test\.py$|(^|/)conftest\.py$")

# fixed identity and dates, so a baseline commit is the same on every run
GIT_ENV = {
    "GIT_AUTHOR_NAME": "pilot",
    "GIT_AUTHOR_EMAIL": "pilot@example.invalid",
    "GIT_COMMITTER_NAME": "pilot",
    "GIT_COMMITTER_EMAIL": "pilot@example.invalid",
    "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
    "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
}


def run(cmd, cwd, env=None, timeout=900, check=False):
    """Run a command; return (exit code, stdout+stderr). A timeout is an error."""
    full = {**os.environ, **(env or {})}
    p = subprocess.run(
        cmd, cwd=cwd, env=full, capture_output=True, text=True, timeout=timeout
    )
    out = p.stdout + p.stderr
    if check and p.returncode != 0:
        raise RuntimeError(f"{cmd} exited {p.returncode}:\n{out}")
    return p.returncode, out


def git(repo, *args):
    return run(["git", *args], cwd=repo, env=GIT_ENV, check=True)[1]


def load_task(task_id):
    path = PILOT / "tasks" / task_id / "task.json"
    task = json.loads(path.read_text())
    task["id"] = task_id
    return task


def copy_tree(src, dst):
    shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True)


def candidate_diff(repo):
    """The change against the baseline, new files included. EMI's own
    configuration is left out: it differs by arm and holds no product code."""
    git(repo, "add", "-A")
    return git(repo, "diff", "--cached", "--binary", "main", "--", ".",
               ":(exclude).emi/config.json")


def write_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def files_in(patch):
    """The paths a patch changes, as its `diff --git` lines name them."""
    return re.findall(r"^diff --git a/(\S+) b/", patch, flags=re.M)


def changed_lines(patch):
    return sum(1 for line in patch.splitlines()
               if line[:1] in "+-" and not line.startswith(("+++", "---")))
