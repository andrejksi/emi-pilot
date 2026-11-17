"""The laws trial: judge saved attempts with EMI and with the plain check,
under each version of a task's laws, so both checkers see the same change
and the same laws. No model runs; what each attempt really was is already
in its oracle.json.

    python3 harness/replay_laws.py --task T --attempts results/harvest-tuning/runs \
        --laws results/laws-trial/drafts/T/laws --out OUT --emi EMI [--venv VENV]

Versions: `none` (no laws), and each subdirectory of --laws (`first`, the
draft as first written; `checked`, as `emi rules check` last passed it).
Writes OUT/<attempt>.<version>/result.json and EMI's receipt beside it.
"""

import argparse
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

import plain_check
from common import GIT_ENV, copy_tree, git, load_task, run, write_json
from gates import emi as emi_gate
from prepare import prepare
from trees import test_command


def base_tree(task_id, laws, dst, venv, emi):
    """The baseline as an EMI arm has it, with these laws committed on it,
    so that the laws are the baseline's: a person's, not the change's."""
    prepare(task_id, "cooperative", dst, venv, emi)
    if laws:
        copy_tree(laws, dst / plain_check.LAWS)
        git(dst, "add", "-A")
        git(dst, "commit", "-q", "--no-verify", "-m", "laws, approved before coding")
        git(dst, "branch", "-f", "main", "HEAD")


def attempts_of(root, task_id):
    for d in sorted(Path(root).iterdir()):
        r = json.loads((d / "run.json").read_text())
        if r["task"] == task_id and (d / "oracle.json").exists():
            yield d, r, json.loads((d / "oracle.json").read_text())


def candidate(base, attempt, dst):
    copy_tree(base, dst)
    diff = attempt / "candidate.diff"
    if diff.stat().st_size:
        code, out = run(["git", "apply", "--binary", str(diff.resolve())], cwd=dst, env=GIT_ENV)
        if code != 0:
            return f"the diff does not apply: {out[-1000:]}"
    return None


def judge_emi(base, attempt, work, ctx):
    """EMI as the study's cooperative arm runs it: `emi done`, with the
    pilot's fixed reviewer playing the person when EMI asks one."""
    problem = candidate(base, attempt, work)
    if problem:
        return {"error": problem}
    started = time.monotonic()
    verdict, _, record = emi_gate(work, ctx)
    seconds = round(time.monotonic() - started, 1)
    if "action" not in record:
        return {"error": record.get("error", "no receipt"), "seconds": seconds}
    receipt = json.loads((Path(ctx["out_dir"]) / record["receipt"]).read_text())
    return {"action": record["action"], "accept": verdict == "accepted",
            "reviewer": record.get("reviewer"), "repair": receipt.get("repair", [])[:5],
            "receipt": record["receipt"], "seconds": seconds}


def judge_plain(task, base, attempt, work, before):
    problem = candidate(base, attempt, work)
    if problem:
        return {"error": problem}
    started = time.monotonic()
    accept, why = plain_check.check(task, work, before)
    return {"accept": accept, "why": why, "seconds": round(time.monotonic() - started, 1)}


def replay(args, task, version, laws, tmp):
    base = tmp / f"base-{version}"
    base_tree(args.task, laws, base, args.venv, args.emi)
    before, why = plain_check.outcomes(task, base, test_command(task))
    for attempt, record, oracle in attempts_of(args.attempts, args.task):
        out = Path(args.out) / f"{attempt.name}.{version}"
        out.mkdir(parents=True, exist_ok=True)
        ctx = {"emi": args.emi, "out_dir": str(out), "task": task}
        emi = judge_emi(base, attempt, tmp / f"{attempt.name}.{version}.emi", ctx)
        plain = (judge_plain(task, base, attempt, tmp / f"{attempt.name}.{version}.plain", before)
                 if before is not None else {"error": f"the baseline's tests gave no result: {why}"})
        write_json(out / "result.json", {
            "attempt": attempt.name, "task": args.task, "model": record.get("model"),
            "version": version, "laws": sorted(str(p.relative_to(laws)) for p in Path(laws).rglob("*")
                                               if p.is_file()) if laws else [],
            "said_done": record["final"] == "accepted", "right": oracle.get("passed"),
            "emi": emi, "plain": plain,
        })
        for side in ("emi", "plain"):
            shutil.rmtree(tmp / f"{attempt.name}.{version}.{side}", ignore_errors=True)
            shutil.rmtree(tmp / f"{attempt.name}.{version}.{side}.emi-state", ignore_errors=True)


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--task", required=True)
    a.add_argument("--attempts", required=True)
    a.add_argument("--laws", help="directory of law versions, one subdirectory each")
    a.add_argument("--out", required=True)
    a.add_argument("--emi", default="emi")
    a.add_argument("--venv")
    a.add_argument("--versions", nargs="*", help="only these versions")
    args = a.parse_args()
    task = load_task(args.task)
    versions = [("none", None)]
    if args.laws and Path(args.laws).exists():
        versions += [(d.name, d) for d in sorted(Path(args.laws).iterdir()) if d.is_dir()]
    if args.versions:
        versions = [(n, d) for n, d in versions if n in args.versions]
    # the runner's scratch space when it gives one (WORK), not /tmp
    with tempfile.TemporaryDirectory(dir=os.environ.get("WORK")) as tmp:
        for name, laws in versions:
            replay(args, task, name, laws, Path(tmp))


if __name__ == "__main__":
    main()
