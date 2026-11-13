"""Where a task's starting code and its Python environment come from.

Two kinds of task:
  dir  a project under projects/ and the virtualenv the caller gives
  git  a real repository at a commit (imported from SWE-rebench-V2 or mined
       from pull requests), with an environment built once per task from
       the task's install steps and kept in the cache

A git task's tree is written without its history: the agent gets one
commit, so it cannot find the fix in a later commit or a remote branch.
"""

import fcntl
import os
import re
import shlex
import shutil
from pathlib import Path

from common import PILOT, copy_tree, git, run

CACHE = Path(os.environ.get("PILOT_CACHE", PILOT / ".cache"))
# what EMI needs in every environment, beside the project's own packages
EMI_NEEDS = ["pytest>=8,<9", "coverage>=7.9,<8", "hypothesis>=6,<7"]
RUNNER_FLAGS_WITH_VALUE = {"-p", "-W", "-k", "-m", "-o", "-c", "--rootdir", "--deselect", "--ignore"}


class Locked:
    """One process at a time builds a given cache entry."""

    def __init__(self, path):
        self.path = Path(str(path) + ".lock")

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.path, "w")
        fcntl.flock(self.f, fcntl.LOCK_EX)

    def __exit__(self, *exc):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()


def mirror(task):
    """A blobless clone of the task's repository, with the base commit in it."""
    slug = task["repo"].replace("/", "__")
    git_dir = CACHE / "repos" / f"{slug}.git"
    with Locked(git_dir):
        if not git_dir.exists():
            run(["git", "clone", "-q", "--bare", "--filter=blob:none",
                 f"https://github.com/{task['repo']}.git", str(git_dir)], cwd=CACHE, check=True,
                timeout=1800)
        code, _ = run(["git", "--git-dir", str(git_dir), "cat-file", "-e",
                       f"{task['base_commit']}^{{commit}}"], cwd=CACHE)
        if code != 0:
            run(["git", "--git-dir", str(git_dir), "fetch", "-q", "origin", task["base_commit"]],
                cwd=CACHE, check=True, timeout=1800)
    return git_dir


def baseline_tree(task, dst):
    """Write the task's starting code into dst (which must be empty)."""
    dst = Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    if task.get("kind", "dir") == "dir":
        copy_tree(PILOT / "projects" / task["project"], dst)
        return
    git_dir = mirror(task)
    index = dst.parent / (dst.name + ".index")
    env = {"GIT_INDEX_FILE": str(index)}  # its own index: tasks can be laid out side by side
    base = ["git", "--git-dir", str(git_dir), "--work-tree", str(dst)]
    try:
        run(base + ["read-tree", task["base_commit"]], cwd=dst, env=env, check=True, timeout=1800)
        run(base + ["checkout-index", "-a", "-f"], cwd=dst, env=env, check=True, timeout=1800)
    finally:
        index.unlink(missing_ok=True)
    return copy_generated(task, dst)


def copy_generated(task, dst):
    """The Python files the task's install generated beside its source (a
    `_version.py` written by setuptools-scm, say), copied into dst as a
    checkout that was installed would have them. Returns their paths."""
    home = CACHE / "envs" / task["id"]
    listing = home / "generated.txt"
    if not listing.exists():
        return []
    paths = listing.read_text().split()
    for rel in paths:
        target = Path(dst) / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(home / "src" / rel, target)
    return paths


def environment(task, given_venv=None):
    """The virtualenv a task's tests run in."""
    if task.get("kind", "dir") == "dir":
        if not given_venv:
            raise SystemExit("this task needs --venv")
        return Path(given_venv).resolve()
    home = CACHE / "envs" / task["id"]
    venv, src, ready = home / "venv", home / "src", home / ".ready"
    with Locked(home):
        if ready.exists():
            return venv
        shutil.rmtree(home, ignore_errors=True)
        baseline_tree(task, src)
        # some builds read their version from git (setuptools-scm); give the
        # source one commit and no tags, so they find a development version
        for args in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--no-verify", "-m", "baseline"]):
            git(src, *args)
        uv = shutil.which("uv")
        if not uv:
            raise SystemExit("git tasks need uv (pip install uv) to make a Python "
                             f"{task['python']} environment")
        run([uv, "venv", "-q", "--seed", "--python", task["python"], str(venv)], cwd=home,
            check=True, timeout=1800)
        path_env = {"PATH": f"{venv / 'bin'}:{os.environ['PATH']}", "VIRTUAL_ENV": str(venv)}
        for step in task["install"]:
            # the dataset's `pip install ...` steps, through uv's installer:
            # the same packages, resolved many times faster than pip does
            fast = re.sub(r"^\s*pip install", f"{shlex.quote(uv)} pip install", step)
            code, out = run(["bash", "-c", fast], cwd=src, env=path_env, timeout=3600)
            if code != 0:
                raise SystemExit(f"install step failed: {step}\n{out[-3000:]}")
        run([uv, "pip", "install", "-q", *EMI_NEEDS], cwd=src, env=path_env, check=True,
            timeout=1800)
        # files the install wrote beside the source that git ignores: a
        # generated module the code imports must be in every run's copy too
        _, ignored = run(["git", "ls-files", "--others", "--ignored", "--exclude-standard",
                          "--", "*.py"], cwd=src, check=True)
        generated = [f for f in ignored.split() if not f.startswith(("build/", ".")) and "/." not in f]
        (home / "generated.txt").write_text("\n".join(generated) + "\n")
        ready.write_text("ok\n")
    return venv


def test_command(task):
    """The command that runs the task's visible tests, from the repository root."""
    if task.get("kind", "dir") == "dir":
        return [".venv/bin/python", "-m", "pytest", "-q"]
    return [".venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *task["test_files"]]


def test_files(test_cmd):
    """The paths a dataset's `pytest ...` command names, without its flags."""
    words = shlex.split(test_cmd)[1:]
    files, skip = [], False
    for w in words:
        if skip:
            skip = False
        elif w in RUNNER_FLAGS_WITH_VALUE:
            skip = True
        elif not w.startswith("-"):
            files.append(w)
    return files
