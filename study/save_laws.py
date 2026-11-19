#!/usr/bin/env python3
"""Blind law-drafting helper for manual / AI-session law authoring (study/gate.md).

Mirrors `harness/draft_laws.py` for non-API AI sessions while enforcing strict
blindness:
  - `prepare` lays out the baseline repository configured for EMI (`cooperative`
    arm), runs `emi rules brief`, and prints ONLY the brief, stand-in rules, and
    the issue prompt (never hidden tests, fixes, oracle metadata, or candidates).
  - `check` verifies that only files under `.emi/laws/` were edited, snapshots
    the first draft (`first/` for primary, `secondary/` for secondary), runs
    `emi rules check --format text`, records every round in `draft_<role>.json`
    and `checks_<role>/<n>.txt`, and snapshots the last passing draft into
    `checked_draft/` (primary) or `secondary_checked/` (secondary).
  - `ensure-emi` fetches the prebuilt `study-gate-v1` binary via `gh` when not
    already present on PATH.

Usage:
    # 0. Optional: fetch the exact study-gate-v1 emi binary
    python3 study/save_laws.py ensure-emi --dest /tmp/emi-bin/emi

    # 1. Prepare a blind baseline workspace and print brief + issue prompt
    python3 study/save_laws.py prepare --task <TASK_ID> --work /tmp/laws/<TASK_ID> --emi /tmp/emi-bin/emi

    # 2. (Agent writes rule tests ONLY under /tmp/laws/<TASK_ID>/.emi/laws/)

    # 3. Check & save the drafted laws (repeat until exit 0)
    python3 study/save_laws.py check --task <TASK_ID> --work /tmp/laws/<TASK_ID> \\
        --role primary --model "<MODEL_ID>" --out results/heldout-laws --emi /tmp/emi-bin/emi
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

PILOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PILOT / "harness"))

from common import load_task, run  # noqa: E402
from prepare import prepare  # noqa: E402
from trees import test_command  # noqa: E402

LAWS = ".emi/laws"
DEFAULT_EMI_ARTIFACT_RUN = "44526078350"
DEFAULT_EMI_REPO = "andrejksi/emi-pilot"

STAND_IN = (
    "You are drafting EMI laws BEFORE any code is written for this task.\n"
    "Rules:\n"
    "1. Read any repository file and run tests (`{tests}`), but write files ONLY under `{laws}/`.\n"
    "   Do NOT write or modify product code or existing test files outside `{laws}/`.\n"
    "2. The person cannot answer interactive questions in this study. Take what the issue prompt\n"
    "   below states as the person's written answers (`A1 written: ...` in `{laws}/answers.txt`),\n"
    "   and where the issue says nothing, treat the answer as \"doesn't matter\". Do not invent\n"
    "   requirements the issue does not state.\n"
    "3. NEVER read, open, grep, or inspect `tasks/*/hidden/`, `tasks/*/replay/`, `tasks/*/task.json`,\n"
    "   or `results/` in `emi-pilot`, and NEVER search GitHub or the web for the PR or fix.\n"
    "4. After writing your rule tests in `{laws}/`, run `study/save_laws.py check ...`. Fix any\n"
    "   issues `emi rules check` reports (exit 3) and re-run `check` until it exits 0.\n"
)


def resolve_emi(emi: str) -> str:
    found = shutil.which(emi)
    if found:
        return found
    p = Path(emi)
    if p.is_file() and os.access(p, os.X_OK):
        return str(p.resolve())
    raise SystemExit(
        f"emi binary not found or not executable: {emi}\n"
        f"Run `python3 study/save_laws.py ensure-emi --dest /tmp/emi-bin/emi` "
        f"or pass `--emi /path/to/emi`."
    )


def emi_state_dir(work: Path) -> Path:
    return work.parent / (work.name + ".emi-state")


def changed_outside_laws(work: Path) -> list[str]:
    """Return paths modified or untracked outside `.emi/laws/`."""
    _, out = run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=work, check=True)
    bad: list[str] = []
    prefix = LAWS.rstrip("/") + "/"
    for line in out.splitlines():
        if len(line) < 4:
            continue
        rel = line[3:].strip()
        if " -> " in rel:
            rel = rel.split(" -> ", 1)[1]
        rel = rel.strip('"')
        if rel == LAWS or rel.startswith(prefix):
            continue
        bad.append(rel)
    return sorted(bad)


def laws_now(work: Path) -> dict[str, str]:
    """Return every added/modified file under `.emi/laws/`, excluding __pycache__."""
    _, out = run(
        ["git", "status", "--porcelain", "--untracked-files=all", "--", LAWS],
        cwd=work,
        check=True,
    )
    root = work / LAWS
    files: dict[str, str] = {}
    for line in out.splitlines():
        if len(line) < 4:
            continue
        rel_git = line[3:].strip().strip('"')
        path = work / rel_git
        if path.is_file() and "__pycache__" not in path.parts:
            files[str(path.relative_to(root))] = path.read_text(encoding="utf-8", errors="replace")
    return dict(sorted(files.items()))


def write_snapshot(files: dict[str, str], dest: Path) -> None:
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def _is_runnable(binary: Path) -> bool:
    if not binary.is_file() or not os.access(binary, os.X_OK):
        return False
    try:
        res = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _build_emi_from_source(dest: Path, ref: str = "study-gate-v1") -> None:
    cargo = shutil.which("cargo")
    if not cargo:
        raise SystemExit(
            "Prebuilt emi-bin could not run on this host and `cargo` is not installed.\n"
            f"Install Rust/cargo or build andrejksi/EMI at tag `{ref}` and pass `--emi /path/to/emi`."
        )
    sibling = PILOT.parent / "EMI"
    src_dir = dest.parent / ".emi-src-build"
    shutil.rmtree(src_dir, ignore_errors=True)
    if (sibling / ".git").exists():
        clone_src = str(sibling)
    else:
        clone_src = "https://github.com/andrejksi/EMI.git"
    print(f"Building emi ({ref}) from {clone_src} via cargo...")
    subprocess.run(["git", "clone", "-q", clone_src, str(src_dir)], check=True)
    subprocess.run(["git", "checkout", "-q", ref], cwd=src_dir, check=True)
    subprocess.run(
        [cargo, "build", "--release", "-p", "emi-cli", "--bin", "emi"],
        cwd=src_dir,
        check=True,
    )
    built = src_dir / "target" / "release" / "emi"
    shutil.copy2(built, dest)
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shutil.rmtree(src_dir, ignore_errors=True)


def cmd_ensure_emi(args: argparse.Namespace) -> int:
    dest = Path(args.dest).resolve()
    if _is_runnable(dest) and not args.force:
        ver = subprocess.run([str(dest), "--version"], capture_output=True, text=True)
        print(f"emi already ready: {dest} ({ver.stdout.strip()})")
        return 0
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir = dest.parent / ".emi-download-tmp"
    shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        "gh",
        "run",
        "download",
        args.run_id,
        "-R",
        args.repo,
        "-n",
        "emi-bin",
        "-D",
        str(tmp_dir),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        downloaded = tmp_dir / "emi"
        if not downloaded.is_file():
            matches = list(tmp_dir.rglob("emi"))
            downloaded = matches[0] if matches else downloaded
        if downloaded.is_file():
            shutil.move(str(downloaded), str(dest))
            dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    shutil.rmtree(tmp_dir, ignore_errors=True)

    if not _is_runnable(dest):
        if dest.exists():
            dest.unlink()
        _build_emi_from_source(dest, ref=args.ref)

    if not _is_runnable(dest):
        raise SystemExit(f"emi binary at {dest} still failed `--version` check")
    ver = subprocess.run([str(dest), "--version"], capture_output=True, text=True)
    print(f"emi ready: {dest} ({ver.stdout.strip()})")
    return 0


def cmd_prepare(args: argparse.Namespace) -> int:
    emi_bin = resolve_emi(args.emi)
    work = Path(args.work).resolve()
    prepare(args.task, "cooperative", work, args.venv, emi_bin)
    task = load_task(args.task)
    tests = test_command(task)
    state = emi_state_dir(work)
    code, brief = run([emi_bin, "rules", "brief"], cwd=work, env={"XDG_STATE_HOME": str(state)})
    if code != 0:
        raise SystemExit(f"emi rules brief failed (exit {code}):\n{brief}")

    print(f"=== BLIND LAW-DRAFTING WORKSPACE READY: {work} ===")
    print(f"=== TASK: {args.task} ===")
    print()
    print(STAND_IN.format(tests=tests, laws=LAWS))
    print("=== EMI RULES BRIEF ===")
    print(brief.rstrip())
    print()
    print("=== ISSUE PROMPT ===")
    print(task["prompt"])
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    emi_bin = resolve_emi(args.emi)
    work = Path(args.work).resolve()
    if not (work / ".git").exists():
        raise SystemExit(f"{work} is not a prepared git workspace")

    bad = changed_outside_laws(work)
    if bad:
        raise SystemExit(
            "Refusing to check laws: files outside `.emi/laws/` were modified:\n"
            + "\n".join(f"  - {p}" for p in bad)
            + "\nRevert changes outside `.emi/laws/` before running `check`."
        )

    files = laws_now(work)
    if not files:
        raise SystemExit(f"No drafted law files found under {work / LAWS}")

    task_out = Path(args.out).resolve() / args.task
    task_out.mkdir(parents=True, exist_ok=True)
    draft_meta_path = task_out / f"draft_{args.role}.json"
    if draft_meta_path.exists():
        meta: dict[str, Any] = json.loads(draft_meta_path.read_text(encoding="utf-8"))
    else:
        meta = {
            "task": args.task,
            "role": args.role,
            "model": args.model,
            "rounds": [],
            "passed": False,
        }

    first_dir_name = "first" if args.role == "primary" else "secondary"
    checked_dir_name = "checked_draft" if args.role == "primary" else "secondary_checked"

    if not meta["rounds"]:
        write_snapshot(files, task_out / first_dir_name)

    state = emi_state_dir(work)
    started = time.monotonic()
    code, text = run(
        [emi_bin, "rules", "check", "--format", "text"],
        cwd=work,
        env={"XDG_STATE_HOME": str(state)},
        timeout=args.timeout,
    )
    elapsed = round(time.monotonic() - started, 1)

    round_idx = len(meta["rounds"])
    checks_dir = task_out / f"checks_{args.role}"
    checks_dir.mkdir(parents=True, exist_ok=True)
    (checks_dir / f"{round_idx}.txt").write_text(text, encoding="utf-8")

    meta["model"] = args.model
    meta["rounds"].append(
        {
            "round": round_idx,
            "exit": code,
            "files": sorted(files),
            "seconds": elapsed,
        }
    )
    if code == 0:
        meta["passed"] = True
        meta["checked_files"] = sorted(files)
        write_snapshot(files, task_out / checked_dir_name)

    draft_meta_path.write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(f"=== emi rules check (round {round_idx}, exit {code}, {elapsed}s) ===")
    print(text.rstrip())
    if code == 0:
        print(f"\nPASSED: saved checked draft to {task_out / checked_dir_name}")
    else:
        print(f"\nFAILED (exit {code}): first draft kept in {task_out / first_dir_name}; fix and re-run `check`.")
    return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Blind law-drafting helper for study/gate.md.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_emi = sub.add_parser("ensure-emi", help="Download prebuilt study-gate-v1 emi binary via gh (or build via cargo).")
    p_emi.add_argument("--dest", default="/tmp/emi-bin/emi")
    p_emi.add_argument("--run-id", default=DEFAULT_EMI_ARTIFACT_RUN)
    p_emi.add_argument("--repo", default=DEFAULT_EMI_REPO)
    p_emi.add_argument("--ref", default="study-gate-v1")
    p_emi.add_argument("--force", action="store_true")
    p_emi.set_defaults(func=cmd_ensure_emi)

    p_prep = sub.add_parser("prepare", help="Prepare a blind workspace and print brief + prompt.")
    p_prep.add_argument("--task", required=True)
    p_prep.add_argument("--work", required=True)
    p_prep.add_argument("--emi", default="emi")
    p_prep.add_argument("--venv")
    p_prep.set_defaults(func=cmd_prepare)

    p_chk = sub.add_parser("check", help="Run emi rules check and snapshot first + checked drafts.")
    p_chk.add_argument("--task", required=True)
    p_chk.add_argument("--work", required=True)
    p_chk.add_argument("--role", required=True, choices=["primary", "secondary"])
    p_chk.add_argument("--model", required=True, help="Full model identifier of the drafter")
    p_chk.add_argument("--out", default="results/heldout-laws")
    p_chk.add_argument("--emi", default="emi")
    p_chk.add_argument("--timeout", type=int, default=3600)
    p_chk.set_defaults(func=cmd_check)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
