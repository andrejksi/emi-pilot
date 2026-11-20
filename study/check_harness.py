#!/usr/bin/env python3
"""Known-answer checks on a replay, run before any of its numbers count.

The study's numbers are only as good as the harness that produced them.
Each check below has an answer known in advance; when the harness does not
give it, the replay measured the harness, not EMI. See EVAL_CHECKLIST.md.

    python3 study/check_harness.py --replays results/<run>/replays.jsonl

Exit 0 when every hard check holds, 1 when one fails. Warnings are printed
and do not fail the run; they are for a person to read before scoring.

Hard checks
  ceiling_catch      The ceiling (the hidden tests as laws) answers non-stop
                     to every wrong candidate.
  ceiling_blocks     The ceiling blocks at most --max-ceiling-block of the
                     right candidates. A right candidate passes the hidden
                     tests by definition; the ceiling blocking it means EMI
                     cannot run those tests faithfully.
  disagreement       The two replays of a (candidate, condition) agree.
  errors             No row is an `error` (diff did not apply, timeout,
                     no receipt).
Warnings
  pytest_baseline    Tasks whose visible tests fail with no change: plain
                     pytest blocks every candidate there, so its blocks are
                     not catches. Rows written before the baseline was
                     recorded are reported as unknown.
  unexplained        EMI rows that did not answer stop and carry no `why`.
  outcome_mix        Share of tasks whose candidates are all right or all
                     wrong: such tasks cannot show a checker telling right
                     from wrong.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

EMI_CONDITIONS = {"emi_default", "primary", "emi_unapproved_primary", "emi_unapproved_secondary", "ceiling"}
PLAIN_CONDITIONS = {"pytest", "restore", "restore_laws"}


def load(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def blocked(row: dict[str, Any]) -> bool:
    return row["action"] != "stop"


def check_ceiling(rows: list[dict[str, Any]], max_block: float,
                  network_tasks: frozenset[str] = frozenset()) -> tuple[list[str], list[str]]:
    """(failures, details) for the ceiling's two known answers.

    Tasks whose hidden tests need the network are left out: the sandbox has
    none, so the ceiling cannot hold there. They are named, never hidden.
    """
    skipped = sorted({r["task"] for r in rows if r["condition"] == "ceiling" and r["task"] in network_tasks})
    ceiling = [r for r in rows if r["condition"] == "ceiling" and r["task"] not in network_tasks]
    if not ceiling:
        return ["ceiling: no ceiling rows; the harness's main known answer was not run"], []
    failures, details = [], [f"  ceiling not judged (hidden tests need the network): {t}" for t in skipped]
    missed = sorted({r["candidate"] for r in ceiling if not r["right"] and not blocked(r)})
    if missed:
        failures.append(f"ceiling_catch: {len(missed)} wrong candidate(s) passed the hidden tests as laws")
        details.extend(f"  missed by ceiling: {c}" for c in missed)
    right = [r for r in ceiling if r["right"]]
    right_blocked = [r for r in right if blocked(r)]
    if right:
        share = len({r["candidate"] for r in right_blocked}) / len({r["candidate"] for r in right})
        if share > max_block:
            failures.append(
                f"ceiling_blocks: {share:.1%} of right candidates blocked by their own hidden tests "
                f"(allowed {max_block:.1%})"
            )
        by_task: dict[tuple[str, str, str], int] = defaultdict(int)
        for r in right_blocked:
            by_task[(r["task"], r["action"], str(r.get("cause")))] += 1
        details.extend(f"  ceiling blocked right: {t} {a} {c} x{n}" for (t, a, c), n in sorted(by_task.items()))
    return failures, details


def check_disagreement(rows: list[dict[str, Any]]) -> list[str]:
    runs: dict[tuple[str, str], set[str]] = defaultdict(set)
    for r in rows:
        runs[(r["candidate"], r["condition"])].add(r["action"])
    split = sorted(k for k, actions in runs.items() if len(actions) > 1)
    return [f"disagreement: {c} under {cond} answered differently on two replays" for c, cond in split]


def check_errors(rows: list[dict[str, Any]]) -> list[str]:
    errs: dict[tuple[str, str, str], int] = defaultdict(int)
    for r in rows:
        if r["action"] == "error":
            errs[(r["task"], r["condition"], str(r.get("cause")))] += 1
    return [f"errors: {t} {cond} {cause} x{n}" for (t, cond, cause), n in sorted(errs.items())]


def warn_pytest_baseline(rows: list[dict[str, Any]]) -> list[str]:
    status: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        if r["condition"] == "pytest":
            status[r["task"]].add(str(r.get("baseline", "unknown")))
    out = []
    failing = sorted(t for t, s in status.items() if "fail" in s or "timeout" in s)
    unknown = sorted(t for t, s in status.items() if s == {"unknown"})
    if failing:
        out.append(f"pytest_baseline: visible tests fail with no change on {len(failing)} task(s): "
                   + ", ".join(failing))
    if unknown:
        out.append(f"pytest_baseline: not recorded for {len(unknown)} task(s); plain pytest's blocks "
                   "there cannot be told from a failing baseline")
    return out


def warn_unexplained(rows: list[dict[str, Any]]) -> list[str]:
    n = sum(1 for r in rows if r["condition"] in EMI_CONDITIONS and blocked(r) and not r.get("why"))
    return [f"unexplained: {n} EMI row(s) did not answer stop and carry no reason"] if n else []


def warn_outcome_mix(rows: list[dict[str, Any]], max_uniform: float) -> list[str]:
    labels: dict[str, set[bool]] = defaultdict(set)
    for r in rows:
        labels[r["task"]].add(bool(r["right"]))
    if not labels:
        return []
    all_right = sorted(t for t, s in labels.items() if s == {True})
    all_wrong = sorted(t for t, s in labels.items() if s == {False})
    out = []
    for name, tasks in (("all right", all_right), ("all wrong", all_wrong)):
        share = len(tasks) / len(labels)
        if share > max_uniform:
            out.append(f"outcome_mix: {len(tasks)} of {len(labels)} tasks have candidates that are {name} "
                       f"({share:.0%}, more than {max_uniform:.0%})")
    return out


def run_checks(rows: list[dict[str, Any]], *, max_ceiling_block: float = 0.02,
               max_uniform: float = 1 / 3,
               network_tasks: frozenset[str] = frozenset()) -> dict[str, list[str]]:
    failures, details = check_ceiling(rows, max_ceiling_block, network_tasks)
    failures += check_disagreement(rows) + check_errors(rows)
    warnings = (warn_pytest_baseline(rows) + warn_unexplained(rows)
                + warn_outcome_mix(rows, max_uniform))
    return {"failures": failures, "warnings": warnings, "details": details}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--replays", required=True, type=Path)
    ap.add_argument("--max-ceiling-block", type=float, default=0.02)
    ap.add_argument("--max-uniform", type=float, default=1 / 3,
                    help="largest share of all-right (or all-wrong) tasks before a warning")
    ap.add_argument("--network-tasks", type=Path,
                    help="file of task ids whose hidden tests need the network (one per line, # comments)")
    args = ap.parse_args(argv)
    network: frozenset[str] = frozenset()
    if args.network_tasks:
        network = frozenset(line.strip() for line in args.network_tasks.read_text(encoding="utf-8").splitlines()
                            if line.strip() and not line.startswith("#"))
    result = run_checks(load(args.replays), max_ceiling_block=args.max_ceiling_block,
                        max_uniform=args.max_uniform, network_tasks=network)
    for line in result["failures"]:
        print(f"FAIL {line}")
    for line in result["details"]:
        print(line)
    for line in result["warnings"]:
        print(f"WARN {line}")
    if result["failures"]:
        print("The harness did not give its known answers: these replays do not count yet.")
        return 1
    print("Known answers hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
