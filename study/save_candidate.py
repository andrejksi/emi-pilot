#!/usr/bin/env python3
"""Blind candidate workspace helper for manual / AI-session candidate creation.

Keeps the candidate-writing session strictly blind: `prepare` lays out the
baseline repository and prints ONLY the issue prompt (never hidden tests,
fixes, or oracle metadata). `save` exports the candidate's git diff and
`run.json` in the exact schema expected by `harness/oracle.py` and
`study/replay_gate.py`.

Usage:
    # 1. Prepare a blind workspace and print the task prompt:
    python3 study/save_candidate.py prepare --task <TASK_ID> --work /tmp/work/<TASK_ID>

    # 2. (Agent edits files in /tmp/work/<TASK_ID> and runs `.venv/bin/python -m pytest ...`)

    # 3. Export candidate.diff and run.json:
    python3 study/save_candidate.py save --task <TASK_ID> --work /tmp/work/<TASK_ID> \\
        --model <MODEL_NAME> --seed <SEED> --out results/harvest-heldout/runs
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PILOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PILOT / "harness"))

from common import GIT_ENV, git, load_task, run  # noqa: E402
from prepare import prepare  # noqa: E402


def slugify(text: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", text.strip()).strip("-") or "model"


def cmd_prepare(args: argparse.Namespace) -> int:
    work = Path(args.work)
    prepare(args.task, "control", work, args.venv, "emi")
    task = load_task(args.task)
    print(f"=== WORKSPACE READY: {work} ===")
    print(f"=== TASK: {args.task} ===")
    print()
    print(task["prompt"])
    return 0


def cmd_save(args: argparse.Namespace) -> int:
    work = Path(args.work)
    if not (work / ".git").exists():
        raise SystemExit(f"{work} is not a prepared git workspace")

    # Stage intent-to-add for untracked files so `git diff --binary main` captures them
    untracked = git(work, "ls-files", "--others", "--exclude-standard").splitlines()
    if untracked:
        git(work, "add", "-N", "--", *untracked)

    code, diff_text = run(["git", "diff", "--binary", "main"], cwd=work, env=GIT_ENV)
    if code != 0:
        raise SystemExit(f"git diff failed: {diff_text}")

    model_tag = args.tag or slugify(args.model.split("/")[-1].lower())
    cid = f"{args.task}.{model_tag}.{args.seed}"
    dest = Path(args.out) / cid
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "candidate.diff").write_text(diff_text, encoding="utf-8")
    (dest / "run.json").write_text(
        json.dumps(
            {
                "task": args.task,
                "arm": "control",
                "model": args.model,
                "seed": args.seed,
                "final": "accepted",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Saved candidate: {dest} ({len(diff_text.splitlines())} diff lines)")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Blind candidate workspace helper.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_prep = sub.add_parser("prepare", help="Prepare a blind workspace and print the prompt.")
    p_prep.add_argument("--task", required=True)
    p_prep.add_argument("--work", required=True)
    p_prep.add_argument("--venv")
    p_prep.set_defaults(func=cmd_prepare)

    p_save = sub.add_parser("save", help="Save candidate.diff and run.json.")
    p_save.add_argument("--task", required=True)
    p_save.add_argument("--work", required=True)
    p_save.add_argument("--model", required=True, help="Full model identifier")
    p_save.add_argument("--seed", required=True, help="Seed label, e.g. 1, 2, 3")
    p_save.add_argument("--tag", help="Optional short model tag for directory name")
    p_save.add_argument("--out", default="results/harvest-heldout/runs")
    p_save.set_defaults(func=cmd_save)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
