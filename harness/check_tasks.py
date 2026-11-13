"""Is each real task sound? From a replay's judged runs on the control arm:
the `nothing` replay must fail the oracle (the hidden tests notice that the
task is not done) and `gold-with-tests` must pass it (the real fix is
right). A task where either does not hold is broken; leave it out of live
runs. Exit 1 when any task is broken or could not be judged.

    python3 harness/check_tasks.py runs/*/
"""

import argparse
import json
import sys
from pathlib import Path

EXPECT = {"nothing": False, "gold-with-tests": True, "gold": True}


def main():
    a = argparse.ArgumentParser()
    a.add_argument("runs", nargs="+")
    args = a.parse_args()
    seen = {}
    for d in map(Path, args.runs):
        if not (d / "run.json").exists() or not (d / "oracle.json").exists():
            continue
        r = json.loads((d / "run.json").read_text())
        if r["arm"] != "control" or r.get("replay") not in EXPECT:
            continue
        o = json.loads((d / "oracle.json").read_text())
        seen.setdefault(r["task"], {})[r["replay"]] = o.get("passed")
    if not seen:
        print("no control-arm replays of real tasks to check")
        return
    bad = 0
    print("| task | nothing (must fail) | gold-with-tests (must pass) | gold | sound |")
    print("|---|---|---|---|---|")
    for task, got in sorted(seen.items()):
        sound = all(got.get(k) is v for k, v in EXPECT.items() if k != "gold")
        bad += not sound
        cells = [str(got.get(k, "missing")) for k in ("nothing", "gold-with-tests", "gold")]
        print(f"| {task} | " + " | ".join(cells) + f" | {'yes' if sound else '**NO**'} |")
    if bad:
        print(f"\n{bad} task(s) broken or not judged: fix or drop them before a live run")
        sys.exit(1)


if __name__ == "__main__":
    main()
