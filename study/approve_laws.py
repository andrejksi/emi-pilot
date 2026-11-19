#!/usr/bin/env python3
"""Timed human law-approval CLI for the EMI laws study (study/gate.md).

Presents ONLY the issue prompt, the primary drafter's passing laws
(`checked_draft/`), and the last `emi rules check` output — never any fix,
hidden test, or candidate diff. Times each task approval and records:
  - `results/heldout-laws/<task>/checked/` (primary approver's accepted laws)
  - `results/heldout-laws/<task>/outside_approved/` (outside approver's selection)
  - `results/heldout-laws/approvals.jsonl` (`task`, `approver`, `minutes`, ...)

Usage:
    # Print the deterministic 10-task subset for the outside approver
    python3 study/approve_laws.py sample --tasks @heldout --n 10

    # Primary approver reviews all held-out tasks (timed)
    python3 study/approve_laws.py review --approver primary --tasks @heldout

    # Outside approver reviews the 10-task sample (timed)
    python3 study/approve_laws.py review --approver outside --sample-outside
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path
from typing import Any

PILOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PILOT / "harness"))

from common import load_task  # noqa: E402

STUDY_SEED = 20261117
MAX_MINUTES = 5.0


def expand_tasks(specs: list[str]) -> list[str]:
    out: list[str] = []
    for spec in specs:
        if spec.startswith("@"):
            batch = PILOT / "batches" / f"{spec[1:]}.txt"
            if not batch.exists():
                raise SystemExit(f"Batch file not found: {batch}")
            for line in batch.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    out.append(line)
        else:
            out.append(spec)
    # Deduplicate preserving sorted order
    return sorted(set(out))


def sample_outside_tasks(task_ids: list[str], n: int = 10, seed: int = STUDY_SEED) -> list[str]:
    ordered = sorted(set(task_ids))
    if n >= len(ordered):
        return ordered
    return sorted(random.Random(seed).sample(ordered, n))


def load_approvals(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def append_approval(path: Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")


def copy_selected(src: Path, dst: Path, rel_files: list[str]) -> None:
    shutil.rmtree(dst, ignore_errors=True)
    if not rel_files:
        return
    dst.mkdir(parents=True, exist_ok=True)
    for rel in rel_files:
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src / rel, target)


def cmd_sample(args: argparse.Namespace) -> int:
    tasks = expand_tasks(args.tasks)
    chosen = sample_outside_tasks(tasks, n=args.n, seed=args.seed)
    for t in chosen:
        print(t)
    return 0


def review_one(
    task_id: str,
    laws_root: Path,
    approver: str,
    approvals_path: Path,
    *,
    input_fn=input,
) -> str:
    """Review a single task interactively. Returns 'done', 'skip', or 'quit'."""
    task_dir = laws_root / task_id
    draft_dir = task_dir / "checked_draft"
    draft_files = sorted(
        str(p.relative_to(draft_dir))
        for p in draft_dir.rglob("*")
        if p.is_file() and "__pycache__" not in p.parts
    ) if draft_dir.is_dir() else []

    if not draft_files:
        print(f"\n[{task_id}] No passing checked_draft/ laws to review — skipping.")
        return "skip"

    task = load_task(task_id)
    checks_dir = task_dir / "checks_primary"
    last_check = ""
    if checks_dir.is_dir():
        txts = sorted(checks_dir.glob("*.txt"), key=lambda p: int(p.stem) if p.stem.isdigit() else -1)
        if txts:
            last_check = txts[-1].read_text(encoding="utf-8", errors="replace").strip()

    print("\n" + "=" * 72)
    print(f"TASK: {task_id}  (approver: {approver}, target <= {MAX_MINUTES:.0f} min)")
    print("=" * 72)
    print("--- ISSUE PROMPT ---")
    print(task["prompt"].strip())
    print("\n--- DRAFTED LAWS (passed emi rules check) ---")
    for idx, rel in enumerate(draft_files, 1):
        print(f"\n[{idx}] {rel}")
        print("-" * 40)
        print((draft_dir / rel).read_text(encoding="utf-8", errors="replace").rstrip())
    if last_check:
        print("\n--- LAST `emi rules check` OUTPUT ---")
        print(last_check[-4000:])

    started = time.monotonic()
    while True:
        choice = input_fn(
            "\nDecision: [a]pprove all | [s]elect files | [r]eject all | [k]ip (do not record) | [q]uit > "
        ).strip().lower()
        if choice == "q":
            return "quit"
        if choice == "k":
            return "skip"
        if choice == "a":
            kept = list(draft_files)
            decision = "approve_all"
            break
        if choice == "r":
            kept = []
            decision = "reject_all"
            break
        if choice == "s":
            raw = input_fn(f"Enter file numbers to KEEP (1..{len(draft_files)}, comma-separated, blank for none): ").strip()
            if not raw:
                kept = []
                decision = "reject_all"
                break
            try:
                indices = [int(tok.strip()) for tok in raw.split(",") if tok.strip()]
                if any(i < 1 or i > len(draft_files) for i in indices):
                    print("Invalid number; try again.")
                    continue
                kept = [draft_files[i - 1] for i in sorted(set(indices))]
                decision = "approve_partial" if len(kept) < len(draft_files) else "approve_all"
                break
            except ValueError:
                print("Please enter comma-separated numbers.")
                continue
        print("Enter a, s, r, k, or q.")

    minutes = round((time.monotonic() - started) / 60.0, 2)
    if approver == "primary":
        copy_selected(draft_dir, task_dir / "checked", kept)
    else:
        copy_selected(draft_dir, task_dir / "outside_approved", kept)

    record = {
        "task": task_id,
        "approver": approver,
        "minutes": minutes,
        "decision": decision,
        "kept_files": kept,
        "dropped_files": [f for f in draft_files if f not in kept],
    }
    append_approval(approvals_path, record)
    warn = " (WARNING: > 5.0 min cap)" if minutes > MAX_MINUTES else ""
    print(f"Recorded {decision} for {task_id} in {minutes:.2f} min{warn}.")
    return "done"


def cmd_review(args: argparse.Namespace) -> int:
    tasks = expand_tasks(args.tasks)
    if args.sample_outside:
        tasks = sample_outside_tasks(tasks, n=args.sample_n, seed=args.seed)

    laws_root = Path(args.laws_root).resolve()
    approvals_path = Path(args.approvals).resolve() if args.approvals else (laws_root / "approvals.jsonl")
    done = {
        (r["task"], r["approver"])
        for r in load_approvals(approvals_path)
    }

    pending = [t for t in tasks if (t, args.approver) not in done]
    print(f"Approver: {args.approver} | Total tasks: {len(tasks)} | Already recorded: {len(tasks) - len(pending)} | Remaining: {len(pending)}")
    for task_id in pending:
        status = review_one(task_id, laws_root, args.approver, approvals_path)
        if status == "quit":
            print("Stopped early; progress saved to", approvals_path)
            return 0
    print("Review complete! Recorded approvals in", approvals_path)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Timed human approval CLI for study/gate.md.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_s = sub.add_parser("sample", help="Print the deterministic outside-approver task sample.")
    p_s.add_argument("--tasks", nargs="+", default=["@heldout"])
    p_s.add_argument("--n", type=int, default=10)
    p_s.add_argument("--seed", type=int, default=STUDY_SEED)
    p_s.set_defaults(func=cmd_sample)

    p_r = sub.add_parser("review", help="Interactively review and time law approvals.")
    p_r.add_argument("--approver", required=True, help="Approver label, e.g. primary or outside")
    p_r.add_argument("--laws-root", default="results/heldout-laws")
    p_r.add_argument("--approvals", help="Path to approvals.jsonl (default: <laws-root>/approvals.jsonl)")
    p_r.add_argument("--tasks", nargs="+", default=["@heldout"])
    p_r.add_argument("--sample-outside", action="store_true", help="Restrict to the 10-task outside sample")
    p_r.add_argument("--sample-n", type=int, default=10)
    p_r.add_argument("--seed", type=int, default=STUDY_SEED)
    p_r.set_defaults(func=cmd_review)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
