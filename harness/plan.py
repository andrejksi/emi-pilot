"""Every run of a pilot: task x arm x (replayed change | seed).

    python3 harness/plan.py replay            # one line per run
    python3 harness/plan.py chat --seeds 3 --json
    python3 harness/plan.py chat --seeds 3 --arms control   # ungated candidates only
"""

import argparse
import json

from common import ARMS, PILOT


def expand(tasks):
    """Task ids, with `@name` standing for every id in batches/name.txt."""
    out = []
    for t in tasks or []:
        if t.startswith("@"):
            f = PILOT / "batches" / f"{t[1:]}.txt"
            if not f.exists():
                raise SystemExit(f"no batch {t} (batches/{t[1:]}.txt)")
            out += f.read_text().split()
        else:
            out.append(t)
    return out


def plan(mode, seeds, tasks=None, arms=ARMS):
    out = []
    for task_dir in sorted((PILOT / "tasks").iterdir()):
        if tasks and task_dir.name not in tasks:
            continue
        if mode == "replay":
            whiches = sorted(p.name.removesuffix(".patch") for p in (task_dir / "replay").iterdir())
        else:
            whiches = [str(s) for s in range(1, seeds + 1)]
        for arm in arms:
            for which in whiches:
                out.append({"task": task_dir.name, "arm": arm, "which": which,
                            "id": f"{task_dir.name}.{arm}.{which}"})
    return out


def main():
    a = argparse.ArgumentParser()
    a.add_argument("mode", choices=("replay", "chat"))
    a.add_argument("--seeds", type=int, default=1)
    a.add_argument("--tasks", nargs="*")
    a.add_argument("--arms", nargs="+", choices=ARMS, default=list(ARMS),
                   help="arms to run, in the order given (default: every arm)")
    a.add_argument("--json", action="store_true")
    a.add_argument("--task-list", action="store_true", help="print the plan's task ids as JSON")
    a.add_argument("--max", type=int, help="refuse a plan with more runs (GitHub: 256 jobs)")
    args = a.parse_args()
    args.tasks = expand(args.tasks)
    runs = plan(args.mode, args.seeds, args.tasks, args.arms)
    if args.tasks and len({r["task"] for r in runs}) != len(set(args.tasks)):
        missing = set(args.tasks) - {r["task"] for r in runs}
        raise SystemExit(f"no such task: {' '.join(sorted(missing))}")
    if args.max and len(runs) > args.max:
        raise SystemExit(f"{len(runs)} runs is more than {args.max}: choose fewer tasks or seeds")
    if args.task_list:
        # one entry per task, for a matrix of one job per task
        print(json.dumps(sorted({r["task"] for r in runs})))
    elif args.json:
        print(json.dumps(runs))
    else:
        for r in runs:
            print(r["task"], r["arm"], r["which"])


if __name__ == "__main__":
    main()
