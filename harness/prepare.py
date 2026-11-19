"""Lay out one run's repository: the task's starting code committed on
`main`, EMI configured on the baseline for the EMI arms (as a person would
leave it, by `emi init --yes` plus the arm's settings), and a `task` branch.

    python3 harness/prepare.py --task calc-median --arm strict --work DIR \
        [--venv VENV] [--emi EMI]

A `dir` task needs --venv; a `git` task builds its own environment.
"""

import argparse
import json
from pathlib import Path

from common import ARMS, EMI_ARMS, PILOT, git, load_task, run
from trees import baseline_tree, environment, import_roots, test_command


def prepare(task_id, arm, work, venv, emi):
    task = load_task(task_id)
    work = Path(work)
    if work.exists() and any(work.iterdir()):
        raise SystemExit(f"{work} is not empty")
    venv = environment(task, venv)
    generated = baseline_tree(task, work) or []
    (work / ".venv").symlink_to(venv)
    git(work, "init", "-q", "-b", "main")
    # the link to the environment is never part of the change
    with open(work / ".git" / "info" / "exclude", "a") as f:
        f.write("/.venv\n")
    git(work, "add", "-A")
    if generated:
        # ignored by the project's .gitignore, but its code imports them
        git(work, "add", "-f", "--", *generated)
    git(work, "commit", "-q", "--no-verify", "-m", "baseline")
    if arm in EMI_ARMS:
        configure(work, arm, emi, task)
    git(work, "switch", "-q", "-c", "task")


def configure(work, arm, emi, task):
    state = work.parent / (work.name + ".emi-state")
    code, out = run([emi, "init", "--yes"], cwd=work, env={"XDG_STATE_HOME": str(state)})
    if code != 0:
        raise SystemExit(f"emi init failed:\n{out}")
    path = work / ".emi" / "config.json"
    config = json.loads(path.read_text())
    config["tests"]["command"] = test_command(task, work)
    if import_roots(task):
        # a src layout: EMI must run the candidate's code, not the installed copy
        config["python_path"] = import_roots(task)
    config.update(json.loads((PILOT / "arms" / f"{arm}.json").read_text()))
    path.write_text(json.dumps(config, indent=2) + "\n")
    git(work, "add", "-A")
    git(work, "commit", "-q", "--no-verify", "-m", "EMI configuration")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--task", required=True)
    a.add_argument("--arm", required=True, choices=ARMS)
    a.add_argument("--work", required=True)
    a.add_argument("--venv")
    a.add_argument("--emi", default="emi")
    args = a.parse_args()
    prepare(args.task, args.arm, args.work, args.venv, args.emi)


if __name__ == "__main__":
    main()
