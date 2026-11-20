#!/usr/bin/env python3
"""Offline rival & alternative measurement runner (Phase 1 a1 + Phase 2 a2).

Measures:
  (a1) Rivals only: runs `emi rules compare` across pairs of harvested
       candidates (`right_vs_wrong`, `right_vs_right`, `wrong_vs_wrong`) on
       all held-out tasks to quantify drift reach, signal vs. noise,
       correlated LLM blindness, and fork taxonomy (crash / wording /
       interface / leaf).
  (a2) Alternatives + family-member probes: compares a candidate against a
       generated meaningfully-different alternative (`alt.diff`) and runs
       unified effect-recording probes (`probe_*.py`) with admission checks
       (deterministic x2, baseline != candidate on fix probes, no private-
       attribute mocking).

Usage:
    # Run one task (arm a1 or a2):
    python3 study/measure_rivals.py run --task TASK --mode a1 \\
        --attempts results/harvest-heldout/runs \\
        --oracles results/gate-replay-heldout/oracles \\
        --emi /path/to/emi --out out/TASK.jsonl

    # Summarize merged JSONL into JSON + Markdown:
    python3 study/measure_rivals.py summarize --in merged.jsonl \\
        --json summary.json --md summary.md
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

PILOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PILOT / "harness"))

from common import GIT_ENV, copy_tree, git, load_task, run  # noqa: E402
from prepare import prepare  # noqa: E402
from trees import code_env  # noqa: E402

UNINTENDED_BUILTINS = {
    "AttributeError",
    "IndexError",
    "KeyError",
    "NameError",
    "RecursionError",
    "UnboundLocalError",
    "ZeroDivisionError",
    "struct.error",
}

PRIVATE_MOCK_RE = re.compile(
    r"""(?:patch\.object\([^,]+,\s*['"]_[^'"_]|patch\([^)]*\._[A-Za-z]|monkeypatch\.setattr\([^,]+,\s*['"]_[^'"_])"""
)


def load_task_candidates(
    task_id: str,
    attempts_dir: Path,
    oracles_dir: Path,
) -> list[dict[str, Any]]:
    """Load all candidates for `task_id` with their committed oracle verdicts."""
    items: list[dict[str, Any]] = []
    for d in sorted(attempts_dir.iterdir()):
        if not d.is_dir() or not d.name.startswith(task_id + "."):
            continue
        run_path = d / "run.json"
        diff_path = d / "candidate.diff"
        if not run_path.exists() or not diff_path.exists():
            continue
        rec = json.loads(run_path.read_text(encoding="utf-8"))
        if rec.get("task") != task_id:
            continue
        oracle_path = oracles_dir / f"{d.name}.oracle.json"
        if not oracle_path.exists():
            oracle_path = d / "oracle.json"
        if not oracle_path.exists():
            continue
        oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
        if oracle.get("passed") is None:
            continue
        items.append(
            {
                "id": d.name,
                "dir": d,
                "model": str(rec.get("model") or "unknown"),
                "right": bool(oracle["passed"]),
                "diff": diff_path,
            }
        )
    return items


def _cross_first(pairs: list[tuple[dict[str, Any], dict[str, Any]]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Order pairs deterministically, preferring cross-model pairs first."""
    return sorted(
        pairs,
        key=lambda ab: (
            0 if ab[0]["model"] != ab[1]["model"] else 1,
            ab[0]["id"],
            ab[1]["id"],
        ),
    )


def select_pairs(
    candidates: list[dict[str, Any]],
    *,
    max_rw: int = 3,
    max_rr: int = 2,
    max_ww: int = 1,
) -> list[dict[str, Any]]:
    """Select deterministic candidate pairs for (a1) measurement."""
    rights = [c for c in candidates if c["right"]]
    wrongs = [c for c in candidates if not c["right"]]
    selected: list[dict[str, Any]] = []

    if rights and wrongs:
        rw = _cross_first([(r, w) for r in rights for w in wrongs])
        for a, b in rw[:max_rw]:
            selected.append({"pair_kind": "right_vs_wrong", "rival": a, "candidate": b})

    if len(rights) >= 2:
        rr = _cross_first(
            [(rights[i], rights[j]) for i in range(len(rights)) for j in range(i + 1, len(rights))]
        )
        for a, b in rr[:max_rr]:
            selected.append({"pair_kind": "right_vs_right", "rival": a, "candidate": b})

    if not rights and len(wrongs) >= 2:
        ww = _cross_first(
            [(wrongs[i], wrongs[j]) for i in range(len(wrongs)) for j in range(i + 1, len(wrongs))]
        )
        for a, b in ww[:max_ww]:
            selected.append({"pair_kind": "wrong_vs_wrong", "rival": a, "candidate": b})

    return selected


def _value_shape(val: Any) -> str:
    if val is None:
        return "none"
    if isinstance(val, bool):
        return "bool"
    if isinstance(val, (int, float)):
        return "number"
    if isinstance(val, str):
        return "str"
    if isinstance(val, list):
        return "list"
    if isinstance(val, dict):
        return "dict"
    return type(val).__name__


def _exc_type(outcome: dict[str, Any]) -> str | None:
    raised = outcome.get("raised")
    if not isinstance(raised, str):
        return None
    return raised.split(":", 1)[0].strip()


def classify_fork(
    disagreement: dict[str, Any],
    *,
    explicit_raises: set[str] | None = None,
    changed_callers: set[str] | None = None,
) -> dict[str, str]:
    """Deterministically classify a disagreement into mechanism and scope."""
    rival_out = disagreement.get("rival") or {}
    cand_out = disagreement.get("candidate") or {}
    func = str(disagreement.get("function") or "")
    explicit = explicit_raises or set()
    callers = changed_callers or set()

    r_exc = _exc_type(rival_out) if isinstance(rival_out, dict) else None
    c_exc = _exc_type(cand_out) if isinstance(cand_out, dict) else None

    if r_exc and c_exc:
        if r_exc == c_exc:
            return {"mechanism": "wording_only", "scope": "leaf_fork"}
        return {"mechanism": "explicit_raise_vs_value", "scope": "interface_fork"}

    if bool(r_exc) != bool(c_exc):
        exc = r_exc or c_exc or ""
        if exc in UNINTENDED_BUILTINS and exc not in explicit:
            return {"mechanism": "crash_unintended", "scope": "leaf_fork"}
        return {"mechanism": "explicit_raise_vs_value", "scope": "interface_fork"}

    if "timeout" in rival_out or "timeout" in cand_out:
        return {"mechanism": "crash_unintended", "scope": "leaf_fork"}

    r_shape = _value_shape(rival_out.get("returned"))
    c_shape = _value_shape(cand_out.get("returned"))
    if r_shape != c_shape or func in callers:
        return {"mechanism": "value_diff", "scope": "interface_fork"}
    return {"mechanism": "value_diff", "scope": "leaf_fork"}


def detect_private_mocking(probe_src: str) -> list[str]:
    """Detect patching/accessing project-private names (_foo) in a probe file."""
    hits: list[str] = []
    for m in PRIVATE_MOCK_RE.finditer(probe_src):
        hits.append(m.group(0))
    try:
        tree = ast.parse(probe_src)
    except SyntaxError:
        return hits
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            name = node.attr
            if name.startswith("_") and not name.startswith("__"):
                # Ignore standard mock helpers like _mock_...
                if not name.startswith("_mock"):
                    hits.append(f".{name}")
    return sorted(set(hits))


def _explicit_raises_in_diff(diff_text: str) -> set[str]:
    found: set[str] = set()
    for m in re.finditer(r"^\+.*\braise\s+([A-Za-z_][A-Za-z0-9_.]*)", diff_text, flags=re.M):
        found.add(m.group(1).split(".")[-1])
    return found


def _apply_diff_clean(work: Path, diff_path: Path) -> str | None:
    if not diff_path.exists() or diff_path.stat().st_size == 0:
        return None
    code, out = run(["git", "apply", "--binary", str(diff_path.resolve())], cwd=work, env=GIT_ENV)
    if code != 0:
        return f"diff_apply_failed: {out[-400:]}"
    return None


def run_emi_compare(
    base_tree: Path,
    rival_diff: Path,
    cand_diff: Path,
    emi_bin: str,
    tmp: Path,
    tag: str,
    *,
    examples: int = 25,
    max_disagreements: int = 10,
) -> dict[str, Any]:
    """Apply `rival_diff` on branch `rival` and `cand_diff` on working tree,
    then run `emi rules compare rival --format json`."""
    work = tmp / f"cmp-{tag}"
    copy_tree(base_tree, work)
    try:
        git(work, "checkout", "-q", "-B", "rival", "main")
        err = _apply_diff_clean(work, rival_diff)
        if err:
            return {"status": "error", "error": f"rival: {err}", "seconds": 0.0}
        git(work, "add", "-A")
        git(work, "commit", "-q", "--allow-empty", "--no-verify", "-m", "rival")

        git(work, "checkout", "-q", "-B", "candidate", "main")
        err = _apply_diff_clean(work, cand_diff)
        if err:
            return {"status": "error", "error": f"candidate: {err}", "seconds": 0.0}

        # Check if product code diffs between rival and candidate are identical
        _, diff_stat = run(["git", "diff", "--name-only", "rival"], cwd=work, env=GIT_ENV)
        changed_between = [p for p in diff_stat.splitlines() if p.strip()]
        identical_code = not changed_between

        state = work.parent / (work.name + ".emi-state")
        started = time.monotonic()
        cmd = [
            emi_bin,
            "rules",
            "compare",
            "rival",
            "--format",
            "json",
            "--examples",
            str(examples),
            "--max-disagreements",
            str(max_disagreements),
        ]
        try:
            code, out = run(cmd, cwd=work, env={"XDG_STATE_HOME": str(state)}, timeout=900)
        except subprocess.TimeoutExpired:
            return {
                "status": "incomplete",
                "error": "timeout",
                "identical_code": identical_code,
                "seconds": 900.0,
            }
        seconds = round(time.monotonic() - started, 1)
        try:
            payload = json.loads(out[out.index("{") :])
        except ValueError:
            return {
                "status": "error",
                "exit": code,
                "error": out[-800:],
                "identical_code": identical_code,
                "seconds": seconds,
            }
        payload["exit"] = code
        payload["identical_code"] = identical_code
        payload["seconds"] = seconds
        return payload
    finally:
        shutil.rmtree(work, ignore_errors=True)
        shutil.rmtree(work.parent / (work.name + ".emi-state"), ignore_errors=True)


def run_effect_probe(
    task: dict[str, Any],
    base_tree: Path,
    cand_diff: Path,
    alt_diff: Path,
    probe_file: Path,
    tmp: Path,
    tag: str,
) -> dict[str, Any]:
    """Run an effect-recording probe script on baseline, candidate, and alternative.

    A probe script prints one JSON object to stdout mapping case_id -> observable
    effect dict (e.g. `{"returned": ..., "raised": ...}`). Admission checks:
      1. Zero project-private mocking (`detect_private_mocking`).
      2. Deterministic x2 on baseline.
      3. Baseline != candidate on at least one case (proves probe observes the fix).
    """
    src = probe_file.read_text(encoding="utf-8")
    private_hits = detect_private_mocking(src)
    if private_hits:
        return {"admitted": False, "reason": f"private_mocking:{','.join(private_hits[:5])}"}

    def eval_side(side: str, diff: Path | None) -> tuple[dict[str, Any] | None, str | None]:
        w = tmp / f"probe-{tag}-{side}"
        copy_tree(base_tree, w)
        try:
            if diff is not None:
                err = _apply_diff_clean(w, diff)
                if err:
                    return None, err
            py = str(w / ".venv" / "bin" / "python")
            if not Path(py).exists():
                py = sys.executable
            cenv = code_env(task, w)
            py_paths = [str(w.resolve())]
            if cenv.get("PYTHONPATH"):
                py_paths = [cenv["PYTHONPATH"], *py_paths]
            env = {**cenv, "PYTHONPATH": os.pathsep.join(py_paths), "PYTHONHASHSEED": "0"}
            code, out = run([py, str(probe_file.resolve())], cwd=w, env=env, timeout=180)
            if code != 0:
                return None, f"probe_exit_{code}: {out[-400:]}"
            json_lines = [l for l in out.splitlines() if l.strip().startswith("{")]
            if not json_lines:
                return None, f"probe_no_json: {out[-400:]}"
            return json.loads(json_lines[-1]), None
        except Exception as exc:
            return None, f"probe_error: {exc}"
        finally:
            shutil.rmtree(w, ignore_errors=True)

    b1, err1 = eval_side("base1", None)
    b2, err2 = eval_side("base2", None)
    if err1 or err2 or b1 is None or b2 is None:
        return {"admitted": False, "reason": f"baseline_failed:{err1 or err2}"}
    if b1 != b2:
        return {"admitted": False, "reason": "baseline_nondeterministic"}

    c1, errc = eval_side("cand", cand_diff)
    a1, erra = eval_side("alt", alt_diff)
    if errc or erra or c1 is None or a1 is None:
        return {"admitted": False, "reason": f"eval_failed:{errc or erra}"}

    baseline_differs = any(b1.get(k) != c1.get(k) for k in set(b1) | set(c1))
    disagreements = []
    for k in sorted(set(c1) | set(a1)):
        if c1.get(k) != a1.get(k):
            disagreements.append(
                {
                    "file": probe_file.name,
                    "function": k,
                    "input": k,
                    "baseline": b1.get(k),
                    "candidate": c1.get(k),
                    "rival": a1.get(k),
                }
            )
    if not disagreements and not baseline_differs:
        return {"admitted": False, "reason": "vacuous_baseline_equals_candidate"}

    return {
        "admitted": True,
        "baseline_differs": baseline_differs,
        "cases": len(set(c1) | set(a1)),
        "disagreements": disagreements,
    }


def cmd_run(args: argparse.Namespace) -> int:
    task_id = args.task
    task = load_task(task_id)
    candidates = load_task_candidates(task_id, args.attempts, args.oracles)
    rows: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory(dir=os.environ.get("WORK")) as tmp_str:
        tmp = Path(tmp_str)
        base_tree = tmp / "base"
        prepare(task_id, "cooperative", base_tree, args.venv, args.emi)

        if args.mode in ("a1", "both"):
            pairs = select_pairs(candidates)
            for idx, p in enumerate(pairs):
                r, c = p["rival"], p["candidate"]
                res = run_emi_compare(
                    base_tree,
                    r["diff"],
                    c["diff"],
                    args.emi,
                    tmp,
                    f"a1-{idx}",
                    examples=args.examples,
                    max_disagreements=args.max_disagreements,
                )
                explicit = _explicit_raises_in_diff(r["diff"].read_text(encoding="utf-8")) | _explicit_raises_in_diff(
                    c["diff"].read_text(encoding="utf-8")
                )
                classified = [
                    {**d, **classify_fork(d, explicit_raises=explicit)}
                    for d in res.get("disagreements", [])
                ]
                rows.append(
                    {
                        "arm": "a1",
                        "task": task_id,
                        "pair_kind": p["pair_kind"],
                        "rival_id": r["id"],
                        "rival_model": r["model"],
                        "rival_right": r["right"],
                        "candidate_id": c["id"],
                        "candidate_model": c["model"],
                        "candidate_right": c["right"],
                        "status": res.get("status"),
                        "identical_code": res.get("identical_code", False),
                        "compared_inputs": res.get("compared_inputs", 0),
                        "generated_inputs": res.get("generated_inputs", 0),
                        "distinct_forks": res.get("distinct_forks", 0),
                        "total_divergences": res.get("total_divergences", 0),
                        "functions": res.get("functions", []),
                        "not_checked": res.get("not_checked", []),
                        "reasons": res.get("reasons", []),
                        "disagreements": classified,
                        "seconds": res.get("seconds", 0.0),
                        "error": res.get("error"),
                    }
                )

        if args.mode in ("a2", "both") and args.alt_root:
            alt_dir = args.alt_root / task_id
            alt_diff = alt_dir / "alt.diff"
            meta_path = alt_dir / "meta.json"
            if alt_diff.exists() and meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                cand_id = meta["candidate_id"]
                cand = next((x for x in candidates if x["id"] == cand_id), None)
                if cand is not None:
                    cmp_res = run_emi_compare(
                        base_tree,
                        alt_diff,
                        cand["diff"],
                        args.emi,
                        tmp,
                        "a2-cmp",
                        examples=args.examples,
                        max_disagreements=args.max_disagreements,
                    )
                    explicit = _explicit_raises_in_diff(alt_diff.read_text(encoding="utf-8")) | _explicit_raises_in_diff(
                        cand["diff"].read_text(encoding="utf-8")
                    )
                    probe_results = []
                    for pf in sorted(alt_dir.glob("probe_*.py")):
                        pr = run_effect_probe(task, base_tree, cand["diff"], alt_diff, pf, tmp, pf.stem)
                        if pr.get("admitted"):
                            pr["disagreements"] = [
                                {**d, **classify_fork(d, explicit_raises=explicit)}
                                for d in pr.get("disagreements", [])
                            ]
                        probe_results.append({"probe": pf.name, **pr})
                    all_divs = [
                        {**d, **classify_fork(d, explicit_raises=explicit)}
                        for d in cmp_res.get("disagreements", [])
                    ]
                    for pr in probe_results:
                        if pr.get("admitted"):
                            all_divs.extend(pr.get("disagreements", []))
                    rows.append(
                        {
                            "arm": "a2",
                            "task": task_id,
                            "pair_kind": "alt_vs_wrong" if not cand["right"] else "alt_vs_right",
                            "rival_id": f"{task_id}.alt",
                            "rival_right": meta.get("alt_right"),
                            "candidate_id": cand["id"],
                            "candidate_right": cand["right"],
                            "status": "disagreed" if all_divs else cmp_res.get("status"),
                            "drift_status": cmp_res.get("status"),
                            "compared_inputs": cmp_res.get("compared_inputs", 0),
                            "distinct_forks": len(all_divs),
                            "disagreements": all_divs,
                            "probes": probe_results,
                            "seconds": cmp_res.get("seconds", 0.0),
                        }
                    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    print(f"{task_id}: wrote {len(rows)} measurement rows to {args.out}")
    return 0


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate reach, signal/noise, and fork-taxonomy summary."""
    by_arm: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        by_arm[str(r.get("arm", "a1"))].append(r)

    out: dict[str, Any] = {"total_rows": len(rows), "arms": {}}
    for arm, arm_rows in sorted(by_arm.items()):
        by_kind: dict[str, list[dict[str, Any]]] = defaultdict(list)
        status_counts: Counter[str] = Counter()
        mech_counts: Counter[str] = Counter()
        scope_counts: Counter[str] = Counter()
        fn_compared = 0
        fn_no_inputs = 0
        fn_not_checked = 0
        identical_pairs = 0

        for r in arm_rows:
            by_kind[str(r.get("pair_kind", "unknown"))].append(r)
            status_counts[str(r.get("status", "unknown"))] += 1
            if r.get("identical_code"):
                identical_pairs += 1
            for f in r.get("functions", []):
                if f.get("status") == "compared":
                    fn_compared += 1
                else:
                    fn_no_inputs += 1
            fn_not_checked += len(r.get("not_checked", []))
            for d in r.get("disagreements", []):
                mech_counts[str(d.get("mechanism", "unknown"))] += 1
                scope_counts[str(d.get("scope", "unknown"))] += 1

        kind_stats = {}
        for k, krows in sorted(by_kind.items()):
            tasks_total = len({r["task"] for r in krows})
            tasks_disagreed = len({r["task"] for r in krows if r.get("status") == "disagreed"})
            pairs_disagreed = sum(1 for r in krows if r.get("status") == "disagreed")
            pairs_agreed = sum(1 for r in krows if r.get("status") == "agreed")
            pairs_incomplete = sum(1 for r in krows if r.get("status") not in ("agreed", "disagreed"))
            kind_stats[k] = {
                "pairs": len(krows),
                "pairs_disagreed": pairs_disagreed,
                "pairs_agreed": pairs_agreed,
                "pairs_incomplete": pairs_incomplete,
                "pair_disagree_rate": round(pairs_disagreed / len(krows), 4) if krows else 0.0,
                "tasks": tasks_total,
                "tasks_disagreed": tasks_disagreed,
                "task_disagree_rate": round(tasks_disagreed / tasks_total, 4) if tasks_total else 0.0,
            }

        out["arms"][arm] = {
            "pairs": len(arm_rows),
            "identical_code_pairs": identical_pairs,
            "status_counts": dict(sorted(status_counts.items())),
            "reach": {
                "functions_compared": fn_compared,
                "functions_no_inputs": fn_no_inputs,
                "functions_not_checked": fn_not_checked,
            },
            "by_pair_kind": kind_stats,
            "fork_mechanisms": dict(sorted(mech_counts.items())),
            "fork_scopes": dict(sorted(scope_counts.items())),
        }
    return out


def format_summary_md(summary: dict[str, Any]) -> str:
    lines = ["# Rival & Alternative Measurement Summary", ""]
    for arm, data in summary["arms"].items():
        lines.append(f"## Arm `{arm}` ({data['pairs']} pairs)")
        lines.append("")
        r = data["reach"]
        tot_fn = r["functions_compared"] + r["functions_no_inputs"] + r["functions_not_checked"]
        pct = f"{(100.0 * r['functions_compared'] / tot_fn):.1f}%" if tot_fn else "n/a"
        lines.append(
            f"- **Reach:** {r['functions_compared']}/{tot_fn} functions compared ({pct}); "
            f"`no_inputs`: {r['functions_no_inputs']}, `not_checked`: {r['functions_not_checked']}"
        )
        lines.append(f"- **Identical-code pairs:** {data['identical_code_pairs']}")
        lines.append(f"- **Statuses:** `{data['status_counts']}`")
        lines.append("")
        lines.append("| Pair Kind | Pairs | Disagreed | Agreed | Incomplete | Tasks Disagreed |")
        lines.append("|---|---:|---:|---:|---:|---:|")
        for k, ks in data["by_pair_kind"].items():
            lines.append(
                f"| `{k}` | {ks['pairs']} | {ks['pairs_disagreed']} ({ks['pair_disagree_rate']:.1%}) | "
                f"{ks['pairs_agreed']} | {ks['pairs_incomplete']} | "
                f"{ks['tasks_disagreed']}/{ks['tasks']} ({ks['task_disagree_rate']:.1%}) |"
            )
        lines.append("")
        if data["fork_mechanisms"] or data["fork_scopes"]:
            lines.append(f"- **Fork mechanisms:** `{data['fork_mechanisms']}`")
            lines.append(f"- **Fork scopes:** `{data['fork_scopes']}`")
            lines.append("")
    return "\n".join(lines)


def cmd_summarize(args: argparse.Namespace) -> int:
    rows = [json.loads(l) for l in args.input.read_text(encoding="utf-8").splitlines() if l.strip()]
    summary = summarize_rows(rows)
    md = format_summary_md(summary)
    if args.json_out:
        args.json_out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.md_out:
        args.md_out.write_text(md, encoding="utf-8")
    if not args.json_out and not args.md_out:
        sys.stdout.write(md)
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Phase 1 (a1) and Phase 2 (a2) rival measurement runner.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="Measure one task.")
    p_run.add_argument("--task", required=True)
    p_run.add_argument("--mode", choices=["a1", "a2", "both"], default="a1")
    p_run.add_argument("--attempts", type=Path, required=True)
    p_run.add_argument("--oracles", type=Path, required=True)
    p_run.add_argument("--alt-root", type=Path)
    p_run.add_argument("--emi", default="emi")
    p_run.add_argument("--venv")
    p_run.add_argument("--examples", type=int, default=25)
    p_run.add_argument("--max-disagreements", type=int, default=10)
    p_run.add_argument("--out", type=Path, required=True)
    p_run.set_defaults(func=cmd_run)

    p_sum = sub.add_parser("summarize", help="Summarize merged JSONL rows.")
    p_sum.add_argument("--in", dest="input", type=Path, required=True)
    p_sum.add_argument("--json", dest="json_out", type=Path)
    p_sum.add_argument("--md", dest="md_out", type=Path)
    p_sum.set_defaults(func=cmd_summarize)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
