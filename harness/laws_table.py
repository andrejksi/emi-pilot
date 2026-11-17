"""Score the laws trial: for each version of the laws and each checker, how
many of the attempts that said done and were wrong it stopped, and how many
of those that said done and were right it stopped.

    python3 harness/laws_table.py OUT/*/result.json
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

CHECKERS = ("emi", "plain")


def verdict(side):
    """True accepted, False stopped, None could not judge."""
    return None if "error" in side else side["accept"]


def rate(n, d):
    return f"{n} of {d}" + (f" ({100 * n / d:.0f}%)" if d else "")


def summary(rows):
    out = ["| laws | checker | wrong, stopped | right, stopped | real fix, stopped | could not judge | mean s |",
           "|---|---|---|---|---|---|---|"]
    by = defaultdict(list)
    for r in rows:
        if r["said_done"] and r["right"] is not None:
            by[r["version"]].append(r)
    for version in sorted(by, key=lambda v: ("none", "first", "checked").index(v)
                          if v in ("none", "first", "checked") else 9):
        group = by[version]
        human = [r for r in group if r["model"] == "human"]
        wrong = [r for r in group if not r["right"] and r["model"] != "human"]
        right = [r for r in group if r["right"] and r["model"] != "human"]
        for c in CHECKERS:
            secs = [r[c]["seconds"] for r in group if "seconds" in r[c]]
            out.append(
                f"| {version} | {c} | {rate(sum(verdict(r[c]) is False for r in wrong), len(wrong))} "
                f"| {rate(sum(verdict(r[c]) is False for r in right), len(right))} "
                f"| {rate(sum(verdict(r[c]) is False for r in human), len(human))} "
                f"| {sum(verdict(r[c]) is None for r in group)} "
                f"| {sum(secs) / len(secs):.1f} |" if secs else f"| {version} | {c} | - | - | - | - | - |")
    return out


def disagreements(rows):
    out = ["| attempt | laws | right? | EMI | plain |", "|---|---|---|---|---|"]
    for r in sorted(rows, key=lambda r: (r["attempt"], r["version"])):
        e, p = verdict(r["emi"]), verdict(r["plain"])
        if r["said_done"] and e != p:
            out.append(f"| {r['attempt']} | {r['version']} | {'right' if r['right'] else 'WRONG'} "
                       f"| {r['emi'].get('action', 'error')} | {'accept' if p else 'stop' if p is False else 'error'} |")
    return out


def main():
    rows = [json.loads(Path(f).read_text()) for f in sys.argv[1:]]
    print("Attempts that said done; \"stopped\" is anything but accept. The real fix is\n"
          "each task's own pull request, code and tests, replayed as one more attempt.\n")
    print("\n".join(summary(rows)))
    print("\nWhere the two checkers disagree:\n")
    print("\n".join(disagreements(rows)))


if __name__ == "__main__":
    main()
