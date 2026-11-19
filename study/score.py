#!/usr/bin/env python3
"""Score the laws study from committed raw records (see study/gate.md).

Usage:
    python3 study/score.py --replays PATH [--approvals PATH] \\
        [--primary-drafter MODEL] [--primary-condition NAME] \\
        [--restore-condition NAME] [--resamples 10000] \\
        [--json OUT.json] [--md OUT.md]

Input formats:
  replays.jsonl: one JSON object per replay run, with keys:
    - candidate: str (unique candidate id)
    - task: str (task id, used for task-cluster bootstrap)
    - model: str (candidate producer model)
    - right: bool (ground-truth label from hidden tests)
    - condition: str (e.g. pytest, restore, emi_default, restore_laws,
                      emi_unapproved_primary, emi_unapproved_secondary,
                      primary, ceiling)
    - action: str ("stop", "repair", "ask_person", "incomplete", "error")
    - run: int (optional; 0/1 for double replay)
    - cause: str (optional; part of EMI that caused a non-stop verdict)
    - stage: str (optional; for slipped wrong changes on primary:
                  "no_law_drafted", "dropped_by_rules_check",
                  "dropped_at_approval", "law_in_force_still_stop")

  approvals.jsonl (optional): one JSON object per task approval:
    - task: str
    - approver: str
    - minutes: float
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

BOOTSTRAP_SEED = 20261117
DEFAULT_RESAMPLES = 10_000
DEFAULT_PRIMARY_DRAFTER = "moonshotai/Kimi-K3.1-Pro"
STAGES = (
    "no_law_drafted",
    "dropped_by_rules_check",
    "dropped_at_approval",
    "law_in_force_still_stop",
)
FIXABLE_STAGES = {"no_law_drafted", "dropped_by_rules_check"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as fh:
        for lineno, raw in enumerate(fh, 1):
            line = raw.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"{path}:{lineno}: invalid JSON: {exc}") from exc
    return rows


def collapse_replays(
    rows: list[dict[str, Any]],
) -> tuple[dict[tuple[str, str], dict[str, Any]], int]:
    """Collapse double-replay runs per (candidate, condition).

    Per study/gate.md: a candidate whose two runs disagree counts for neither
    side. Returns (agreed_map, disagreed_count).
    """
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = (str(row["candidate"]), str(row["condition"]))
        grouped[key].append(row)

    agreed: dict[tuple[str, str], dict[str, Any]] = {}
    disagreed = 0
    for key, runs in sorted(grouped.items()):
        accepts = {r["action"] == "stop" for r in runs}
        if len(accepts) > 1:
            disagreed += 1
            continue
        # Deterministic pick: sort by run index if present, else first row
        ordered = sorted(runs, key=lambda r: (r.get("run", 0), r.get("action", "")))
        chosen = dict(ordered[0])
        chosen["runs"] = len(runs)
        chosen["accept"] = chosen["action"] == "stop"
        agreed[key] = chosen
    return agreed, disagreed


def task_bootstrap_ci(
    items_by_task: dict[str, list[bool]],
    *,
    seed: int = BOOTSTRAP_SEED,
    resamples: int = DEFAULT_RESAMPLES,
) -> tuple[float | None, float | None]:
    """95% percentile bootstrap interval resampling tasks with replacement."""
    tasks = sorted(t for t, vals in items_by_task.items() if vals)
    if not tasks:
        return None, None
    rng = random.Random(seed)
    n_tasks = len(tasks)
    stats: list[float] = []
    for _ in range(resamples):
        hits = 0
        total = 0
        for _ in range(n_tasks):
            vals = items_by_task[tasks[rng.randrange(n_tasks)]]
            hits += sum(1 for v in vals if v)
            total += len(vals)
        if total > 0:
            stats.append(hits / total)
    if not stats:
        return None, None
    stats.sort()
    lo_idx = int(0.025 * (len(stats) - 1))
    hi_idx = int(0.975 * (len(stats) - 1))
    return round(stats[lo_idx], 4), round(stats[hi_idx], 4)


def rate_summary(
    outcomes_by_task: dict[str, list[bool]],
    *,
    resamples: int = DEFAULT_RESAMPLES,
) -> dict[str, Any]:
    hits = sum(sum(1 for v in vals if v) for vals in outcomes_by_task.values())
    total = sum(len(vals) for vals in outcomes_by_task.values())
    rate = round(hits / total, 4) if total else None
    lo, hi = task_bootstrap_ci(outcomes_by_task, resamples=resamples)
    return {
        "hits": hits,
        "total": total,
        "rate": rate,
        "ci95": [lo, hi] if lo is not None else None,
    }


def score_condition(
    agreed: dict[tuple[str, str], dict[str, Any]],
    condition: str,
    restore_accepted_wrong: set[str],
    *,
    resamples: int,
) -> dict[str, Any]:
    catch_by_task: dict[str, list[bool]] = defaultdict(list)
    all_wrong_by_task: dict[str, list[bool]] = defaultdict(list)
    false_block_by_task: dict[str, list[bool]] = defaultdict(list)
    incomplete_right = 0

    for (cand, cond), row in sorted(agreed.items()):
        if cond != condition:
            continue
        task = str(row["task"])
        blocked = not row["accept"]
        if row["right"]:
            false_block_by_task[task].append(blocked)
            if row["action"] == "incomplete":
                incomplete_right += 1
        else:
            all_wrong_by_task[task].append(blocked)
            if cand in restore_accepted_wrong:
                catch_by_task[task].append(blocked)

    return {
        "catch_over_restore": rate_summary(catch_by_task, resamples=resamples),
        "catch_all_wrong": rate_summary(all_wrong_by_task, resamples=resamples),
        "false_block": rate_summary(false_block_by_task, resamples=resamples),
        "incomplete_right": incomplete_right,
    }


def score_approvals(
    rows: list[dict[str, Any]],
    *,
    resamples: int = DEFAULT_RESAMPLES,
) -> dict[str, dict[str, Any]]:
    by_approver: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in rows:
        by_approver[str(row["approver"])].append((str(row["task"]), float(row["minutes"])))

    out: dict[str, dict[str, Any]] = {}
    for approver, pairs in sorted(by_approver.items()):
        pairs.sort()
        mins = [m for _, m in pairs]
        med = round(statistics.median(mins), 3)
        rng = random.Random(BOOTSTRAP_SEED)
        n = len(mins)
        boots = sorted(
            statistics.median(mins[rng.randrange(n)] for _ in range(n))
            for _ in range(resamples)
        )
        lo = round(boots[int(0.025 * (len(boots) - 1))], 3)
        hi = round(boots[int(0.975 * (len(boots) - 1))], 3)
        out[approver] = {
            "tasks": n,
            "median_minutes": med,
            "ci95": [lo, hi],
            "max_minutes": round(max(mins), 3),
        }
    return out


def decide_gate(
    *,
    catch_rate: float | None,
    same_family_rate: float | None,
    false_block_rate: float | None,
    approvals: dict[str, dict[str, Any]],
    stage_counts: dict[str, int],
) -> dict[str, Any]:
    if catch_rate is None or false_block_rate is None:
        return {"verdict": "insufficient_data", "reasons": ["missing primary catch or false-block data"]}

    if catch_rate < 0.25 or false_block_rate > 0.20:
        reasons = []
        if catch_rate < 0.25:
            reasons.append(f"catch rate {catch_rate:.1%} < 25%")
        if false_block_rate > 0.20:
            reasons.append(f"false-block rate {false_block_rate:.1%} > 20%")
        return {"verdict": "fail", "reasons": reasons}

    approval_ok = all(a["median_minutes"] <= 5.0 for a in approvals.values())
    same_family_ok = same_family_rate is None or same_family_rate >= 0.40
    if catch_rate >= 0.50 and same_family_ok and false_block_rate <= 0.10 and approval_ok:
        return {"verdict": "pass", "reasons": ["all gate thresholds met"]}

    reasons = []
    if catch_rate < 0.50:
        reasons.append(f"catch rate {catch_rate:.1%} < 50%")
    if not same_family_ok and same_family_rate is not None:
        reasons.append(f"same-family catch rate {same_family_rate:.1%} < 40%")
    if false_block_rate > 0.10:
        reasons.append(f"false-block rate {false_block_rate:.1%} > 10%")
    if not approval_ok:
        slow = [k for k, v in approvals.items() if v["median_minutes"] > 5.0]
        reasons.append(f"median approval time > 5 min for {', '.join(slow)}")

    total_slipped = sum(stage_counts.values())
    dominant_fixable = None
    if total_slipped > 0:
        for stage in FIXABLE_STAGES:
            share = stage_counts.get(stage, 0) / total_slipped
            if share >= 0.60:
                dominant_fixable = {"stage": stage, "share": round(share, 4)}
                break

    if dominant_fixable:
        return {
            "verdict": "between_fixable_stage",
            "reasons": reasons,
            "fixable_stage": dominant_fixable,
        }
    return {"verdict": "between_validator_branch", "reasons": reasons}


def score(
    replay_rows: list[dict[str, Any]],
    approval_rows: list[dict[str, Any]],
    *,
    primary_drafter: str = DEFAULT_PRIMARY_DRAFTER,
    primary_condition: str = "primary",
    restore_condition: str = "restore",
    resamples: int = DEFAULT_RESAMPLES,
) -> dict[str, Any]:
    agreed, disagreed = collapse_replays(replay_rows)
    conditions = sorted({cond for _, cond in agreed})

    restore_accepted_wrong = {
        cand
        for (cand, cond), row in agreed.items()
        if cond == restore_condition and not row["right"] and row["accept"]
    }

    condition_scores = {
        cond: score_condition(agreed, cond, restore_accepted_wrong, resamples=resamples)
        for cond in conditions
    }

    same_family_by_task: dict[str, list[bool]] = defaultdict(list)
    stage_counts: Counter[str] = Counter()
    false_block_causes: Counter[str] = Counter()

    for (cand, cond), row in sorted(agreed.items()):
        if cond != primary_condition:
            continue
        task = str(row["task"])
        blocked = not row["accept"]
        if not row["right"] and cand in restore_accepted_wrong:
            if row.get("model") == primary_drafter:
                same_family_by_task[task].append(blocked)
            if not blocked:
                stage = str(row.get("stage") or "unspecified")
                stage_counts[stage] += 1
        elif row["right"] and blocked:
            cause = str(row.get("cause") or row["action"])
            false_block_causes[cause] += 1

    primary_scores = condition_scores.get(primary_condition, {})
    catch_summary = primary_scores.get("catch_over_restore", rate_summary({}, resamples=resamples))
    same_family_summary = rate_summary(same_family_by_task, resamples=resamples)
    false_block_summary = primary_scores.get("false_block", rate_summary({}, resamples=resamples))
    approvals_summary = score_approvals(approval_rows, resamples=resamples)

    stage_table = {s: stage_counts.get(s, 0) for s in STAGES}
    for extra in sorted(set(stage_counts) - set(STAGES)):
        stage_table[extra] = stage_counts[extra]

    gate = decide_gate(
        catch_rate=catch_summary["rate"],
        same_family_rate=same_family_summary["rate"],
        false_block_rate=false_block_summary["rate"],
        approvals=approvals_summary,
        stage_counts=stage_table,
    )

    return {
        "bootstrap": {"seed": BOOTSTRAP_SEED, "resamples": resamples},
        "primary_drafter": primary_drafter,
        "primary_condition": primary_condition,
        "restore_condition": restore_condition,
        "disagreed_replays_excluded": disagreed,
        "restore_accepted_wrong_count": len(restore_accepted_wrong),
        "primary": {
            "catch_rate": catch_summary,
            "same_family_catch_rate": same_family_summary,
            "false_block_rate": false_block_summary,
        },
        "approvals": approvals_summary,
        "per_stage_slipped": stage_table,
        "false_block_causes": dict(sorted(false_block_causes.items())),
        "conditions": condition_scores,
        "gate": gate,
    }


def _fmt_rate(summary: dict[str, Any]) -> str:
    if summary["rate"] is None:
        return "n/a (0/0)"
    ci = summary["ci95"]
    ci_str = f" [95% CI {ci[0]:.1%}–{ci[1]:.1%}]" if ci else ""
    return f"{summary['rate']:.1%} ({summary['hits']}/{summary['total']}){ci_str}"


def format_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Laws Study Score Report",
        "",
        f"- **Gate verdict:** `{report['gate']['verdict']}` ({'; '.join(report['gate']['reasons'])})",
        f"- **Disagreed double-replays excluded:** {report['disagreed_replays_excluded']}",
        f"- **Wrong changes accepted by `{report['restore_condition']}`:** {report['restore_accepted_wrong_count']}",
        "",
        "## Primary Gate Measures",
        "",
        f"- **Catch rate (over restore):** {_fmt_rate(report['primary']['catch_rate'])}",
        f"- **Same-family catch rate (`{report['primary_drafter']}`):** {_fmt_rate(report['primary']['same_family_catch_rate'])}",
        f"- **False-block rate (incl. incomplete):** {_fmt_rate(report['primary']['false_block_rate'])}",
    ]
    if report["approvals"]:
        lines.append("")
        lines.append("## Approval Time")
        lines.append("")
        lines.append("| Approver | Tasks | Median (min) | 95% CI | Max (min) |")
        lines.append("|---|---:|---:|---|---:|")
        for approver, stats in report["approvals"].items():
            ci = stats["ci95"]
            lines.append(
                f"| {approver} | {stats['tasks']} | {stats['median_minutes']:.2f} | "
                f"{ci[0]:.2f}–{ci[1]:.2f} | {stats['max_minutes']:.2f} |"
            )

    lines.extend(["", "## Per-Stage Slipped Wrong Changes", ""])
    lines.append("| Stage | Count |")
    lines.append("|---|---:|")
    for stage, count in report["per_stage_slipped"].items():
        lines.append(f"| `{stage}` | {count} |")

    if report["false_block_causes"]:
        lines.extend(["", "## False-Block Causes", ""])
        lines.append("| Cause | Count |")
        lines.append("|---|---:|")
        for cause, count in report["false_block_causes"].items():
            lines.append(f"| `{cause}` | {count} |")

    lines.extend(["", "## All Conditions", ""])
    lines.append("| Condition | Catch over restore | Catch all wrong | False block | Incomplete (right) |")
    lines.append("|---|---|---|---|---:|")
    for cond, stats in report["conditions"].items():
        lines.append(
            f"| `{cond}` | {_fmt_rate(stats['catch_over_restore'])} | "
            f"{_fmt_rate(stats['catch_all_wrong'])} | {_fmt_rate(stats['false_block'])} | "
            f"{stats['incomplete_right']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Score laws study raw records per study/gate.md.")
    ap.add_argument("--replays", type=Path, required=True, help="JSONL of replay records")
    ap.add_argument("--approvals", type=Path, help="Optional JSONL of approval timing records")
    ap.add_argument("--primary-drafter", default=DEFAULT_PRIMARY_DRAFTER)
    ap.add_argument("--primary-condition", default="primary")
    ap.add_argument("--restore-condition", default="restore")
    ap.add_argument("--resamples", type=int, default=DEFAULT_RESAMPLES)
    ap.add_argument("--json", dest="json_out", type=Path, help="Write JSON report here")
    ap.add_argument("--md", dest="md_out", type=Path, help="Write Markdown report here")
    args = ap.parse_args(argv)

    replays = load_jsonl(args.replays)
    approvals = load_jsonl(args.approvals) if args.approvals else []
    report = score(
        replays,
        approvals,
        primary_drafter=args.primary_drafter,
        primary_condition=args.primary_condition,
        restore_condition=args.restore_condition,
        resamples=args.resamples,
    )
    md = format_markdown(report)
    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.write_text(md, encoding="utf-8")
    if not args.json_out and not args.md_out:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
