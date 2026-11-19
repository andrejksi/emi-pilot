#!/usr/bin/env python3
"""Double-replay gate runner for the laws study (see study/gate.md).

Replays every candidate of a task twice (`--runs 2`, sandboxed when bwrap is
available) across all 8 conditions of study/gate.md:
  1. pytest                    plain pytest on the candidate tree
  2. restore                   restore script, no laws
  3. emi_default               EMI default, no laws
  4. restore_laws              restore script + approved laws
  5. emi_unapproved_primary    EMI + primary drafter's unapproved laws
  6. emi_unapproved_secondary  EMI + secondary drafter's unapproved laws
  7. primary                   EMI + approved laws
  8. ceiling                   EMI + hidden tests as laws

Writes one JSON object per (candidate, condition, run) to `--out` in the exact
JSONL schema consumed by `study/score.py`.

Usage:
    python3 study/replay_gate.py --task TASK --attempts DIR [DIR ...] \\
        --laws-root DIR --out OUT.jsonl --emi EMI [--runs 2]
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

PILOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PILOT / "harness"))

import plain_check  # noqa: E402
from common import GIT_ENV, copy_tree, git, load_task, run  # noqa: E402
from gates import emi as emi_gate  # noqa: E402
from gates import naive as naive_gate  # noqa: E402
from prepare import prepare  # noqa: E402
from trees import test_command  # noqa: E402

ALL_CONDITIONS = (
    "pytest",
    "restore",
    "emi_default",
    "restore_laws",
    "emi_unapproved_primary",
    "emi_unapproved_secondary",
    "primary",
    "ceiling",
)


def has_law_files(laws_dir: Path | None) -> bool:
    if not laws_dir or not laws_dir.is_dir():
        return False
    return any(p.is_file() for p in laws_dir.rglob("*"))


def resolve_law_dirs(
    task_id: str,
    *,
    laws_root: Path | None = None,
    approved_laws: Path | None = None,
    unapproved_primary: Path | None = None,
    unapproved_secondary: Path | None = None,
) -> dict[str, Path | None]:
    """Resolve law directories for a task from explicit args or a drafts root."""
    task_root = (laws_root / task_id) if laws_root else None
    if task_root and (task_root / "laws").is_dir():
        task_root = task_root / "laws"

    if approved_laws is None and task_root:
        cand = task_root / "checked"
        approved_laws = cand if has_law_files(cand) else None
    elif approved_laws is not None and not has_law_files(approved_laws):
        approved_laws = None

    if unapproved_primary is None and task_root:
        cand = task_root / "first"
        unapproved_primary = cand if has_law_files(cand) else None
    elif unapproved_primary is not None and not has_law_files(unapproved_primary):
        unapproved_primary = None

    if unapproved_secondary is None and task_root:
        cand = task_root / "secondary"
        unapproved_secondary = cand if has_law_files(cand) else None
    elif unapproved_secondary is not None and not has_law_files(unapproved_secondary):
        unapproved_secondary = None

    checked_draft = None
    if task_root:
        cand = task_root / "checked_draft"
        checked_draft = cand if has_law_files(cand) else None

    return {
        "approved": approved_laws,
        "checked_draft": checked_draft,
        "unapproved_primary": unapproved_primary,
        "unapproved_secondary": unapproved_secondary,
    }


def classify_emi_cause(receipt: dict[str, Any] | None, record: dict[str, Any]) -> str | None:
    """Identify which part of EMI caused a non-stop verdict."""
    action = record.get("action")
    if action == "stop":
        return None
    if "error" in record and not action:
        return "error"
    if action == "incomplete":
        if receipt:
            not_ver = receipt.get("not_verified") or []
            if isinstance(not_ver, list) and not_ver:
                first = not_ver[0]
                if isinstance(first, dict):
                    kind = first.get("kind") or first.get("reason")
                    if kind:
                        return f"incomplete:{kind}"
                elif isinstance(first, str):
                    return "incomplete:not_verified"
        return "incomplete"
    if receipt:
        laws = receipt.get("laws") or {}
        if isinstance(laws, dict):
            if laws.get("broken"):
                return "laws_broken"
            if laws.get("unmet") or laws.get("failed"):
                return "laws_unmet"
        rule = receipt.get("rule")
        if rule and rule != "none":
            return str(rule)
        if receipt.get("regression"):
            return "regression"
        if receipt.get("changed_old_tests"):
            return "changed_old_tests"
        if receipt.get("ask"):
            return "ask_person"
    return str(action or "error")


def infer_slipped_stage(
    *,
    has_approved: bool,
    has_unapproved_primary: bool,
    has_checked_draft: bool = False,
    override: str | None = None,
) -> str:
    """Classify why a wrong candidate slipped past the primary condition."""
    if override:
        return override
    if has_approved:
        return "law_in_force_still_stop"
    if has_checked_draft:
        return "dropped_at_approval"
    if has_unapproved_primary:
        return "dropped_by_rules_check"
    return "no_law_drafted"


def collect_candidates(
    attempt_roots: list[Path],
    task_id: str,
    tmp: Path,
    *,
    include_gold: bool = True,
) -> list[tuple[str, Path, dict[str, Any], dict[str, Any]]]:
    """Collect deduplicated (candidate_id, attempt_dir, run_record, oracle) tuples."""
    seen: set[str] = set()
    items: list[tuple[str, Path, dict[str, Any], dict[str, Any]]] = []
    for root in attempt_roots:
        if not root.is_dir():
            continue
        for d in sorted(root.iterdir()):
            if not d.is_dir():
                continue
            run_file = d / "run.json"
            oracle_file = d / "oracle.json"
            if not run_file.exists() or not oracle_file.exists():
                continue
            rec = json.loads(run_file.read_text(encoding="utf-8"))
            if rec.get("task") != task_id:
                continue
            oracle = json.loads(oracle_file.read_text(encoding="utf-8"))
            if oracle.get("passed") is None:
                continue
            cid = d.name
            if cid in seen:
                continue
            seen.add(cid)
            items.append((cid, d, rec, oracle))

    if include_gold:
        gold = PILOT / "tasks" / task_id / "replay" / "gold-with-tests.patch"
        if gold.exists():
            cid = f"{task_id}.human.gold"
            if cid not in seen:
                d = tmp / cid
                d.mkdir(parents=True, exist_ok=True)
                shutil.copy2(gold, d / "candidate.diff")
                items.append(
                    (
                        cid,
                        d,
                        {"task": task_id, "model": "human", "final": "accepted"},
                        {"passed": True},
                    )
                )
    return items


def build_base_tree(
    task: dict[str, Any],
    laws: Path | None,
    dst: Path,
    venv: str | None,
    emi_bin: str,
    *,
    ceiling: bool = False,
) -> list[str]:
    """Prepare baseline tree with optional laws or hidden tests committed.

    Returns list of hidden-touched relative file paths (non-empty only for
    git-task ceiling builds so candidate diffs can avoid conflicting on them).
    """
    task_id = task["id"]
    prepare(task_id, "cooperative", dst, venv, emi_bin)
    hidden_touched: list[str] = []

    if ceiling:
        hidden_dir = PILOT / "tasks" / task_id / "hidden"
        if task.get("kind", "dir") == "dir":
            if hidden_dir.is_dir():
                copy_tree(hidden_dir, dst / plain_check.LAWS)
        else:
            patch = hidden_dir / "test.patch"
            if patch.exists():
                hidden_touched = re.findall(
                    r"^diff --git a/(\S+) b/", patch.read_text(encoding="utf-8"), flags=re.M
                )
                code, out = run(["git", "apply", "--binary", str(patch)], cwd=dst, env=GIT_ENV)
                if code != 0:
                    raise RuntimeError(f"ceiling hidden patch failed to apply: {out[-500:]}")
            f2p = (task.get("oracle") or {}).get("fail_to_pass") or []
            if f2p:
                laws_dir = dst / plain_check.LAWS
                laws_dir.mkdir(parents=True, exist_ok=True)
                law_src = (
                    '"""Ceiling: the task\'s hidden fail_to_pass tests as laws."""\n'
                    "import subprocess, sys\n\n"
                    f"TESTS = {f2p!r}\n\n"
                    "def test_hidden_fail_to_pass():\n"
                    '    """New: all hidden fail_to_pass tests must pass."""\n'
                    '    res = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *TESTS])\n'
                    "    assert res.returncode == 0\n"
                )
                (laws_dir / "test_ceiling_hidden.py").write_text(law_src, encoding="utf-8")
        git(dst, "add", "-A")
        git(dst, "commit", "-q", "--no-verify", "-m", "ceiling: hidden tests as laws")
        git(dst, "branch", "-f", "main", "HEAD")
    elif has_law_files(laws):
        assert laws is not None
        copy_tree(laws, dst / plain_check.LAWS)
        git(dst, "add", "-A")
        git(dst, "commit", "-q", "--no-verify", "-m", "laws, approved before coding")
        git(dst, "branch", "-f", "main", "HEAD")

    return hidden_touched


def apply_candidate(
    base: Path,
    attempt_dir: Path,
    dst: Path,
    *,
    exclude_paths: list[str] | None = None,
) -> str | None:
    copy_tree(base, dst)
    diff = attempt_dir / "candidate.diff"
    if not diff.exists() or diff.stat().st_size == 0:
        return None
    cmd = ["git", "apply", "--binary"]
    for p in exclude_paths or []:
        cmd.extend(["--exclude", p])
    cmd.append(str(diff.resolve()))
    code, out = run(cmd, cwd=dst, env=GIT_ENV)
    if code != 0:
        return f"diff_apply_failed: {out[-500:]}"
    return None


def eval_pytest(task: dict[str, Any], base: Path, attempt_dir: Path, work: Path) -> dict[str, Any]:
    err = apply_candidate(base, attempt_dir, work)
    if err:
        return {"action": "error", "cause": "diff_apply_failed", "seconds": 0.0}
    started = time.monotonic()
    try:
        verdict, _, record = naive_gate(work, {"task": task})
    except subprocess.TimeoutExpired as exc:
        return {"action": "error", "cause": "timeout", "seconds": round(float(exc.timeout), 1)}
    seconds = round(time.monotonic() - started, 1)
    if verdict == "accepted":
        return {"action": "stop", "cause": None, "seconds": seconds}
    return {"action": "repair", "cause": f"pytest_exit_{record.get('exit')}", "seconds": seconds}


def eval_restore(
    task: dict[str, Any],
    base: Path,
    attempt_dir: Path,
    work: Path,
    before: dict[str, str] | None,
) -> dict[str, Any]:
    if before is None:
        return {"action": "error", "cause": "baseline_tests_failed", "seconds": 0.0}
    err = apply_candidate(base, attempt_dir, work)
    if err:
        return {"action": "error", "cause": "diff_apply_failed", "seconds": 0.0}
    started = time.monotonic()
    try:
        accept, why = plain_check.check(task, work, before)
    except subprocess.TimeoutExpired as exc:
        return {"action": "error", "cause": "timeout", "seconds": round(float(exc.timeout), 1)}
    seconds = round(time.monotonic() - started, 1)
    if accept:
        return {"action": "stop", "cause": None, "seconds": seconds}
    cause = "laws" if "laws" in why else "regression"
    return {"action": "repair", "cause": cause, "seconds": seconds}


def eval_emi(
    task: dict[str, Any],
    base: Path,
    attempt_dir: Path,
    work: Path,
    emi_bin: str,
    receipt_dir: Path,
    *,
    exclude_paths: list[str] | None = None,
) -> dict[str, Any]:
    err = apply_candidate(base, attempt_dir, work, exclude_paths=exclude_paths)
    if err:
        return {"action": "error", "cause": "diff_apply_failed", "seconds": 0.0}
    receipt_dir.mkdir(parents=True, exist_ok=True)
    ctx: dict[str, Any] = {"emi": emi_bin, "out_dir": str(receipt_dir), "task": task}
    started = time.monotonic()
    try:
        _, _, record = emi_gate(work, ctx)
    except subprocess.TimeoutExpired as exc:
        return {"action": "error", "cause": "timeout", "seconds": round(float(exc.timeout), 1)}
    seconds = round(time.monotonic() - started, 1)
    action = record.get("action")
    if not action:
        return {"action": "error", "cause": "no_receipt", "seconds": seconds}
    receipt = None
    if record.get("receipt"):
        rpath = receipt_dir / record["receipt"]
        if rpath.exists():
            receipt = json.loads(rpath.read_text(encoding="utf-8"))
    cause = classify_emi_cause(receipt, record)
    return {"action": str(action), "cause": cause, "seconds": seconds}


def replay_task(
    task_id: str,
    attempt_roots: list[Path],
    out_jsonl: Path,
    *,
    emi_bin: str,
    venv: str | None = None,
    laws_root: Path | None = None,
    approved_laws: Path | None = None,
    unapproved_primary: Path | None = None,
    unapproved_secondary: Path | None = None,
    conditions: list[str] | None = None,
    runs: int = 2,
    include_gold: bool = True,
    stage_override: str | None = None,
    receipts_dir: Path | None = None,
) -> list[dict[str, Any]]:
    task = load_task(task_id)
    law_dirs = resolve_law_dirs(
        task_id,
        laws_root=laws_root,
        approved_laws=approved_laws,
        unapproved_primary=unapproved_primary,
        unapproved_secondary=unapproved_secondary,
    )
    selected = list(conditions) if conditions else list(ALL_CONDITIONS)
    if "emi_unapproved_secondary" in selected and law_dirs["unapproved_secondary"] is None:
        selected.remove("emi_unapproved_secondary")

    has_approved = law_dirs["approved"] is not None
    has_checked_draft = law_dirs["checked_draft"] is not None
    has_unapproved_primary = law_dirs["unapproved_primary"] is not None

    rows: list[dict[str, Any]] = []
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(dir=os.environ.get("WORK")) as tmp_str:
        tmp = Path(tmp_str)
        candidates = collect_candidates(attempt_roots, task_id, tmp, include_gold=include_gold)

        # Build each distinct base tree once per task.
        bases: dict[str, tuple[Path, list[str]]] = {}
        before_outcomes: dict[str, dict[str, str] | None] = {}

        def get_base(key: str, laws: Path | None, *, ceiling: bool = False) -> tuple[Path, list[str]]:
            if key not in bases:
                bdir = tmp / f"base-{key}"
                hidden_touched = build_base_tree(task, laws, bdir, venv, emi_bin, ceiling=ceiling)
                bases[key] = (bdir, hidden_touched)
            return bases[key]

        def get_before(key: str, base: Path) -> dict[str, str] | None:
            if key not in before_outcomes:
                before, _ = plain_check.outcomes(task, base, test_command(task))
                before_outcomes[key] = before
            return before_outcomes[key]

        for cond in selected:
            if cond in ("pytest", "restore", "emi_default"):
                base, exclude = get_base("none", None)
                before = get_before("none", base) if cond == "restore" else None
            elif cond in ("restore_laws", "primary"):
                base, exclude = get_base("approved", law_dirs["approved"])
                before = get_before("approved", base) if cond == "restore_laws" else None
            elif cond == "emi_unapproved_primary":
                base, exclude = get_base("unapproved_primary", law_dirs["unapproved_primary"])
                before = None
            elif cond == "emi_unapproved_secondary":
                base, exclude = get_base("unapproved_secondary", law_dirs["unapproved_secondary"])
                before = None
            elif cond == "ceiling":
                base, exclude = get_base("ceiling", None, ceiling=True)
                before = None
            else:
                raise ValueError(f"unknown condition: {cond}")

            for cid, attempt_dir, rec, oracle in candidates:
                right = bool(oracle["passed"])
                model = str(rec.get("model") or "unknown")
                for run_idx in range(runs):
                    work = tmp / f"work-{cond}-{cid}-r{run_idx}"
                    rdir = (
                        (receipts_dir / task_id / cond / f"{cid}.r{run_idx}")
                        if receipts_dir
                        else (tmp / f"receipts-{cond}-{cid}-r{run_idx}")
                    )
                    if cond == "pytest":
                        res = eval_pytest(task, base, attempt_dir, work)
                    elif cond in ("restore", "restore_laws"):
                        res = eval_restore(task, base, attempt_dir, work, before)
                    else:
                        res = eval_emi(
                            task, base, attempt_dir, work, emi_bin, rdir, exclude_paths=exclude
                        )

                    row: dict[str, Any] = {
                        "candidate": cid,
                        "task": task_id,
                        "model": model,
                        "right": right,
                        "condition": cond,
                        "action": res["action"],
                        "run": run_idx,
                        "cause": res["cause"],
                        "seconds": res["seconds"],
                    }
                    if cond == "primary" and not right and res["action"] == "stop":
                        row["stage"] = infer_slipped_stage(
                            has_approved=has_approved,
                            has_unapproved_primary=has_unapproved_primary,
                            has_checked_draft=has_checked_draft,
                            override=stage_override,
                        )
                    rows.append(row)

                    shutil.rmtree(work, ignore_errors=True)
                    shutil.rmtree(work.parent / (work.name + ".emi-state"), ignore_errors=True)
                    if not receipts_dir:
                        shutil.rmtree(rdir, ignore_errors=True)

    with out_jsonl.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Double-replay gate runner for study/gate.md.")
    ap.add_argument("--task", required=True, help="Task ID")
    ap.add_argument("--attempts", required=True, nargs="+", type=Path, help="Attempt directories")
    ap.add_argument("--laws-root", type=Path, help="Root dir containing <task>/{first,checked,secondary}")
    ap.add_argument("--approved-laws", type=Path, help="Override approved laws dir for this task")
    ap.add_argument("--unapproved-primary", type=Path, help="Override unapproved primary laws dir")
    ap.add_argument("--unapproved-secondary", type=Path, help="Override unapproved secondary laws dir")
    ap.add_argument("--conditions", nargs="*", choices=ALL_CONDITIONS, help="Subset of conditions")
    ap.add_argument("--runs", type=int, default=2, help="Number of replays per (candidate, condition)")
    ap.add_argument("--no-gold", action="store_true", help="Do not include gold-with-tests.patch")
    ap.add_argument("--stage-override", help="Override slipped stage label for this task")
    ap.add_argument("--receipts-dir", type=Path, help="Optional directory to preserve EMI receipts")
    ap.add_argument("--out", required=True, type=Path, help="Output JSONL path")
    ap.add_argument("--emi", default="emi", help="Path to emi binary")
    ap.add_argument("--venv", help="Virtualenv for dir tasks")
    args = ap.parse_args(argv)

    rows = replay_task(
        args.task,
        args.attempts,
        args.out,
        emi_bin=args.emi,
        venv=args.venv,
        laws_root=args.laws_root,
        approved_laws=args.approved_laws,
        unapproved_primary=args.unapproved_primary,
        unapproved_secondary=args.unapproved_secondary,
        conditions=args.conditions,
        runs=args.runs,
        include_gold=not args.no_gold,
        stage_override=args.stage_override,
        receipts_dir=args.receipts_dir,
    )
    print(f"{args.task}: wrote {len(rows)} replay rows to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
