#!/usr/bin/env python3
"""Run a scenario on a tree and record its observation; admit scenarios;
answer a candidate's observation from the merged fix's.

A scenario is a plain Python script, run with the task's own interpreter
from the repository root. It does what the task text describes through
the project's public names and prints one line per observation:

    EMI-OBSERVATION {"name": "requests on second call", "value": 0}

A script, not a pytest test: a project's pytest settings (python_files,
testpaths) decide what pytest collects, and a test it skips is never run.
That silently dropped the ceiling's law on fontTools and Faker
(results/rerun7-2026-11-20). A script has no such step.

Every run is sealed (no network, the pilot's records hidden: harness
`agent.sealed`) and pinned (hash seed, time zone, locale). A scenario is
run twice; two runs that observe differently are `nondeterministic` and
observe nothing.

    run_scenario.py observe --tree WORK --scenario S.py [--task ID]
    run_scenario.py admit   --scenario S.py --task-text TEXT.txt --baseline OBS.json
    run_scenario.py answer  --candidate OBS.json --merged OBS.json
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
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "harness"))

from agent import scrubbed_env, sealed  # noqa: E402
from common import load_task  # noqa: E402
from trees import code_env  # noqa: E402

MARK = "EMI-OBSERVATION "
SCENARIO_DIR = ".emi-scenario"
TIMEOUT_S = 120
PINS = {"PYTHONHASHSEED": "0", "TZ": "UTC", "LC_ALL": "C.UTF-8", "LANG": "C.UTF-8",
        "PYTHONDONTWRITEBYTECODE": "1"}


def parse_observations(stdout: str) -> list[dict[str, Any]] | str:
    """The observation lines, or why they could not be read."""
    out = []
    for line in stdout.splitlines():
        if not line.startswith(MARK):
            continue
        try:
            item = json.loads(line[len(MARK):])
        except json.JSONDecodeError as e:
            return f"an observation line is not JSON ({e.msg})"
        if not isinstance(item, dict) or set(item) != {"name", "value"}:
            return "an observation must be {\"name\": ..., \"value\": ...}"
        out.append(item)
    return out


def run_once(tree: Path, scenario: Path, task: dict[str, Any] | None) -> dict[str, Any]:
    """One sealed, pinned run of `scenario` in `tree`."""
    dst = tree / SCENARIO_DIR / "scenario.py"
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(scenario, dst)
    python = tree / ".venv" / "bin" / "python"
    env = scrubbed_env("MODEL_API_KEY", {**(code_env(task, tree) if task else {}), **PINS})
    cmd = sealed(tree, f"{python} {SCENARIO_DIR}/scenario.py")
    try:
        p = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "seconds": TIMEOUT_S}
    finally:
        shutil.rmtree(tree / SCENARIO_DIR, ignore_errors=True)
    obs = parse_observations(p.stdout)
    tail = p.stderr[-800:]
    if isinstance(obs, str):
        return {"status": "unreadable", "why": obs, "stderr": tail}
    if p.returncode != 0:
        return {"status": "crashed", "exit": p.returncode, "stderr": tail, "observations": obs}
    if not obs:
        return {"status": "no_observation", "stderr": tail}
    return {"status": "observed", "observations": obs}


def observe(tree: Path, scenario: Path, task: dict[str, Any] | None, runs: int = 2) -> dict[str, Any]:
    """`runs` runs; one result, `nondeterministic` when they differ."""
    results = [run_once(tree, scenario, task) for _ in range(runs)]
    first = results[0]
    if first["status"] != "observed":
        return first
    if any(r != first for r in results[1:]):
        return {"status": "nondeterministic", "runs": results}
    return first


# --- admission -----------------------------------------------------------

def private_uses(src: str) -> list[str]:
    """Private names of the project the scenario reads, patches or imports:
    `x._y`, `from m import _y`, and patch targets naming `._y`."""
    tree = ast.parse(src)
    found: set[str] = set()

    def private(name: str) -> bool:
        return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))

    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and private(node.attr):
            found.add(node.attr)
        elif isinstance(node, ast.ImportFrom):
            found.update(a.name for a in node.names if private(a.name))
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if re.fullmatch(r"[\w.]+", node.value) and any(private(p) for p in node.value.split(".")[1:]):
                found.add(node.value)
    return sorted(found)


def names_used(src: str) -> set[str]:
    """Every name the scenario imports or reads as an attribute."""
    tree = ast.parse(src)
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(a.name for a in node.names)
            if node.module:
                names.update(node.module.split("."))
        elif isinstance(node, ast.Import):
            for a in node.names:
                names.update(a.name.split("."))
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return names


def names_the_task(src: str, task_text: str) -> bool:
    words = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", task_text))
    return any(n in words and not n.startswith("_") and len(n) > 2 for n in names_used(src))


# (predicate on (source, task text, baseline result), message): a scenario
# is admitted when no predicate holds.
ADMISSION: list[tuple[Callable[[str, str, dict[str, Any]], bool], str]] = [
    (lambda s, t, b: bool(private_uses(s)), "it uses the project's private names"),
    (lambda s, t, b: not names_the_task(s, t), "it calls no public name the task text names"),
    (lambda s, t, b: b.get("status") == "nondeterministic", "it observes differently on two baseline runs"),
    (lambda s, t, b: b.get("status") in ("timeout", "unreadable", "no_observation"),
     "it observed nothing at the baseline"),
]


def admit(src: str, task_text: str, baseline: dict[str, Any]) -> dict[str, Any]:
    """Whether a scenario is admitted, and every reason it is not.

    A baseline run that crashed is admitted: for a bug fix the baseline may
    be exactly what crashes. One that observed nothing at all is not.
    """
    try:
        why = [msg for pred, msg in ADMISSION if pred(src, task_text, baseline)]
    except SyntaxError as e:
        why = [f"it does not parse ({e.msg})"]
    out: dict[str, Any] = {"admitted": not why, "why": why}
    if private_uses_safe(src):
        out["private"] = private_uses_safe(src)
    return out


def private_uses_safe(src: str) -> list[str]:
    try:
        return private_uses(src)
    except SyntaxError:
        return []


# --- the simulated answerer -----------------------------------------------

def observed_values(result: dict[str, Any]) -> Any:
    """What a result shows a person: its observations, or how it ended."""
    if result.get("status") in ("observed", "crashed"):
        return {"status": result["status"], "observations": result.get("observations", [])}
    return {"status": result.get("status")}


def answer(candidate: dict[str, Any], merged: dict[str, Any]) -> dict[str, Any]:
    """The simulated person's answer, from the merged fix's observation.

    `agree`: the candidate observes what the merged fix does. `finding`:
    it does not, answered "should be the merged fix's". `either`: the merged
    fix's own observation is not settled (it differed between its runs, or
    observed nothing), so the truth does not decide and nothing is asked.
    """
    if merged.get("status") not in ("observed", "crashed"):
        return {"answer": "either", "why": f"the merged fix's run was {merged.get('status')}"}
    want, got = observed_values(merged), observed_values(candidate)
    if want == got:
        return {"answer": "agree"}
    return {"answer": "finding", "candidate": got, "merged": want}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("observe")
    o.add_argument("--tree", required=True, type=Path)
    o.add_argument("--scenario", required=True, type=Path)
    o.add_argument("--task")
    o.add_argument("--runs", type=int, default=2)
    a = sub.add_parser("admit")
    a.add_argument("--scenario", required=True, type=Path)
    a.add_argument("--task-text", required=True, type=Path)
    a.add_argument("--baseline", required=True, type=Path)
    w = sub.add_parser("answer")
    w.add_argument("--candidate", required=True, type=Path)
    w.add_argument("--merged", required=True, type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "observe":
        task = load_task(args.task) if args.task else None
        res = observe(args.tree.resolve(), args.scenario.resolve(), task, args.runs)
    elif args.cmd == "admit":
        res = admit(args.scenario.read_text(encoding="utf-8"),
                    args.task_text.read_text(encoding="utf-8"),
                    json.loads(args.baseline.read_text(encoding="utf-8")))
    else:
        res = answer(json.loads(args.candidate.read_text(encoding="utf-8")),
                     json.loads(args.merged.read_text(encoding="utf-8")))
    print(json.dumps(res, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
