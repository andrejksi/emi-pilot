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
    # read-tree -u fetches the clone's missing file contents in one batch;
    # checkout-index fetched them one request per file, over 30 minutes
    # for litellm's 16,000 files
    try:
        run(base + ["read-tree", "--reset", "-u", task["base_commit"]], cwd=dst, env=env,
            check=True, timeout=1800)
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
        (home / "roots.txt").write_text("".join(f"{r}\n" for r in _probe_roots(venv, src)))
        ready.write_text("ok\n")
    return venv


# Run by the environment's own Python, isolated (-I) and from `/`, so only
# the installed packages answer: where does each editable install of the
# project import its code from, relative to the source it was installed from?
_ROOTS_PROBE = r"""
import importlib.metadata as md, importlib.util, json, pathlib, sys
src = pathlib.Path(sys.argv[1]).resolve()
found = set()
def note(path):
    p = pathlib.Path(path).resolve()
    if p.is_file():
        p = p.parent
    if src in p.parents or p == src:
        found.add(str(p.relative_to(src)))
for d in md.distributions():
    info = json.loads(d.read_text("direct_url.json") or "{}")
    if not info.get("dir_info", {}).get("editable"):
        continue
    names = set((d.read_text("top_level.txt") or "").split())
    for f in d.files or []:
        if f.suffix == ".pth":
            for line in (d.locate_file(f).read_text().splitlines()):
                if line and not line.startswith(("#", "import")):
                    note(line.strip())
        elif len(f.parts) > 1 and not f.parts[0].endswith(".dist-info"):
            names.add(f.parts[0])
    for n in names:
        try:
            spec = importlib.util.find_spec(n)
        except Exception:
            continue
        if spec and spec.submodule_search_locations:
            for loc in spec.submodule_search_locations:
                note(pathlib.Path(loc).parent)
        elif spec and spec.origin and spec.origin.endswith(".py"):
            note(spec.origin)
print("\n".join(sorted(r for r in found if r != ".")))
"""


def _probe_roots(venv, src):
    """The directories, other than the repository root, that the project's
    code is imported from (`src` for a src layout)."""
    code, out = run([str(venv / "bin" / "python"), "-I", "-c", _ROOTS_PROBE, str(src)], cwd="/")
    if code != 0:
        raise SystemExit(f"could not read where the project imports from:\n{out[-2000:]}")
    return [line for line in out.splitlines() if line.strip()]


def import_roots(task):
    """The project's import roots under the repository root, relative. An
    editable install points the environment at the source it was built
    from, not at a run's copy; with these first on PYTHONPATH, every test
    run (the agent's, the gates', EMI's, the oracle's) runs the run's code.
    The repository root itself needs nothing: `python -m pytest` puts the
    working directory first."""
    if task.get("kind", "dir") == "dir":
        return []
    home = CACHE / "envs" / task["id"]
    roots = home / "roots.txt"
    if not roots.exists():
        roots.write_text("".join(f"{r}\n" for r in _probe_roots(home / "venv", home / "src")))
    return [r for r in roots.read_text().splitlines() if r]


def code_env(task, work):
    """PYTHONPATH for a test run in `work`, or nothing when the project
    needs none."""
    roots = import_roots(task)
    return {"PYTHONPATH": ":".join(str(Path(work).resolve() / r) for r in roots)} if roots else {}


def test_command(task, work=None):
    """The command that runs the task's visible tests, from the repository root.

    When `work` is given, any test file that does not exist in `work` (for
    example a brand-new test file added only by a hidden patch) is omitted so
    baseline runs do not fail with pytest exit 4.
    """
    if task.get("kind", "dir") == "dir":
        return [".venv/bin/python", "-m", "pytest", "-q"]
    files = list(task["test_files"])
    if work is not None:
        w = Path(work)
        present = [p for p in files if (w / p).exists()]
        if present:
            files = present
    return [".venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider", *files]


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
