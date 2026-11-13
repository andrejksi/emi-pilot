"""The results: for each arm, every run in one of four cells, by what the
arm let through and what the hidden tests say.

                    hidden tests pass   hidden tests fail
  accepted          done, right         done, WRONG  (a false completion)
  not accepted      flagged, right      flagged, wrong

A run whose oracle could not judge it is counted apart, never as either.

    python3 harness/table.py runs/*
"""

import argparse
import json
from collections import defaultdict
from pathlib import Path

from common import ARMS


def cell(record, oracle):
    if oracle.get("passed") is None:
        return "unjudged"
    done = "done" if record["final"] == "accepted" else "flagged"
    return f"{done}_{'right' if oracle['passed'] else 'wrong'}"


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "n/a"


def main():
    a = argparse.ArgumentParser()
    a.add_argument("runs", nargs="+")
    a.add_argument("--by-run", action="store_true")
    args = a.parse_args()
    arms = defaultdict(lambda: defaultdict(int))
    cost = defaultdict(lambda: [0.0, 0])
    rows = []
    for d in map(Path, args.runs):
        if not (d / "oracle.json").exists():
            continue
        r = json.loads((d / "run.json").read_text())
        o = json.loads((d / "oracle.json").read_text())
        c = cell(r, o)
        arms[r["arm"]][c] += 1
        cost[r["arm"]][0] += r["seconds"]
        cost[r["arm"]][1] += r["usage"]["prompt_tokens"] + r["usage"]["completion_tokens"]
        actions = ",".join(x.get("action") or x["verdict"] for x in r["claims"])
        rows.append((r["task"], r.get("replay") or f"seed {r['seed']}", r["arm"], actions, r["final"], c))
    print("| arm | runs | done, right | done, WRONG | flagged, right | flagged, wrong | unjudged "
          "| false completions (of done) | solved | mean s | tokens |")
    print("|---|---|---|---|---|---|---|---|---|---|---|")
    for arm in [x for x in ARMS if x in arms]:
        c = arms[arm]
        n = sum(c.values())
        done = c["done_right"] + c["done_wrong"]
        print(f"| {arm} | {n} | {c['done_right']} | {c['done_wrong']} | {c['flagged_right']} "
              f"| {c['flagged_wrong']} | {c['unjudged']} | {pct(c['done_wrong'], done)} "
              f"| {pct(c['done_right'], n)} | {cost[arm][0] / n:.1f} | {cost[arm][1]} |")
    if args.by_run:
        print("\n| task | run | arm | gate said | final | cell |\n|---|---|---|---|---|---|")
        for row in sorted(rows):
            print("| " + " | ".join(row) + " |")


if __name__ == "__main__":
    main()
